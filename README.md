# Axiocore V3: Unstructured-to-Ops Engine

Axiocore is a production-grade intelligent document processing (IDP) system that extracts structured data from mess, unstructured sources (invoices, receipts, contracts). It relies on a local-first OCR cascade, LLM-powered schema extraction, and mandatory human-in-the-loop (HITL) review.

## 🏗 Architecture & Documentation
The entire system architecture has been frozen strictly as of March 2026. **Do not deviate from the core blueprint.** 

If you are a new developer or an AI Agent contributing to this repository, your first step is to read the definitive spec documents located in the `.gemini/antigravity/brain/` session artifacts for the current build:

1. **`axiocore_v3_spec.md`**: The frozen technical specification. Details the 9-state pipeline, the exact sequence for the transactional outbox, compute weight routing rules, and multi-tenant constraints.
2. **`implementation_plan.md`**: The phase-by-phase execution guide currently driving development (Phase 1: Core Muscle -> Phase 4: Production).
3. **`research_report.md`**: Context on *why* technical decisions were made (e.g., sticking to Redis Streams over Kafka, maintaining strict FastAPI/NestJS boundary).

*Note: The legacy `project.md` file contains historical context but is officially deprecated regarding V3 architecture.*

## 💻 Tech Stack
* **API Gateway & Orchestration:** NestJS (TypeScript, Node.js 20 LTS)
* **Extraction Worker:** FastAPI (Python 3.11+, handles Pillow, Presidio, OCR)
* **Primary Database:** PostgreSQL 16 (RLS multi-tenancy)
* **Event Backbone:** Redis Streams 7.x (Kappa architecture, High/Low queue routing)
* **Object Storage:** MinIO (S3-compatible, self-hosted)

## 🚀 Getting Started (Phase 5 Complete)
Axiocore V3 is now at **Phase 5: Intelligence & Efficiency**. 

The system has transitioned from a static pipeline to an agentic platform with:
- **Self-Improving AI:** Privacy-preserving fine-tuning via DP-LoRA.
- **Auto-Approvals (HOTL):** Safety-gated automation for high-confidence extractions.
- **Chain-of-Scroll:** Intelligent sparse navigation for large multi-page PDFs.

Run the foundation services using Docker:
```bash
docker-compose up -d postgres redis minio
```

Followed by starting the NestJS orchestration gateway:
```bash
pnpm install
pnpm dev --filter=@opp/gateway
```

3. **Start the Python Worker:**
```bash
cd workers/python-worker
source venv/bin/activate
python src/main.py
```

## 🧪 Testing & Verification
Axiocore uses a phase-by-phase verification strategy.

### 1. Automated System Check
Run the master verification suite to check all 5 phases (Infrastructure, Privacy, Extraction, Hardening, Intelligence):
```bash
cd workers/python-worker
$env:PYTHONPATH="."; python -m pytest master_system_verify.py
```

### 2. Manual Smoke Test
Upload a document via the Gateway and monitor the Redis stream:
```bash
# Monitor the high-priority stream
redis-cli XREAD BLOCK 0 STREAMS stream:extraction:high $
```

## 📂 Project Structure
```text
├── apps/
│   └── backend_gateway/      # NestJS: Auth, Ingest, HITL Review, Redis Relay
├── workers/
│   └── python-worker/        # FastAPI: OCR Cascade (Tier 0-3), PII, DP-LoRA
├── packages/
│   └── shared/               # Zod schemas, TS interfaces, Shared Logic
├── docs/
│   ├── ARCHITECTURE.md       # Definitive technical specification
│   ├── adrs/                 # Architectural Decision Records (ADR 001-004)
│   └── handoffs/             # Phase-specific execution logs
└── docker-compose.yml        # Services: PG, Redis, MinIO
```

## 🔒 Security & Compliance
Axiocore is built with **"Privacy by Design"** adhering rigidly to GDPR guidelines:
- **No Cloud VLMs:** All extractions run locally on bare-metal GPUs to prevent data exfiltration.
- **Mandatory Exif Stripping:** Raw images are stripped using `Pillow` before any processing.
- **Data Masking:** OCR output passes through Microsoft Presidio for synthetic PII replacement.
- **Day-1 Multi-Tenancy:** PostgreSQL RLS and strict JWT validation securely partition data.
