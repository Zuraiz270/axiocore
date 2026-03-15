import { Injectable, UnauthorizedException } from '@nestjs/common';
import { PassportStrategy } from '@nestjs/passport';
import { ExtractJwt, Strategy } from 'passport-jwt';

// Define the shape of our JWT payloads based on the V3 Spec
export interface JwtPayload {
  sub: string;       // The user ID
  tenant_id: string; // The RLS scope
  iat?: number;
  exp?: number;
}

@Injectable()
export class JwtStrategy extends PassportStrategy(Strategy) {
  constructor() {
    super({
      jwtFromRequest: ExtractJwt.fromAuthHeaderAsBearerToken(),
      ignoreExpiration: false,
      secretOrKey: process.env.JWT_SECRET || 'dev-secret-do-not-use-in-prod',
    });
  }

  async validate(payload: JwtPayload) {
    if (!payload.tenant_id) {
      throw new UnauthorizedException('Multi-tenant scope (tenant_id) is missing from the token.');
    }
    
    // Passport attaches this return value to req.user
    return { userId: payload.sub, tenantId: payload.tenant_id };
  }
}
