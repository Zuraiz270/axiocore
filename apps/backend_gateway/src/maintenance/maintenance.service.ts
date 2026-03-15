import { Injectable, Logger, OnApplicationBootstrap } from '@nestjs/common';
import { PrismaService } from '../prisma/prisma.service';
import { StorageService } from '../storage/storage.service';
import { Cron, CronExpression } from '@nestjs/schedule';

@Injectable()
export class MaintenanceService implements OnApplicationBootstrap {
  private readonly logger = new Logger(MaintenanceService.name);

  constructor(
    private readonly prisma: PrismaService,
    private readonly storage: StorageService
  ) {}

  async onApplicationBootstrap() {
    this.logger.log('MaintenanceService: Checking DeletionRegistry for replay (A11)...');
    try {
      await this.replayDeletions();
    } catch (error) {
      this.logger.error('Failed to replay deletions on startup', error);
    }
  }

  /**
   * REPLAY LOGIC (A11): On restart, ensure deleted docs in registry
   * are also absent from primary DB and storage.
   */
  async replayDeletions() {
    const pending = await (this.prisma as any).deletionRegistry.findMany({
      where: { status: 'pending' }
    });

    if (pending.length === 0) return;

    this.logger.log(`Replaying ${pending.length} deletions from registry...`);

    for (const record of pending) {
      try {
        // 1. Delete from PostgreSQL if still exists
        await (this.prisma as any).document.deleteMany({
          where: { id: record.document_id }
        });

        // 2. Delete from Storage
        await this.storage.deleteObject(record.storage_path);

        // 3. Mark as completed
        await (this.prisma as any).deletionRegistry.update({
          where: { id: record.id },
          data: { 
            status: 'completed',
            completed_at: new Date()
          }
        });
        
        this.logger.debug(`Replayed deletion for doc ${record.document_id}`);
      } catch (err) {
        this.logger.error(`Failed to replay deletion for ${record.document_id}`, err);
      }
    }
  }

  /**
   * Nightly Orphan Cleanup (A14): Compare MinIO objects against Document records.
   * Objects older than 24h with no DB record are deleted.
   */
  @Cron(CronExpression.EVERY_DAY_AT_MIDNIGHT)
  async cleanupOrphanedObjects() {
    this.logger.log('Starting nightly MinIO orphan cleanup (A14)...');
    
    try {
      const allObjects = await this.storage.listAllObjects();
      
      for (const objectName of allObjects) {
        // Only target document storage paths (tenant-{id}/...)
        if (!objectName.startsWith('tenant-')) continue;

        try {
          const doc = await (this.prisma as any).document.findFirst({
            where: { storage_path: objectName }
          });

          if (!doc) {
            const stat = await this.storage.getObjectStat(objectName);
            const ageInHours = (new Date().getTime() - stat.lastModified.getTime()) / (1000 * 60 * 60);

            if (ageInHours > 24) {
              this.logger.warn(`Orphan found: ${objectName} (Age: ${ageInHours.toFixed(1)}h). Deleting...`);
              await this.storage.deleteObject(objectName);
            }
          }
        } catch (err) {
          this.logger.error(`Error checking status of object ${objectName}`, err);
        }
      }
      this.logger.log('Orphan cleanup complete.');
    } catch (error) {
      this.logger.error('Orphan cleanup failed', error);
    }
  }
}
