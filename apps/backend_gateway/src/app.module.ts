import { Module } from '@nestjs/common';
import { AppController } from './app.controller';
import { AppService } from './app.service';

import { AuthModule } from './auth/auth.module';
import { IngestModule } from './ingest/ingest.module';
import { PrismaModule } from './prisma/prisma.module';
import { ScheduleModule } from '@nestjs/schedule';
import { OutboxModule } from './outbox/outbox.module';
import { RedisModule } from './redis/redis.module';
import { StorageModule } from './storage/storage.module';
import { MaintenanceModule } from './maintenance/maintenance.module';
import { ThrottlerModule } from '@nestjs/throttler';
import { ReviewModule } from './review/review.module';

@Module({
  imports: [
    ScheduleModule.forRoot(),
    ThrottlerModule.forRoot([{
      ttl: 60000,
      limit: 10,
    }]),
    AuthModule, 
    IngestModule, 
    PrismaModule,
    OutboxModule,
    RedisModule,
    StorageModule,
    MaintenanceModule,
    ReviewModule
  ],
  controllers: [AppController],
  providers: [AppService],
})
export class AppModule {}
