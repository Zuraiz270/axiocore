# Session Handoff Methodology

When an LLM session becomes too long, context degrades. We use handoff documents to bridge the gap cleanly.

## Instructions for the LLM Entity:
If you are nearing the context limit, or completing a major milestone, you must generate a handoff document in this directory titled `YYYY-MM-DD_HH-MM_{feature_name}_handoff.md`.

### Handoff Format Requirements:
1. **Current State:** Exactly what was just built (e.g., "Merged Prisma schema migration for documents table").
2. **Pending State / Broken State:** What is currently failing or unfinished (e.g., "The Redis Stream consumer is reading but throwing a validation error on Zod parse").
3. **Exact Next Step:** The very next terminal command or file edit the incoming agent needs to execute. Do not be vague. State the objective clearly.
4. **Relevant Files:** A markdown list of the 3-5 files that dictate the current behavior so the new LLM knows exactly what to `view_file` first.
