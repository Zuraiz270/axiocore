# ADR 0003: Agentic Navigation (Chain-of-Scroll)

**Date:** 2026-03-16
**Status:** Accepted

## Context
Processing large multi-page documents (>20 pages) through a vision-language model (VLM) is prohibitively expensive both in terms of latency and token costs. Most pages in a large corpus are structurally redundant or irrelevant to the target schema (e.g., terms and conditions pages in an invoice).

## Decision
We will implement an **Agentic Navigator** following a **Chain-of-Scroll (CoS)** heuristic.
1. **Anchor Detection:** The worker first performs a lightweight "scan" of the PDF structure (using PyMuPDF) to identify high-signal "anchor" pages based on keyword density (e.g., "Total", "Summary", "Table of Contents").
2. **Sparse Selection:** Only the identified high-signal indices + surrounding context pages are passed to the heavy Tier 2/Tier 3 extraction logic.
3. **Sequential Verification:** If the extraction fails, the navigator "scrolls" to the next most likely anchor set.

## Consequences
**Positive:**
- Reduces token costs by up to 90% for large documents.
- Significant reduction in end-to-end extraction latency.
- Prevents LLM context window overflow on extremely large files.

**Negative:**
- Heuristic-based; may occasionally miss a relevant field if the anchor keywords are not present. Mitigated by allowing manual "Re-extract Full" triggers in the HITL portal.
