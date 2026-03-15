import { Injectable, Logger } from '@nestjs/common';
import Redis from 'ioredis';
import { IngestRequest } from '@opp/shared';
import { PrismaService } from '../prisma/prisma.service';

@Injectable()
export class IngestService {
  private readonly logger = new Logger(IngestService.name);
  private readonly redisClient: Redis;

  constructor(private readonly prisma: PrismaService) {
    this.redisClient = new Redis(process.env.REDIS_URL || 'redis://localhost:6379');
  }

  /**
   * Calculates the compute weight of a document using the defined architecture formula:
   * W = (Page Count * Resolution Factor) + Modality Weight
   */
  calculateComputeWeight(
    pageCount: number,
    sourceType: 'digital_native' | 'scanned',
    resolutionFactor: number = 1.0 // Assume 300 DPI normalized to 1.0
  ): number {
    const modalityWeight = sourceType === 'digital_native' ? 1.0 : 5.0;
    const computeWeight = (pageCount * resolutionFactor) + modalityWeight;
    return computeWeight;
  }

  /**
   * Determines the priority queue based on Compute Weight and current stream pressure.
   */
  async determineRoutingLane(computeWeight: number): Promise<'high' | 'low'> {
    // Spec: Route to high_priority_stream IF W <= 15 AND XLEN(stream:extraction:high) < 10

    if (computeWeight > 15) {
      return 'low'; // Too heavy for the fast lane
    }

    try {
      // Check backpressure on the high-priority Redis Stream
      const highLanePressure = await this.redisClient.xlen('stream:extraction:high');
      
      if (highLanePressure < 10) {
        return 'high';
      } else {
        return 'low'; // High priority is currently congested, downgrade to low lane
      }
    } catch (error) {
      this.logger.error('Failed to check Redis stream length, defaulting to low queue', error);
      return 'low';
    }
  }

  async processIngestion(payload: IngestRequest, tenantId: string, pageCount: number, sourceType: 'digital_native' | 'scanned') {
    const weight = this.calculateComputeWeight(pageCount, sourceType);
    const lane = await this.determineRoutingLane(weight);
    
    // Strict Transactional Outbox Sequence (Phase 1)
    return await this.prisma.$transaction(async (tx) => {
      // 1. Enforce Row-Level Security explicitly within the transaction bounds
      // (Bypassed slightly if using Prisma natively without an RLS extension, but simulated for structure)
      await tx.$executeRawUnsafe(`SET LOCAL app.current_tenant = '${tenantId}';`);

      // 2. Insert document metadata row
      const doc = await tx.document.create({
        data: {
          tenant_id: tenantId,
          original_filename: payload.original_filename,
          mime_type: payload.mime_type,
          file_size_bytes: payload.file_buffer?.length || 1024,
          page_count: pageCount,
          storage_path: `tenant-${tenantId}/incoming/${payload.original_filename}`, // Storage mock
          priority_queue: lane,
          schema_type: payload.schema_type,
          source_type: sourceType,
          status: 'INGESTED'
        }
      });

      // 3. Insert Outbox Event securely
      const eventPayload = {
        document_id: doc.id,
        storage_path: doc.storage_path,
        priority_queue: lane,
        compute_weight: weight,
        mime_type: doc.mime_type,
        schema_type: doc.schema_type,
        source_type: doc.source_type,
        file_size_bytes: doc.file_size_bytes,
      };

      const outbox = await tx.outboxEvent.create({
        data: {
          tenant_id: tenantId,
          aggregate_type: 'document',
          aggregate_id: doc.id,
          event_type: 'document.ingested',
          payload: eventPayload,
          status: 'PENDING' // Relay will pick this up
        }
      });

      return {
        message: 'Compute weight calculated and routed atomically.',
        document_id: doc.id,
        outbox_event_id: outbox.id,
        tenant_id: tenantId,
        compute_weight: weight,
        assigned_lane: lane
      };
    });
  }
}
