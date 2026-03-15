import { Injectable, Logger } from '@nestjs/common';
import { Cron, CronExpression } from '@nestjs/schedule';
import { PrismaService } from '../prisma/prisma.service';
import { StorageService } from '../storage/storage.service';

@Injectable()
export class OrphanCleanupService {
  private readonly logger = new Logger(OrphanCleanupService.name);

  constructor(
    private readonly prisma: PrismaService,
    private readonly storage: StorageService,
  ) {}

  /**
   * Nightly MinIO Orphan Cleanup (Axiocore Policy A14).
   * Runs at 3 AM every night.
   */
  @Cron(CronExpression.EVERY_DAY_AT_3AM)
  async handleCleanup() {
    this.logger.log('Starting nightly MinIO orphan cleanup...');
    
    try {
      // 1. Get all objects from MinIO
      const minioObjects = await this.storage.listAllObjects();
      if (minioObjects.length === 0) {
        this.logger.log('No objects found in MinIO. Cleanup complete.');
        return;
      }

      // 2. Get all document storage paths from Postgres
      // We use a set for fast O(1) lookups
      const documents = await this.prisma.document.findMany({
        select: { storage_path: true },
      });
      const dbPaths = new Set(documents.map((doc) => doc.storage_path));

      // 3. Identify orphans
      // An orphan is a MinIO object that DOES NOT exist in dbPaths
      const orphans = minioObjects.filter((obj) => !dbPaths.has(obj));

      if (orphans.length === 0) {
        this.logger.log('No orphans found. Storage is consistent.');
        return;
      }

      this.logger.log(`Found ${orphans.length} orphaned objects. Deleting...`);

      // 4. Delete orphans
      for (const orphan of orphans) {
        // Safety check: Don't delete metadata or folder markers if any
        if (orphan.endsWith('/')) continue;
        
        // Spec A14: Only delete orphans older than 24h
        const stat = await this.storage.getObjectStat(orphan);
        const yesterday = new Date();
        yesterday.setDate(yesterday.getDate() - 1);

        if (stat.lastModified < yesterday) {
          await this.storage.deleteObject(orphan);
        } else {
          this.logger.debug(`Skipping recent orphan: ${orphan} (modified ${stat.lastModified})`);
        }
      }

      this.logger.log('Nightly cleanup finished.');
    } catch (error) {
      this.logger.error(`Orphan cleanup failed: ${error.message}`);
    }
  }
}
