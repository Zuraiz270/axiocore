# Axiocore V3 Tech Stack

**Status:** FROZEN (March 2026)

## 1. Application Layer
* **NestJS (Node.js 20 LTS):** Primary API Gateway. Handles JWT authentication, Idempotency, RLS propagation, and Transactional Outbox routing.
* **FastAPI (Python 3.11+):** High-throughput extraction worker. Offloads heavy CPU/GPU tasks (EXIF stripping, OCR, LLM inference) away from Node.js event loops.
* **Next.js (React 18+):** Frontend application serving the HITL (Human-In-The-Loop) review portal using WebSockets/SSE for real-time queue updates.

## 2. Data & Storage Layer
* **PostgreSQL 16:** Operational database. Heavily utilizes JSONB for flexible schema extraction payloads, and Row-Level Security (RLS) for absolute tenant isolation.
* **Redis 7.x:** In-memory speed layer. Powers three key components:
  1. **Redis Streams:** The unified event broker handling High/Low priority document processing queues (Kappa architecture).
  2. **Redlock:** Distributed locking mechanism for assigning 15-second Review leases.
  3. **Idempotency/Denylist Cache:** Storing processed UUIDs and blocked JWTs.
* **MinIO:** Self-hosted S3-compatible object storage. Stores raw evidence documents strictly grouped under `tenant-{id}/raw/` bucket prefixes.

## 3. AI & Privacy Layer
* **Microsoft Presidio:** Modular PII redaction engine used locally to swap real names/numbers with synthetic tokens.
* **Pillow & python-magic:** Native Python libraries utilized prior to analysis to strip Exif data and validate safe MIME payloads to prevent path traversal/polyglot attacks.
* **OCR Cascade:** `pdfjs-dist` (Digital Text) -> `OCRmyPDF` (Simple Scans) -> `Docling/PaddleOCR 3.0` (Complex Layouts/Scan defects).
* **Local Schema Extractor:** vLLM or Ollama serving Llama-3-8B-Instruct (or equivalent local SLM) using strict Zod outputs to parse Markdown/OCR to predefined JSON schemas.
* **Fine-Tuning (DP-LoRA):** `PEFT` (Parameter-Efficient Fine-Tuning) and `Opacus` (Differential Privacy Engine for PyTorch) for secure, local model adaptation.
* **Intelligent Navigation:** `PyMuPDF` (fitz) for sparse page selection and heuristic-based Chain-of-Scroll optimizations.

## 4. Infrastructure & Ops
* **Docker / Docker Compose:** Containerization for local development parity and seamless CI/CD integration.
* **Prisma or Drizzle ORM:** Type-safe database management interacting intimately with Postgres RLS context.
* **TurboRepo / pnpm Workspace:** Monorepo management for code sharing across `@opp/gateway`, `@opp/worker`, `@opp/frontend`, and `@opp/shared`.
