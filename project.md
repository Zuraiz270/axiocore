# Axiocore V3 Project Documentation

> [!WARNING]
> This document (`project.md`) is officially deprecated. The early 3,000+ line project sketches and AI critiques from Feb/March 2026 have been archived to preserve context window hygiene and prevent contradictory instructions.

## Definitive Architecture & Plans

The "Unstructured-to-Ops" pipeline architecture is 100% frozen as of **March 2026 (Version 3.2-frozen)**. If you are an AI Coding Agent or a developer looking for architectural rules, database schemas, or workflow definitions, you **MUST** consult the definitive artifacts in the `.gemini/antigravity/brain` directory for this session, specifically:

1. **`axiocore_v3_spec.md`**
   The single source of truth for the stack (NestJS, FastAPI, Postgres, Redis Streams). Contains the exact 9-state pipeline, the transaction outbox rules, and the strict multi-tenant boundaries.

2. **`implementation_plan.md`**
   The phase-by-phase execution checklist (from Phase 1: Core Muscle to Phase 5: V4 Backlog).

3. **`research_report.md`**
   The justification document explaining why Kafka/BullMQ were rejected, why the Lambda architecture was avoided, and why certain VLM components are sequestered to V4.

4. **`task.md`**
   The active build checklist.

*Do not rely on any other text files or historical prompts for architectural decisions.*
