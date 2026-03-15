import { Injectable, OnModuleDestroy } from '@nestjs/common';
import Redis from 'ioredis';

@Injectable()
export class RedisService implements OnModuleDestroy {
  private readonly client: Redis;

  constructor() {
    this.client = new Redis(process.env.REDIS_URL || 'redis://localhost:6379');
  }

  async get(key: string): Promise<string | null> {
    return this.client.get(key);
  }

  async set(key: string, value: string, expirySeconds?: number): Promise<void> {
    if (expirySeconds) {
      await this.client.set(key, value, 'EX', expirySeconds);
    } else {
      await this.client.set(key, value);
    }
  }

  async del(key: string): Promise<void> {
    await this.client.del(key);
  }

  // Redis Stream Support (Phase 5)
  async xreadgroup(group: string, consumer: string, streams: string[], count = 1, block = 2000): Promise<any> {
    // Note: ioredis uses a slightly different signature for xreadgroup
    // .xreadgroup('GROUP', group, consumer, 'COUNT', count, 'BLOCK', block, 'STREAMS', ...streams, ...ids)
    const streamPairs = streams.flatMap(s => [s, '>']);
    return this.client.xreadgroup('GROUP', group, consumer, 'COUNT', count, 'BLOCK', block, 'STREAMS', ...streams, ...streams.map(() => '>'));
  }

  async xack(stream: string, group: string, id: string): Promise<void> {
    await this.client.xack(stream, group, id);
  }

  async xgroup(command: 'CREATE', stream: string, group: string, id: string = '$', mkstream = true): Promise<void> {
    try {
      if (mkstream) {
        await this.client.xgroup('CREATE', stream, group, id, 'MKSTREAM');
      } else {
        await this.client.xgroup('CREATE', stream, group, id);
      }
    } catch (err) {
      if (!err.message.includes('BUSYGROUP')) throw err;
    }
  }

  onModuleDestroy() {
    this.client.disconnect();
  }
}
