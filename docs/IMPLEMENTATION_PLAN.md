# Axiocore V3 Implementation Plan

> **Goal:** Execute the production-grade "Unstructured-to-Ops" document processing engine.
> **Status:** DEFINITIVE — Aligned with the frozen architecture contract.

---

## Phase 1: Core Muscle (Weeks 1–2)
**Focus:** Infrastructure, Gateway Routing, Idempotency, and the Transactional Outbox.

### 1. Database & Infrastructure
*   **Technologies:** PostgreSQL 16, Redis 7.x, MinIO, NestJS (Gateway).
*   **Data Model (`documents` table):**
    *   Columns: `tenant_id` (RLS enforced), `original_filename`, `mime_type`, `file_size_bytes`, `page_count`, `storage_path`.
    *   `status` (ENUM): `INGESTED`, `EXTRACTING`, `PENDING_REVIEW`, `IN_REVIEW`, `APPROVED`, `REJECTED`, `EXTRACTION_FAILED`, `STORED`, `DLQ`. *(Note: `EXTRACTED` is explicitly omitted).*
    *   `priority_queue`: `high` or `low`.
*   **Data Model (`outbox_events` table):** Tracks state transitions for the relay.

### 2. Multi-Tenancy (Day 1)
*   JWT Auth Guard extracts `tenant_id`.
*   Redis-based JWT denylist checked on every request.
*   Every DB transaction explicitly runs `SET LOCAL app.current_tenant`.
*   PostgreSQL Row-Level Security (RLS) is active.
*   Redis keys and MinIO paths strictly scope payloads and files by `tenant_id`.
*   The outbox relay preserves tenant context on publication.

### 3. Ingestion & Outbox Flow (NestJS)
*   **Endpoint:** `POST /documents/ingest`
*   **Idempotency:** Required at ingest using `Idempotency-Key` or content hash.
*   **Pressure-Aware Routing:** Gateway calculates Compute Weight and Lane.
    *   Formula: $W = (\text{Page Count} \times \text{Resolution Factor}) + \text{Modality Weight}$
    *   Constants: Resolution = 1.0 (for 300 DPI), Digital Native = 1.0, Scanned/Photo = 5.0.
    *   Logic: Route to `high_priority_stream` IF $W \le 15$ AND `XLEN(stream:extraction:high) < 10`. Otherwise, route to `low_priority_stream`.
*   **Transactional Outbox (Strict Sequence):**
    1. Insert document metadata row into PostgreSQL.
    2. Insert `outbox_events` row.
    3. Commit the single PostgreSQL transaction.
    4. Separate Relay process publishes to Redis Streams.
    5. Mark outbox row as delivered.

### 4. Smoke Tests
*   Golden ingest flow (upload $\rightarrow$ storage $\rightarrow$ DB $\rightarrow$ Redis stream).
*   Cross-tenant denial test (verify RLS and storage boundary isolation).

---

## Phase 2: Privacy Shield & Reliability (Weeks 3–4)
**Focus:** The Python Worker, Modality Processing, EXIF Stripping, and PII Masks.

### 1. Worker Environment (FastAPI)
*   Separate highly-concurrent Python application.
*   Pulls events from Redis Streams, processing all heavy data operations off the NestJS event loop.
*   Worker executes DB queries explicitly propagating `tenant_id` context.

### 2. Privacy & Artifact Pipeline
*   **Pillow EXIF/GPS Stripping:** Mandatory worker-side step immediately before any processing or persistent storage.
*   **PII Recognition (Presidio):** Worker-side detection of sensitive fields.
*   **Artifact Rules:** 
    *   *Evidence Artifact:* Minimally sanitized source artifact (EXIF stripped) retained for audit/review.
    *   *Derived Processing Artifact:* Generated OCR text, layout JSON, embeddings.
    *   *Training/Eval Artifact:* Must never contain raw PII; strict synthetic placeholder replacement (e.g., "John Doe" $\rightarrow$ "<PERSON_72>").

### 3. Reviewer Locking (Redlock)
*   Worker/Gateway coordinates an Atomic Lease for HITL review.
*   Strict limits: 5-second heartbeat, 15-second absolute expiry.

---

## Phase 3: Extraction Cascade & R&D (Weeks 5–6)
**Focus:** Local-first extraction pipeline and cross-modal defenses.

### 1. The Cascade Architecture
*   **Tier 0 (Direct Parse):** For born-digital files.
*   **Tier 1 (OCRmyPDF):** For generating searchable text layers on basic scans.
*   **Tier 2 (IBM Docling):** For robust structural/table extraction.
*   **Tier 3 (VLM / Heavy OCR):** Benchmark-gated slot. Remains FEATURE-FLAGGED OFF until benchmark winner is verified. (Candidates: PaddleOCR 3.0, DeepSeek-OCR-2, Qwen2.5-VL).

### 2. Multi-Page & Context Controls
*   **Page-Bound Provenance:** Page indices must be tracked alongside chunks for multi-page document binding.
*   **Cross-Modal Consistency:** Calculate similarity ($S$) between extracted numeric text and original crops. If $S < 0.75$, trigger mandatory review escalation (not automatic failure).

---

## Phase 4: Production & Self-Improvement (Week 7+)
**Focus:** Human-in-the-loop review operations and fine-tuning prerequisites.

### 1. HITL Governance & Labeling
*   **Configurable Consensus Labeling:** By default, extractions with values > $5,000 require two human reviewer verifications. This threshold is overrideable per schema/tenant.
*   **Reviewer Monitoring:** Suspiciously fast approvals automatically flagged for second-pass review.

### 2. Criteria-Gated Fine-Tuning
Fine-tuning operations are blocked until the following criteria are met (no calendar-based triggers):
*   Minimum 1,000+ high-signal, approved tags collected.
*   A frozen holdout set is established.
*   Disagreement rates are below defined operational thresholds.
*   Privacy and export-safety checks pass.
*   The model rollback deployment path is fully tested.

---

## Phase 5: Late-Phase Hardening (V4 Backlog)
**Focus:** Operations deferred from V3 scope. Current code must not implement these features until Phase 1-4 are hardened.

*   SISA / Machine unlearning frameworks.
*   Visual prompt injection defense systems.
*   Agentic long-document navigation (Chain-of-Scroll / SCoPE-style logic).
*   Advanced reviewer-quality analytics and label-poisoning defenses.
*   DP-LoRA / Opacus (Differential Privacy) configurations for unconstrained fine-tuning.
