import { z } from 'zod';

export const OutboxEventStatusEnum = z.enum([
  'PENDING',
  'PUBLISHED',
  'FAILED'
]);

export const OutboxEventSchema = z.object({
  id: z.string().uuid(),
  tenant_id: z.string().uuid(),
  aggregate_type: z.string(), // e.g. "document"
  aggregate_id: z.string().uuid(),
  event_type: z.string(), // e.g. "document.ingested"
  payload: z.record(z.any()), // JSONB column
  status: OutboxEventStatusEnum,
  created_at: z.date(),
  published_at: z.date().nullable().optional()
});

export type OutboxEvent = z.infer<typeof OutboxEventSchema>;

// Specific payload shapes for Redis streams
export const DocumentIngestedEventPayloadSchema = z.object({
  document_id: z.string().uuid(),
  storage_path: z.string(),
  priority_queue: z.enum(['high', 'low']),
  compute_weight: z.number(),
});

export type DocumentIngestedEventPayload = z.infer<typeof DocumentIngestedEventPayloadSchema>;
