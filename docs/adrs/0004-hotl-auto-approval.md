# ADR 0004: HOTL Auto-Approval Logic

**Date:** 2026-03-16
**Status:** Accepted

## Context
Manual human review (HITL) is the primary bottleneck for system throughput. As the system reaches high accuracy, many extractions are 100% correct but still require a "human click" to proceed to the terminal `STORED` state.

## Decision
We will implement **Human-on-the-Loop (HOTL)** automation via the `AutoApprovalService`.
1. **Confidence Threshold:** Only documents with a mean confidence score $> 0.95$ across all extracted fields are eligible.
2. **Forensic Gate:** Any document with a forensic red flag (suspicious metadata, signature mismatch, or low semantic similarity $S < 0.85$ between tiers) is disqualified from auto-approval.
3. **Value Cap:** Documents with a financial impact $> \$5000$ (or equivalent high-stake marker) **always** require human consensus, regardless of confidence.
4. **System Label:** Automated approvals are tagged as `approved_by: system` for distinct auditing.

## Consequences
**Positive:**
- Drastically reduces the backlog of manual reviews for "slam-dunk" cases.
- Allows human reviewers to focus only on edge cases and high-stakes data.

**Negative:**
- Introduces a small risk of "silent failure" if the model is overconfident in an incorrect extraction. Mitigated by strict forensic and value gates.
