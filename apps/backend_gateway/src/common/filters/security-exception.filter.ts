import { ExceptionFilter, Catch, ArgumentsHost, HttpException, HttpStatus, Logger } from '@nestjs/common';
import { Request, Response } from 'express';

@Catch(HttpException)
export class SecurityExceptionFilter implements ExceptionFilter {
  private readonly logger = new Logger('SecurityAudit');

  catch(exception: HttpException, host: ArgumentsHost) {
    const ctx = host.switchToHttp();
    const response = ctx.getResponse<Response>();
    const request = ctx.getRequest<Request>();
    const status = exception.getStatus();

    if (status === HttpStatus.TOO_MANY_REQUESTS) {
      const tenantId = (request as any).user?.tenantId || 'anonymous';
      const ip = request.ip;
      
      this.logger.warn(
        `[NIS2 SECURITY EVENT] Rate limit exceeded. Tenant: ${tenantId}, IP: ${ip}, Path: ${request.url}`
      );
    }

    response.status(status).json({
      statusCode: status,
      timestamp: new Date().toISOString(),
      path: request.url,
      message: exception.message,
    });
  }
}
