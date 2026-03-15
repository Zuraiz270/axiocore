import { Injectable, Logger } from '@nestjs/common';
import { PrismaService } from '../prisma/prisma.service';
import { ReviewService } from './review.service';

@Injectable()
export class AutoApprovalService {
  private readonly logger = new Logger(AutoApprovalService.name);

  constructor(
    private readonly prisma: PrismaService,
    private readonly reviewService: ReviewService,
  ) {}

  /**
   * Evaluates if a document qualifies for Auto-Approval (HOTL).
   * Criteria:
   * 1. Confidence Score > 0.95
   * 2. No Integrity Risk (Forensics)
   * 3. No Consensus required
   */
  async evaluateDocument(documentId: string): Promise<boolean> {
    const doc = await (this.prisma as any).document.findUnique({
      where: { id: documentId },
    });

    if (!doc) return false;

    const forensics = doc.forensics_report as any;
    const isHighConfidence = doc.confidence_score >= 0.95;
    const isLowRiskIntegrity = !forensics || forensics.integrity_risk === 'low';
    const noConsensusRequired = !doc.requires_consensus;

    if (isHighConfidence && isLowRiskIntegrity && noConsensusRequired) {
      this.logger.log(`Document ${documentId} qualifies for Auto-Approval. Confidence: ${doc.confidence_score}`);
      
      try {
        // Submit a "System" review
        await this.reviewService.submitReview(
          doc.tenant_id,
          documentId,
          '00000000-0000-0000-0000-000000000000', // System Reviewer ID
          {
            status: 'APPROVED',
            comment: 'Auto-approved via HOTL logic (Confidence > 0.95)',
            durationMs: 0,
            isCorrection: false,
            extractionVersion: doc.extraction_version,
          },
          true // Bypass lock check for system
        );
        return true;
      } catch (err) {
        this.logger.error(`Failed to auto-approve document ${documentId}: ${err.message}`);
      }
    }

    return false;
  }
}
