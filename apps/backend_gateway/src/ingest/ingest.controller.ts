import { Controller, Post, Body, UseGuards, Request, BadRequestException } from '@nestjs/common';
import { IngestService } from './ingest.service';
import { JwtAuthGuard } from '../auth/jwt-auth.guard';
import { IngestRequestSchema } from '@opp/shared';

@Controller('documents')
export class IngestController {
  constructor(private readonly ingestService: IngestService) {}

  @UseGuards(JwtAuthGuard)
  @Post('ingest')
  async ingestDocument(@Request() req, @Body() body: any) {
    // 1. Validate payload using the shared Zod schema
    const validationResult = IngestRequestSchema.safeParse(body);
    if (!validationResult.success) {
      throw new BadRequestException(validationResult.error.errors);
    }
    
    const validatedData = validationResult.data;

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
