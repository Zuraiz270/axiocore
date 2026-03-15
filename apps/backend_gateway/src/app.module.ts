import { Module } from '@nestjs/common';
import { AppController } from './app.controller';
import { AppService } from './app.service';

import { AuthModule } from './auth/auth.module';
import { IngestModule } from './ingest/ingest.module';
import { PrismaModule } from './prisma/prisma.module';
import { ScheduleModule } from '@nestjs/schedule';
import { OutboxModule } from './outbox/outbox.module';

@Module({
  imports: [
    ScheduleModule.forRoot(),
    AuthModule, 
    IngestModule, 
    PrismaModule,
    OutboxModule
  ],
  controllers: [AppController],
  providers: [AppService],
})
export class AppModule {}
