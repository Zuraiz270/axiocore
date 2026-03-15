import { z } from 'zod';

export const DocumentStatusEnum = z.enum([
  'INGESTED',
  'EXTRACTING',
  'PENDING_REVIEW',
  'IN_REVIEW',
  'APPROVED',
  'REJECTED',
  'EXTRACTION_FAILED',
  'STORED',
  'DLQ',
]);

export type DocumentStatus = z.infer<typeof DocumentStatusEnum>;

export const DocumentSchema = z.object({
  id: z.string().uuid(),
  tenant_id: z.string().uuid(),
  original_filename: z.string().min(1),
  mime_type: z.string(),
  file_size_bytes: z.number().positive(),
  page_count: z.number().positive(),
  storage_path: z.string(),
  status: DocumentStatusEnum,
  priority_queue: z.enum(['high', 'low']),
  reviewer_id: z.string().uuid().nullable().optional(),
  locked_at: z.date().nullable().optional(),
  extraction_version: z.number().int().default(1),
  schema_type: z.string(),
  source_type: z.string(),
  artifact_hash_set: z.string().nullable().optional(),
  created_at: z.date(),
  updated_at: z.date(),
});

export type Document = z.infer<typeof DocumentSchema>;

export const IngestRequestSchema = z.object({
  file_buffer: z.any(), // Handled by multer in NestJS, typed as any here for validation bypass
  original_filename: z.string(),
  mime_type: z.string(),
  schema_type: z.string(), // what type of document are we trying to extract? e.g. "invoice"
});

export type IngestRequest = z.infer<typeof IngestRequestSchema>;
