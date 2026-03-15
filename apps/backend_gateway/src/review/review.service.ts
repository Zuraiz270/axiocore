import { Injectable, BadRequestException, Logger, ConflictException, UnauthorizedException } from '@nestjs/common';
import { PrismaService } from '../prisma/prisma.service';
import { RedisService } from '../redis/redis.service';

@Injectable()
export class ReviewService {
  private readonly logger = new Logger(ReviewService.name);
  private readonly LOCK_TTL = 15; // 15 seconds absolute expiry

  constructor(
    private prisma: PrismaService,
    private redis: RedisService,
  ) {}

  async acquireReviewLock(documentId: string, reviewerId: string): Promise<void> {
    const lockKey = `lock:document:${documentId}`;
    const existingLock = await this.redis.get(lockKey);

    if (existingLock && existingLock !== reviewerId) {
      throw new ConflictException('This document is already being reviewed by another user.');
    }

    // Set lock with 15s TTL (A5 spec)
    await this.redis.set(lockKey, reviewerId, this.LOCK_TTL);
    
    // Also update the document record for visibility
    await this.prisma.document.update({
      where: { id: documentId },
      data: { 
        reviewer_id: reviewerId,
        locked_at: new Date()
      }
    });
  }

  async extendReviewLock(documentId: string, reviewerId: string): Promise<void> {
    const lockKey = `lock:document:${documentId}`;
    const currentReviewer = await this.redis.get(lockKey);

    if (currentReviewer !== reviewerId) {
      throw new UnauthorizedException('Lock has expired or been stolen.');
    }

    await this.redis.set(lockKey, reviewerId, this.LOCK_TTL);
  }

  async submitReview(
    tenantId: string,
    documentId: string,
    reviewerId: string,
    data: { 
      status: 'APPROVED' | 'REJECTED'; 
      comment?: string;
      durationMs: number;
      isCorrection: boolean;
      extractionVersion: number; // A1 Requirement
    },
  ) {
    // A5: Verify Lock Ownership before submission
    const lockKey = `lock:document:${documentId}`;
    const lockOwner = await this.redis.get(lockKey);
    if (lockOwner !== reviewerId) {
       throw new UnauthorizedException('Submission denied: Reviewer lock expired or belongs to another session.');
    }
    // 1. "Suspiciously Fast" Flagging (Phase 4 Security)
    if (data.durationMs < 2000 && data.status === 'APPROVED') {
      this.logger.warn(
        `Suspiciously fast approval detected: Doc ${documentId} by Reviewer ${reviewerId} in ${data.durationMs}ms`,
      );
      // We still record it, but it might be flagged in audits later
    }

    // 2. Record the review
    const review = await (this.prisma as any).review.create({
      data: {
        document_id: documentId,
        reviewer_id: reviewerId,
        tenant_id: tenantId,
        status: data.status,
        comment: data.comment,
        review_duration_ms: data.durationMs,
        was_corrected: data.isCorrection,
      },
    });

    // 3. Update document status if consensus reached or single review sufficient
    // A1: Conditional Update to prevent stale submissions
    const doc = await (this.prisma as any).document.findFirst({
      where: { 
        id: documentId,
        extraction_version: data.extractionVersion // A1: Stale Review Protection
      },
    });

    if (!doc) {
      throw new ConflictException(`Stale review: Extraction version ${data.extractionVersion} no longer matches the current document state.`);
    }

    // Release lock on success
    await this.redis.del(lockKey);

    if ((doc as any).requires_consensus) {
      const allReviews = await (this.prisma as any).review.findMany({
        where: { document_id: documentId },
      });

      if (allReviews.length >= 2) {
        const approvals = allReviews.filter((r) => r.status === 'APPROVED').length;
        if (approvals >= 2) {
          await (this.prisma as any).document.update({
            where: { id: documentId },
            data: { status: 'APPROVED' },
          });
        } else if (allReviews.length - approvals >= 1) {
          // If any rejection in consensus mode, it goes to REJECTED
          await (this.prisma as any).document.update({
            where: { id: documentId },
            data: { status: 'REJECTED' },
          });
        }
      }
    } else {
      // Single review sufficient
      await (this.prisma as any).document.update({
        where: { id: documentId },
        data: { status: data.status === 'APPROVED' ? 'APPROVED' : 'REJECTED' },
      });
    }

    return review;
  }

  async getReviewerAnalytics(tenantId: string) {
    const reviews = await (this.prisma as any).review.findMany({
      where: { tenant_id: tenantId },
    });

    const total = reviews.length;
    if (reviews.length === 0) return { correctionRate: 0, avgReviewTime: 0 };

    return {
      totalReviews: reviews.length,
      correctionRate: (reviews.filter((r) => r.was_corrected).length / reviews.length) * 100,
      avgReviewTimeMs: reviews.reduce((acc, r) => acc + (r.review_duration_ms || 0), 0) / reviews.length,
      suspiciousApprovals: reviews.filter((r) => r.review_duration_ms && r.review_duration_ms < 2000 && r.status === 'APPROVED').length,
    };
  }
}
