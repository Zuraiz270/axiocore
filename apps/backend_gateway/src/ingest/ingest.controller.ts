import { Controller, Post, Body, UseGuards, Request, BadRequestException } from '@nestjs/common';
import { IngestService } from './ingest.service';
import { JwtAuthGuard } from '../auth/jwt-auth.guard';
import { IngestRequestSchema } from '@opp/shared';

import { ThrottlerGuard } from '@nestjs/throttler';

@UseGuards(JwtAuthGuard, ThrottlerGuard)
@Controller('documents')
export class IngestController {
  constructor(private readonly ingestService: IngestService) {}

  @Post('ingest')
  async ingestDocument(@Request() req, @Body() body: any) {
    // 1. Validate payload using the shared Zod schema
    const validationResult = IngestRequestSchema.safeParse(body);
    if (!validationResult.success) {
      throw new BadRequestException(validationResult.error.errors);
    }
    
    const validatedData = validationResult.data;

    // A2: Hostile Document Admission Validations
    const MAX_FILE_SIZE = 50 * 1024 * 1024; // 50MB
    const MAX_PAGES = 200;
    const ALLOWED_MIMES = [
      'application/pdf',
      'image/png',
      'image/jpeg',
      'image/tiff',
      'image/heic'
    ];

    if (validatedData.file_buffer && validatedData.file_buffer.length > MAX_FILE_SIZE) {
      throw new BadRequestException('File size exceeds the 50MB limit (A2).');
    }

    if (!ALLOWED_MIMES.includes(validatedData.mime_type)) {
      throw new BadRequestException(`Unsupported format: ${validatedData.mime_type}. Allowed: PDF, PNG, JPG, TIFF, HEIC (A2).`);
    }

    // 2. Extract tenant context established by the JwtAuthGuard
    const tenantId = req.user.tenantId;

    // 3. For Phase 1 scaffold, we mock page count (normally extracted via PDF tools)
    const mockPageCount = 5; 
    const mockSourceType = 'digital_native';

    // 4. Push to the Pressure-Aware routing logic
    return this.ingestService.processIngestion(
      validatedData,
      tenantId,
      mockPageCount,
      mockSourceType
    );
  }
}
