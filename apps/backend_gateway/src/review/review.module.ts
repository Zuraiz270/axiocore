import { Module } from '@nestjs/common';
import { ReviewService } from './review.service';
import { ReviewController } from './review.controller';
import { RedisModule } from '../redis/redis.module';
import { AutoApprovalService } from './auto-approval.service';
import { ExtractionCompletionConsumer } from './extraction-completion.consumer';

@Module({
  imports: [RedisModule],
  controllers: [ReviewController],
  providers: [ReviewService, AutoApprovalService, ExtractionCompletionConsumer],
  exports: [ReviewService, AutoApprovalService],
})
export class ReviewModule {}
