import { ExecutionContext, Injectable, UnauthorizedException } from '@nestjs/common';
import { AuthGuard } from '@nestjs/passport';
import Redis from 'ioredis';

@Injectable()
export class JwtAuthGuard extends AuthGuard('jwt') {
  private readonly redisClient: Redis;

  constructor() {
    super();
    // In a real app we would inject this, but for the Phase 1 scaffold this establishes the connection.
    this.redisClient = new Redis(process.env.REDIS_URL || 'redis://localhost:6379');
  }

  async canActivate(context: ExecutionContext): Promise<boolean> {
    // 1. Run the standard Passport JWT validation (from JwtStrategy)
    const canActivate = await super.canActivate(context);
    if (!canActivate) {
      return false;
    }

    const request = context.switchToHttp().getRequest();
    
    // 2. Extract the raw token from the header for the denylist check
    const authHeader = request.headers.authorization;
    if (!authHeader || !authHeader.startsWith('Bearer ')) {
      throw new UnauthorizedException('Invalid authorization header format');
    }
    
    const token = authHeader.split(' ')[1];

    // 3. Redis Denylist check (from Axiocore V3 Spec: Security)
    const isRevoked = await this.redisClient.get(`denylist:${token}`);
    if (isRevoked) {
      throw new UnauthorizedException('This session has been revoked.');
    }

    return true;
  }
}
