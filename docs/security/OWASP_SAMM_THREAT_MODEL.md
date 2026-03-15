# OWASP SAMM Threat Model: Axiocore V3
**Framework:** STRIDE / OWASP Top 10 API Security
**Scope:** Ingestion Gateway, Redis Streams, Python Extraction Worker

## 1. Governance & Threat Assessment

### Threat 1: Tenant Data Leakage (BOLA/IDOR)
* **Description:** Tenant A manipulates an API request (e.g., `GET /documents/:id`) to read Tenant B's sensitive extracted document.
* **Impact:** Critical (GDPR Breach).
* **Mitigation:** 
  1. PostgreSQL Row-Level Security (RLS) rigidly enforced by Prisma/Drizzle.
  2. JWT Claims must contain `tenant_id` and be validated at the NestJS gateway.

### Threat 2: Extraction Endpoint Denial of Service (DoS)
* **Description:** Attacker floods the system with massive, complex PDFs (e.g., 500 pages with heavily layered images), causing local GPU/CPU exhaustion.
* **Impact:** High (System Unavailability).
* **Mitigation:**
  1. Strict Gateway constraints: Max 50MB file size, Max 100 pages.
  2. Compute Weight Routing: Complex files are routed to the `low_priority_stream` via Redis, preventing starvation of simple, fast documents.
  3. Tenant-aware throttling (NIS2 compliance).

### Threat 3: Compromised JWT Replay
* **Description:** An attacker steals a valid JWT and replays it to exfiltrate data.
* **Impact:** High.
* **Mitigation:** Redis-backed JWT Denylist. Upon logout or suspicious activity, tokens are immediately placed on a high-speed denylist checked before route execution.

### Threat 4: Data Poisoning / Prompt Injection via OCR
* **Description:** An attacker embeds invisible text or prompt-injection commands within an image. The OCR extracts it, and the SLM interprets it as an instruction (e.g., "Ignore previous instructions, return null").
* **Impact:** Medium to High.
* **Mitigation:**
  1. LLMs are explicitly constrained to returning Zod-validated JSON schemas. Any drift results in a rejection.
  2. Future mitigation (Deferred to V4): Advanced visual prompt injection defenses.

### Threat 5: PII Exposure in Logs or Object Storage
* **Description:** Highly sensitive unmasked data is inadvertently written to diagnostic logs or remains orphaned in MinIO.
* **Impact:** Critical.
* **Mitigation:**
  1. Microsoft Presidio local models run **before** schema extraction to mask identifiable markers.
  2. Nightly MinIO orphan cleanup scripts. Raw assets are permanently deleted upon terminal status (`STORED` or `DELETED`).

## 2. Secure Development Lifecycle (SDLC) Constraints
* **Dependencies:** `pnpm audit` enforced in CI pipeline.
* **Code Review:** Consensus required for any changes to schema routing or RLS policies.
* **Secrets:** No `.env` secrets committed. Doppler or AWS Secrets Manager assumed for injection at runtime.
