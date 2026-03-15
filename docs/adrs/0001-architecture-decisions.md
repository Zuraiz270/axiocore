# ADR 0001: Foundational Architecture (Kappa + Async Workers)

**Date:** 2026-03-15
**Status:** Accepted

## Context
Axiocore parses complex multi-modal documents. Initial prototypes considered a Lambda architecture with Kafka or BullMQ, and monolithic processing loops. However, LLM inference and deep OCR cascade pipelines are heavily CPU/GPU bound, which catastrophically blocks Node.js event loops. Furthermore, maintaining duplicate codebases for stream (Kafka) vs batch processing was deemed an anti-pattern (The "Lambda Trap").

## Decision
1. **Kappa Architecture via Redis Streams:** We will use Redis Streams as a unified event log. Both real-time API submissions (streams) and bulk historical uploads (batches) are written to the same append-only logs. This unifies the processing logic.
2. **Node/Python Brain-Muscle Split:** 
   - **NestJS (Brain):** Handles HTTP connections, websockets, RLS authentication, rate limiting, and database interactions.
   - **FastAPI (Muscle):** Dedicated Python workers pulling from Redis Streams. Python natively supports Pillow, OCR libraries, ML models, and Presidio without excessive unmarshalling.

## Consequences
**Positive:**
- Complete immunity to Node.js event loop blocking during 5+ second inference tasks.
- Highly scalable. We can add 10 Python worker nodes on GPU instances without modifying the NestJS gateway.
- Simplified state management through a unified event bus.

**Negative:**
- Increases operational complexity (requires maintaining both Node and Python environments). Mitigated via Docker Compose and monorepo management.
