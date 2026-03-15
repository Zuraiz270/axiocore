# Axiocore V3 — Architecture Specification (FINAL)

> **Status:** DEFINITIVE — Frozen Architecture Contract  
> **Date:** 2026-03-15 | **Version:** 3.2-frozen  
> **Supersedes:** decision_freeze.md, blocker_register.md, rnd_intelligence_brief.md  
> **R&D Validated:** March 2026 OCR R&D Engine (7 tracks, 14 searches, 7 deep-fetches, 9 KG entities)

---

## §1 System Identity

**Axiocore** is an intelligent document processing (IDP) system that extracts structured data from unstructured documents (invoices, receipts, contracts) using a cascade of OCR engines, LLM-powered schema extraction, and mandatory human-in-the-loop review. It is self-hosted, GDPR-first, and designed for multi-tenant SaaS deployment.

### Design Principles
1. **Local-first** — GPU-bound processing runs on owned hardware, not cloud APIs
2. **Review-all (V3)** — Every extraction is reviewed by a human. Trust is earned, not assumed
3. **Privacy by design** — PII is redacted at ingestion, EXIF stripped, data never leaves tenant scope
4. **Event-driven** — Redis Streams as unified event bus (Kappa architecture, no Lambda split)
5. **Fail-safe** — DLQ, idempotency, transactional outbox — no silent data loss

---

## §2 Frozen V3 Stack

| Layer | Technology | Rationale |
|:---|:---|:---|
| API Gateway | NestJS (Node.js 20 LTS) | REST, WebSocket, auth, already in codebase |
| Extraction Service | FastAPI (Python 3.11+) | Offloads GPU-bound OCR/ML from Node event loop |
| Event Bus | Redis Streams 7.x | Consumer groups + PEL, no Kafka overhead |
| Primary DB | PostgreSQL 16 | ACID, JSONB, RLS, partitioning |
| Object Storage | MinIO (S3-compatible) | Self-hosted, shared bucket with tenant-{id}/ prefixes |
| PII Detection | Microsoft Presidio | NER-based entity recognition, open-source |
| Cache / Idempotency | Redis 7.x (same instance) | Keys, locks, session vars |
| Container | Docker Compose (dev), Railway/Vercel (prod) | Existing deployment |

> [!CAUTION]
> **Excluded from V3:** Kafka, RabbitMQ, TimescaleDB, Debezium, Kubernetes, SingleStore.

---

## §3 OCR Cascade

### FastApi Worker Preprocessing & Taxonomy
All Python-native heavy lifting strictly operates in the FastAPI worker (no Pillow/OCR in NestJS).
1. **Mandatory Artifact Stripping:** `Pillow` strips EXIF/GPS at worker ingestion. 
2. **Preprocessing Pipeline:** Deskew (>2° skew) → Sauvola Binarization → Denoising (cv2.fastNlMeansDenoising) → CLAHE.

### OCR Tier Cascade (Local-First Only)
```
Document → Direct Parse (Tier 0: native text layer via pdfjs-dist / pdfplumber)
              │ yes → scrub PII via Presidio → proceed
              │ no → [Preprocessing Pipeline] ↓
          OCRmyPDF (Tier 1: Searchable PDF generation / Fast Tesseract OCR)
              │ fallback / complex layout (tables) ↓
          Docling (Tier 2: Granite-258M, 114ms/page L4, 97.9% table accuracy)
              │ fallback for heavily warped/multilingual ↓
          PaddleOCR 3.0 (Tier 2.5)
              │
          [Tier 3 VLM Benchmark Slot - Feature Flagged OFF (e.g. DeepSeek-OCR-2, Qwen2.5-VL)]
```

> [!IMPORTANT]
> **R&D Amendment #2:** PaddleOCR-VL (Vision-Language variant) topped CodeSOTA OmniDocBench 2026. Must run B-10 head-to-head benchmark against Docling before finalizing Tier 2 dominance. If PaddleOCR-VL wins on our internal corpus, prioritize it.

**Post-OCR stitching:** Concatenate all pages with `\n---PAGE {n}---\n` delimiters → **`marker-pdf`** converts to clean markdown *(R&D Amendment #5)* → LLM schema extraction on formatted markdown (handles cross-page refs, better LLM comprehension than raw OCR text).

---

## §4 Workflow State Machine

```text
[*] → INGESTED → [Compute Weight Score Router] → EXTRACTING (High or Low Priority Queue) → PENDING_REVIEW → IN_REVIEW → APPROVED → STORED → [*]
                       ↓                                                                       ↓
                EXTRACTION_FAILED (retry ×3)                                              REJECTED → PENDING_REVIEW
                       ↓
                      DLQ (manual investigation)
```
*(Note: `EXTRACTED` state has been explicitly removed. `STORED` is the terminal downstream action.)*

### Pressure-Aware Gateway Routing
Gateway calculates a Compute Weight Score ($W$) before queuing:
$W = (\text{Page Count} \times \text{Resolution Factor}) + \text{Modality Weight}$
Constants: Resolution = 1.0 (for 300 DPI), Digital Native = 1.0, Scanned/Photo = 5.0.
If $W \le 15$ AND `XLEN(stream:extraction:high) < 10`, the document is routed to `high_priority_stream`. Otherwise, it routes to a background `low_priority_stream` to prevent heavy scans from blocking fast digital-native documents.

| Rule | Value |
|:---|:---|
| Review policy (V3) | Review-all. No auto-approval. |
| Optimistic lock SQL | `UPDATE documents SET reviewer_id=$1, locked_at=NOW() WHERE id=$2 AND (reviewer_id IS NULL OR locked_at < NOW()-'15 seconds')` |
| Lock timeout | 15 seconds (5s heartbeat extends) |
| Max retries | 3 (exponential: 5s → 25s → 125s) |
| Re-extraction | Manual trigger only. Creates new version, never overwrites. |

---

## §5 Behavioral Policies (A1–A14)

### A1. Stale Review Protection
Review submission includes `extraction_version`. Server: `UPDATE … WHERE id=$1 AND extraction_version=$2`. 0 rows → 409 Conflict.

### A2. Hostile Document Admission
File size ≤50MB, pages ≤200, formats: pdf/png/jpg/tiff/heic. Password-protected → 422. MIME validated via `python-magic`. *Limits subject to corpus calibration (B-10).*

**R&D Amendment #3 — Digital Signature Verification:** Before OCR processing, verify digital signatures using `pyHanko`. Valid signature → store verification result in `extraction_provenance`. Invalid/missing → flag for reviewer awareness (not auto-reject).

**R&D Amendment #4 — PDF Metadata Forensics:** At ingestion, extract `CreationDate`, `ModDate`, `Producer`, and font embedding metadata via `pdfplumber`. Flag documents with: (a) `ModDate` significantly after `CreationDate` without matching Producer, (b) unusual/missing font embeddings, (c) known forgery tool fingerprints. Results stored in `document_metadata_audit`.

### A3. Evidence Conflict Resolution (Configurable Business Logic)
Precedence is strictly configurable business logic, NOT hardcoded. Default baseline: `structured_attachment > image_ocr > email_body > metadata`. Conflicts shown in review UI with source tags — reviewer MUST select the canonical value. All stored in `extraction_evidence`.

### A4. Immutable Version Tuple
Every extraction stores: `{schema_version, extractor_version, ocr_engine_version, model_version, prompt_template_hash, artifact_hash_set}` in `extraction_provenance`. Append-only.

### A5. Reviewer Crash Recovery (Atomic Lease)
Reviewer UI failure must fail fast to prevent stalled pipelines. Redis Redlock atomic lease used for document locking. If the 5-second UI heartbeat fails, Redis automatically expires the lock after 15 seconds, returning the doc to `PENDING_REVIEW`.

### A6. Prompt Injection Quarantine
1. Structural isolation: `<SYSTEM>/<EVIDENCE>/<SCHEMA>` delimiters
2. Input sanitization: strip `ignore previous`, `system:`, `<|im_start|>`
3. Output validation: Zod schema enforcement
4. Quarantine: >3 injection patterns → manual-only flag
5. **[R&D Amendment]** Add modality-specific sanitization for image/audio-based injection vectors

### A7. Cost & Latency Budget

| Metric | Target |
|:---|:---|
| p95 extraction (GPU) | 5s/page |
| p95 extraction (CPU) | 25s/page |
| Max cost/document | $0.02 |
| GPU SKU | NVIDIA L4 (24GB) or T4 (16GB) |
| Max concurrent | 10 (GPU), 3 (CPU) |

### A8. Label Quality Governance
No fine-tuning until 2000+ approved docs. 10% holdout set (frozen). Reviewer changes >50% fields → "High Correction" → quality review before training. Track `correction_rate` per reviewer (flag >30%). Append-only with deletion registry.

### A9. Reviewer Heartbeat (Fail-fast)
UI sends WebSocket or PATCH `/documents/{id}/heartbeat` every 5 seconds. This extends the fast-expiring Redis Redlock. Heartbeat failure > 15 seconds terminates review session automatically.

### A15. Cross-Modal Consistency Scoring *(V3 Defense-in-Depth)*
To detect VLM hallucinations on blurred/complex layouts: Calculate Cosine Similarity ($S$) between text embeddings of extracted claims and image embeddings of the source crop. If $S < 0.75$, trigger mandatory review escalation in the HITL portal to warn the reviewer (not an automatic failure).

### A16. Privacy Boundary Strictness
Raw upload handling is distinct from sanitized persistence:
1. **Raw Storage:** Original documents are securely stored in MinIO `raw/` restricted buckets immediately upon ingestion.
2. **Worker Pre-Processing:** Before any downstream analysis, worker-side processing MUST perform EXIF/GPS stripping via `Pillow`.
3. **Derived Storage:** Only synthesized/scrubbed text representations enter the extraction schema or training sets.
Raw assets are accessed *only* by the HITL Review UI via ephemeral, signed URL leases.

### A10. Schema-Specific Precedence Override
Per-schema `schema_precedence_rules` config. Review UI shows active rule. Example: "correction_email" → `email_body > structured_attachment`.

### A11. Restore-Time Deletion Replay
On ANY backup restore, apply `deletion_registry` before app starts:
```sql
DELETE FROM documents d USING deletion_registry dr
WHERE d.id = dr.document_id AND dr.status = 'completed';
```
MinIO: iterate registry, re-delete objects.

### A12. Immutable Review Tuple
Append-only: `{extraction_version, schema_version, ocr_engine_version, model_version, prompt_template_hash, artifact_hash_set, reviewer_ui_version}`.

### A13. JWT Revocation *(R&D Amendment)*
Stolen JWT + RLS bypass is an unmitigated risk. V3 must implement a Redis-based JWT denylist checked on every authenticated request. Tokens added to denylist on: logout, password change, admin revocation. TTL = token expiry.

### A14. MinIO Orphan Cleanup *(R&D Amendment)*
When MinIO upload succeeds but Postgres insert fails: orphan objects accumulate. Nightly cron compares MinIO object keys against `documents` table. Orphans older than 24h → delete + log.

---

## §6 Blocker Register

> Every item MUST be resolved before V3 ships. Source: ChatGPT + Gemini critiques.

### 🔴 Critical (resolve before first integration test)

| ID | Blocker | Acceptance Test |
|:---|:---|:---|
| **B-01** | Stale Review Submission | Submit v1 review after re-extraction to v2 → 409 Conflict |
| **B-02** | Hostile Document Admission | 51MB→413, password PDF→422, renamed .exe→415, 201-page→422 |
| **B-03** | Evidence Conflict Resolution | 3 conflicting "total" values → all shown with sources, reviewer selects canonical |
| **B-04** | Version Tuple Capture | Re-extraction with new prompt → new provenance row, old unchanged |
| **B-05** | Reviewer Crash Recovery | Wait 16s with no heartbeat → doc returns to PENDING_REVIEW |
| **B-13** | Backup Restore Revives Erased Docs | Restore pre-erasure backup → erased doc not queryable |

### 🟡 High (resolve before HITL goes live)

| ID | Blocker | Acceptance Test |
|:---|:---|:---|
| **B-06** | Prompt Injection Quarantine | Inject "Ignore all previous instructions" → output conforms to schema, doc flagged |
| **B-07** | Cost & Latency Budget | 100-page on L4: p95 < 500s total, cost < $2 |
| **B-08** | Label Quality Governance | 100 approved docs → 10 held out; 60% field changes → "High Correction" flag |
| **B-09** | Tenant Isolation Beyond RLS | Modify signed URL to tenant B path → 403; Redis query for tenant B → not found |
| **B-10** | Internal Corpus Benchmark | 50 invoices + ground truth → F1 report, tier < 0.85 → alert |
| **B-14** | Reviewer Lock Expiration | Heartbeat 15s → lock valid; stop heartbeat 16s → lock released |
| **B-15** | Review Invalidation on Re-extraction | Re-extract during review → WebSocket notification, submit disabled |

### 🟠 Medium (resolve before GA)

| ID | Blocker | Acceptance Test |
|:---|:---|:---|
| **B-11** | Multi-Page Context Loss | 4-page invoice: vendor p1, total p4 → both extracted with page sources |
| **B-12** | Backpressure Gateway *(+ NIS2 Security)* | XLEN > 10000 → 429 with Retry-After, no documents dropped. **R&D Amendment #6:** Frame as NIS2 2025 security requirement — add WAF rate-limiting to ingestion endpoint (not just performance). |

---

## §7 Implementation Patterns

### 7.1 Transactional Outbox
**Strict Transaction Sequence (No Dual-Writes):**
1. `BEGIN` PostgreSQL Transaction.
2. Insert document metadata row into `documents`.
3. Insert event row into `outbox_events`.
4. `COMMIT` the transaction.
5. A separate asynchronous relay polling service reads un-published rows and publishes (`XADD`) to Redis Streams, then marks the outbox row delivered.

### 7.2 Idempotency Interceptor
```
Client → POST /api/documents/approve (Header: Idempotency-Key: uuid-v4)
  → Redis GET idempotency:{tenant}:{key}
  → Found? Return cached response (200)
  → Not found? Process → SET NX idempotency:{key} {response} EX 86400
```

### 7.3 Dead Letter Queue
```
Main: document:extraction → Consumer fails ×3
  → XPENDING (find idle) → XCLAIM (reassign) → 3rd fail → XADD dlq + XACK main
  → Alert: XLEN(dlq) > 0 → Slack webhook
  → Admin: inspect + retry/discard
```

### 7.4 Multi-Tenant Isolation
```
Request → NestJS middleware → tenant_id from JWT
  → AsyncLocalStorage.run({ tenantId })
  → SET LOCAL app.current_tenant = '{tenant_id}'
  → RLS policy: USING (tenant_id = current_setting('app.current_tenant')::uuid)
  → Redis keys: tenant:{id}:*, MinIO: tenant-{id}/, Logs: tenantId field
```

### 7.5 GDPR Cascade Deletion
```
Erasure Request → 1. PostgreSQL DELETE (documents, extractions, audit_logs)
                → 2. MinIO: mc rm tenant-{id}/documents/{doc-id}/*
                → 3. Redis: DEL cache:extraction:{doc-id}
                → 4. Training Registry: mark "erased" in deletion_registry
                → 5. Audit: INSERT INTO erasure_audit
```

---

## §8 Retention Policy

| Data | Retention | Deletion |
|:---|:---|:---|
| Raw docs (MinIO) | Until erasure/offboarding | `mc rm --recursive` |
| Extractions (PG) | Indefinite | CASCADE on erasure |
| EXIF metadata | 0s (stripped at ingestion) | Never stored |
| PII text | Replaced at ingestion (Presidio) | N/A |
| Redis Stream entries | 7 days (XTRIM) | Nightly |
| Outbox rows | 7 days | Partition drop |
| Idempotency keys | 24h TTL | Automatic |
| Audit logs | 1 year | Cold S3 archive |
| Backups | 30 days rolling | + deletion replay on restore |

---

### Phase 5 (Implemented & Verified)
Advanced agentic components moved from backlog to core production infrastructure:

| Feature | Implementation | Rationale |
|:---|:---|:---|
| DP-LoRA (Opacus) | `TrainingService` (Python) | Privacy-preserving fine-tuning via PEFT + Opacus. |
| Auto-Approval (HOTL) | `AutoApprovalService` (NestJS) | Confidence-based automated approval (>95%). |
| Agentic Navigation | `AgenticNavigator` (Python) | "Chain-of-Scroll" sparse page selection for long docs. |

### Future Backlog (V6+)
| Deferred Feature | Trigger / Rationale |
|:---|:---|
| SISA / Machine Unlearning | Label-poisoning defense and erasure verification. |
| Visual Prompt Injection | Advanced adversarial blocking and multimodal sanitization. |
| VLM Tier 3 Stabilization | Benchmarking required for full production rollout. |

---

## §10 R&D Validation Summary (March 2026)

### Run 1: General Architecture R&D
| Finding | Decision |
|:---|:---|
| Gemini 3 Pro leads at 88% accuracy (800-doc benchmark) | **INVESTIGATE** — accuracy varies 55+ pts by domain. Our corpus benchmark (B-10) is the real test. |
| DataFilter reduces prompt injection to near-zero | **ADOPT V3** — added to A6, amends B-06 resolution |
| DP-LoRA/DP-FedLoRA/PrivLoRA validated | **DEFER V4** — confirms plan, no action needed now |
| Multimodal injection: 82% success vs text-only | **ADOPT V3** — added A6.5 modality sanitization |
| V3 pattern stack: 0 GitHub references found | **ACKNOWLEDGE** — our stack is novel, must build internal docs |
| NestJS+Redis Streams DLQ guide exists (oneuptime.com) | **USE** — reference implementation for §7.3 |

### Run 2: OCR-Specific R&D (7-track engine, 14 searches, 7 deep-fetches)
| Finding | Decision |
|:---|:---|
| PaddleOCR-VL tops OmniDocBench 2026 | **EVALUATE** — run B-10 head-to-head vs Docling |
| Preprocessing (deskew+binarize+denoise) boosts CER 5-20% | **ADOPT V3** — added to §3 preprocessing pipeline |
| `marker-pdf` converts OCR to markdown for better LLM input | **ADOPT V3** — added to §3 post-OCR stitching |
| `pyHanko` verifies digital signatures (open-source) | **ADOPT V3** — added to A2 hostile document admission |
| PDF metadata forensics detects tampering | **ADOPT V3** — added to A2 |
| NIS2 2025 requires upload security beyond backpressure | **ADOPT V3** — B-12 reframed as security requirement |
| GDPR: self-hosted OCR = compliant by design | **CONFIRMED** — no gaps found |
| No dominant open-source forgery detection tool exists | **ACKNOWLEDGE** — cross-modal scoring (A15) is our best defense |
| 0 GitHub results for our full cascade design | **CONFIRMED** — Axiocore OCR pipeline is novel |

---

## §11 Cost Budget (V3 Target)

| Item | Monthly | Notes |
|:---|:---|:---|
| GPU (L4 spot) | ~$200 | 1× single GPU, on-demand scaling |
| PostgreSQL (managed) | ~$50 | Railway or Supabase |
| Redis (managed) | ~$30 | Single instance |
| MinIO (self-hosted) | Storage cost only | On same infrastructure |
| Monitoring (Grafana Cloud free) | $0 | Up to 50GB telemetry |
| **Total** | **~$280/mo** | Before 10k docs/month |

---

## §12 Next Actions (Sequential Build Priority)

Under the Solo Dev + AI Agent protocol, execution will proceed in strict sequence:

1. **Phase 1: Core Muscle (Modality Router & Gateway)**
   - Scaffold NestJS API Gateway.
   - Implement Stripe-style Idempotency Keys to prevent duplicate writes at ingestion.
   - Implement Compute Weight Score ($W$) logic to route digital-native vs scanned documents immediately.
   - Establish the Redis Streams foundation for high/low priority queues.

2. **Phase 2: Privacy Shield (Synthetic Generator)**
   - Deploy FastAPI extraction worker.
   - Implement Microsoft Presidio pipeline to swap PII (e.g., "Ali Ahmed" → "Synthetic_User_72") at ingestion.
   - Build Redlock atomic lease (5s heartbeat / 15s timeout) for the review portal.

3. **Phase 3: Extraction Cascade & Cross-Modal Defense**
   - Implement preprocessing pipeline (deskew → Sauvola binarize → denoise → CLAHE).
   - Integrate Docling and PaddleOCR. Run B-10 benchmark.
   - Add `marker-pdf` for post-OCR markdown formatting before LLM extraction.
   - Implement consistency scoring between text extraction and image crops ($S < 0.75$).

4. **Phase 4: Hardening & HITL Portal**
   - Implement Configurable Consensus Labeling for high-stakes extractions (>$5,000).
   - Build Reviewer Analytics and fast-approval flagging algorithms.

---

## Execution Protocol

**Staffing Structure:** Solo Developer (Review/Approval) + Axiocore AI Agent (Execution)
**Rule:** All code, infrastructure, database migrations, and R&D will be built, configured, and tested by the AI Agent under the strict technical review of the Solo Developer.

| Role | Name | Status |
|:---|:---|:---|
| **System Lead** | Solo Developer | Approved (March 2026) |
| **Execution Engine** | Axiocore AI Agent | Ready for deployment |
