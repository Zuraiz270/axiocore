import { Controller, Post, Headers, UnauthorizedException, UseGuards, Get, Request } from '@nestjs/common';
import { AuthService } from './auth.service';
import { JwtAuthGuard } from './jwt-auth.guard';

@Controller('auth')
export class AuthController {
  constructor(
    private readonly authService: AuthService,
  ) {}

  @Post('logout')
  @UseGuards(JwtAuthGuard)
  async logout(@Headers('authorization') auth: string) {
    if (!auth || !auth.startsWith('Bearer ')) {
      throw new UnauthorizedException('Invalid token format');
    }

    const token = auth.split(' ')[1];
    await this.authService.revokeToken(token);

    return { message: 'Successfully logged out and session revoked.' };
  }
}
