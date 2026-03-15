# Product Requirements Document (PRD)
**Project:** Axiocore V3
**Date:** March 15, 2026

## 1. Product Vision
To build a highly accurate, self-hosted document parsing engine that turns unstructured chaos into fully typed operational data, requiring human intervention only for exceptions or model training loops, with mathematical guarantees of privacy.

## 2. User Personas
1. **The Human Reviewer (HITL):** Needs a split-screen UI showing the original evidence artifact alongside the extracted, editable JSON form. Demands sub-second UI responsiveness and clear highlights of low-confidence fields.
2. **The API Consumer (System User):** External ERP or CRM system POSTing webhooks with raw PDFs attached and expecting a callback with structured JSON.
3. **The Administrator:** Needs to monitor queue depths, DLQ sizes, tenant rate limits, and model drift statistics.

## 3. Functional Requirements (FRs)

### FR1: Ingestion & Routing
* **FR1.1:** System shall accept PDFs, JPEGs, PNGs, and TIFFs up to 50MB.
* **FR1.2:** System shall calculate a `Compute Weight` (Pages x Modality) to route documents to high or low-priority queues based on current pressure.
* **FR1.3:** Gateway shall enforce Idempotency using `Idempotency-Key` headers.

### FR2: Privacy & Preprocessing
* **FR2.1:** System shall strip all EXIF/GPS metadata from incoming image buffers instantly using Python Pillow.
* **FR2.2:** System shall run NLP-based PII detection (Microsoft Presidio) to mask sensitive data with synthetic tokens (e.g., `<PERSON_1>`) before sending to local LLM schema mapping.

### FR3: Extraction Cascade
* **FR3.1:** System shall route digital-native PDFs to Tier 0 (direct layout parsing).
* **FR3.2:** System shall route scanned images through preprocessing (deskew, binarization) and Tier 1 OCR (OCRmyPDF/Docling).
* **FR3.3:** Extraction layer shall map OCR text to a predefined Zod JSON Schema using a local model (e.g., Llama-3-8B).

### FR4: Review & Workflow
* **FR4.1:** Documents must pass through 9 states: `INGESTED`, `EXTRACTING`, `PENDING_REVIEW`, `IN_REVIEW`, `APPROVED`, `REJECTED`, `EXTRACTION_FAILED`, `STORED`, `DLQ`.
* **FR4.2:** Review sessions must be protected by a strict 15-second Atomic Lock (Redis Redlock), renewed every 5 seconds.
* **FR4.3:** High-stakes values (e.g., Invoice Total > $5000) require Consensus Labeling (two distinct reviewers).

## 4. Non-Functional Requirements (NFRs)
* **NFR1 - Security:** Multi-tenant Row-Level Security (RLS) mandated in PostgreSQL. JWT logic must include a Redis-backed denylist.
* **NFR2 - Latency:** Gateway must acknowledge receipt and persist Outbox event in < 500ms. GPU inference p95 target is 5s/page.
* **NFR3 - Scalability:** System must use Redis Streams (Kappa architecture) to seamlessly buffer asynchronous loads without losing state.
* **NFR4 - Resilience:** The Transactional Outbox pattern guarantees that a DB write and message publish never fail independently.
