# LLM Agent Findings & Constraints

*Use this file to store hard-won lessons and constraints so the LLM doesn't hallucinate or forget decisions across session boundaries.*

## Core Findings
1. **The Lambda Trap is real:** Do not suggest Kafka. We strictly use Redis Streams for both batch and real-time processing to maintain a unified codebase in Python.
2. **Node.js blocks on ML:** 100% of OCR, Exif stripping, and LLM inference *must* run in the FastAPI worker. NestJS only handles bytes, authentication, and passing references.
3. **Redlock is non-negotiable:** Review sessions must lock the document for exactly 15 seconds. If the heartbeat fails, the document immediately returns to `PENDING_REVIEW`.

## Reference Materials
- Always refer to `docs/ARCHITECTURE.md` for the single source of truth.
- Always implement the transaction outbox for any state change to ensure Postgres and Redis stay synchronized.
