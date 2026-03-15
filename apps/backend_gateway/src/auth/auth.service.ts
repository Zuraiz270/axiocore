import { Injectable } from '@nestjs/common';
import { JwtService } from '@nestjs/jwt';
import { RedisService } from '../redis/redis.service';

@Injectable()
export class AuthService {
  constructor(
    private readonly jwtService: JwtService,
    private readonly redisService: RedisService,
  ) {}

  async revokeToken(token: string): Promise<void> {
    const payload = this.jwtService.decode(token) as any;
    if (!payload || !payload.exp) {
      // If we can't decode or find expiry, block indefinitely or for a safe default
      await this.redisService.set(`denylist:${token}`, 'revoked', 86400); // 24h fallback
      return;
    }

    const now = Math.floor(Date.now() / 1000);
    const ttl = payload.exp - now;

    if (ttl > 0) {
      await this.redisService.set(`denylist:${token}`, 'revoked', ttl);
    }
  }
}
