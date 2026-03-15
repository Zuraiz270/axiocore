import { Controller, Post, Get, Body, Param, UseGuards, Request } from '@nestjs/common';
import { ReviewService } from './review.service';
import { JwtAuthGuard } from '../auth/jwt-auth.guard';

@Controller('reviews')
@UseGuards(JwtAuthGuard)
export class ReviewController {
  constructor(private readonly reviewService: ReviewService) {}

  @Post(':documentId/lock')
  async acquireLock(
    @Request() req,
    @Param('documentId') documentId: string,
  ) {
    return this.reviewService.acquireReviewLock(documentId, req.user.id);
  }

  @Post(':documentId/heartbeat')
  async extendLock(
    @Request() req,
    @Param('documentId') documentId: string,
  ) {
    return this.reviewService.extendReviewLock(documentId, req.user.id);
  }

  @Post(':documentId')
  async submitReview(
    @Request() req,
    @Param('documentId') documentId: string,
    @Body() body: { 
      status: 'APPROVED' | 'REJECTED'; 
      comment?: string;
      durationMs: number;
      isCorrection: boolean;
      extractionVersion: number;
    },
  ) {
    return this.reviewService.submitReview(
      req.user.tenantId,
      documentId,
      req.user.id,
      body,
    );
  }

  @Get('analytics')
  async getAnalytics(@Request() req) {
    return this.reviewService.getReviewerAnalytics(req.user.tenantId);
  }
}
