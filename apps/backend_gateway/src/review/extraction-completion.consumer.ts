import { Injectable, Logger, OnApplicationBootstrap, OnApplicationShutdown } from '@nestjs/common';
import { RedisService } from '../redis/redis.service';
import { AutoApprovalService } from './auto-approval.service';

@Injectable()
export class ExtractionCompletionConsumer implements OnApplicationBootstrap, OnApplicationShutdown {
  private readonly logger = new Logger(ExtractionCompletionConsumer.name);
  private isRunning = true;
  private readonly STREAM_NAME = 'stream:extraction:complete';
  private readonly GROUP_NAME = 'gateway_completion_group';
  private readonly CONSUMER_NAME = 'gateway_1';

  constructor(
    private readonly redisService: RedisService,
    private readonly autoApprovalService: AutoApprovalService,
  ) {}

  async onApplicationBootstrap() {
    this.logger.log('Starting ExtractionCompletionConsumer listener...');
    await this.redisService.xgroup('CREATE', this.STREAM_NAME, this.GROUP_NAME, '0', true);
    this.poll();
  }

  onApplicationShutdown() {
    this.isRunning = false;
  }

  private async poll() {
    while (this.isRunning) {
      try {
        const results = await this.redisService.xreadgroup(
          this.GROUP_NAME,
          this.CONSUMER_NAME,
          [this.STREAM_NAME],
          1,
          2000
        );

        if (results && results.length > 0) {
          for (const [stream, messages] of results) {
            for (const [id, fields] of messages) {
              // fields is an array of [key, value, key, value...]
              const payload: any = {};
              for (let i = 0; i < fields.length; i += 2) {
                payload[fields[i]] = fields[i + 1];
              }

              this.logger.log(`Received completion event for doc: ${payload.document_id}`);
              
              await this.autoApprovalService.evaluateDocument(payload.document_id);
              
              await this.redisService.xack(this.STREAM_NAME, this.GROUP_NAME, id);
            }
          }
        }
      } catch (err) {
        this.logger.error(`Error in CompletionConsumer poll: ${err.message}`);
        await new Promise(resolve => setTimeout(resolve, 5000));
      }
    }
  }
}
