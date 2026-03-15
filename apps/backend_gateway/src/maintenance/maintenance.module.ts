import { Module } from '@nestjs/common';
import { MaintenanceService } from './maintenance.service';
import { StorageModule } from '../storage/storage.module';

@Module({
  imports: [StorageModule],
  providers: [MaintenanceService],
})
export class MaintenanceModule {}
