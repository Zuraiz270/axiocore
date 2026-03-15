import { Injectable, Logger } from '@nestjs/common';
import { Cron, CronExpression } from '@nestjs/schedule';
import { PrismaService } from '../prisma/prisma.service';
import Redis from 'ioredis';

@Injectable()
export class OutboxService {
  private readonly logger = new Logger(OutboxService.name);
  private readonly redisClient: Redis;
  private isPolling = false;

  constructor(private readonly prisma: PrismaService) {
    this.redisClient = new Redis(process.env.REDIS_URL || 'redis://localhost:6379');
  }

  // Poll every 5 seconds. In production, tools like pg_notify or Debezium could be used,
  // but for V3 Phase 1, cron polling is sufficient and robust.
  @Cron(CronExpression.EVERY_5_SECONDS)
  async processOutbox() {
    if (this.isPolling) {
      return; // Prevent duplicate concurrent polling
    }
    this.isPolling = true;

    try {
      // 1. Fetch pending outbox events (ordered by creation to maintain causality)
      const pendingEvents = await this.prisma.outboxEvent.findMany({
        where: { status: 'PENDING' },
        orderBy: { created_at: 'asc' },
        take: 50, // Batch limit
      });

      if (pendingEvents.length === 0) {
        return;
      }

      this.logger.log(`Found ${pendingEvents.length} pending outbox events to publish.`);

      // 2. Process each event
      for (const event of pendingEvents) {
        try {
          // Architecture Logic: route specifically based on priority_queue payload
          const payload = event.payload as Record<string, any>;
          const lane = payload.priority_queue === 'high' ? 'high' : 'low';
          const streamKey = `stream:extraction:${lane}`;

          // Format for Redis Streams (XADD) - Note: object must be flattened into key-value strings
          const flatPayload = {
            id: event.aggregate_id,
            tenant_id: event.tenant_id,
            event_type: event.event_type,
            storage_path: payload.storage_path,
            compute_weight: String(payload.compute_weight),
          };

          // 3. Publish to Redis Stream
          await this.redisClient.xadd(streamKey, '*', ...Object.entries(flatPayload).flat());

          // 4. Mark Outbox event as PUBLISHED securely
          await this.prisma.outboxEvent.update({
            where: { id: event.id },
            data: { 
              status: 'PUBLISHED',
              published_at: new Date()
            }
          });

          this.logger.debug(`Successfully published outbox event ${event.id} to ${streamKey}`);
        } catch (error) {
          this.logger.error(`Failed to publish outbox event ${event.id}`, error);
          // Mark as FAILED so it can be retried or investigated
          await this.prisma.outboxEvent.update({
            where: { id: event.id },
            data: { status: 'FAILED' }
          });
        }
      }
    } catch (error) {
      this.logger.error('Error during outbox polling loop', error);
    } finally {
      this.isPolling = false;
    }
  }
}
