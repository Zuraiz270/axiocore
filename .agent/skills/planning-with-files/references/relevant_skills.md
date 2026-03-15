# Relevant Skills & Reference Tools

During the implementation of Axiocore V3, LLM agents should leverage the following internal tools and mindsets:

## 1. Local Code Inspection Skills
* `view_file` & `list_dir`: Always verify the `docs/` hierarchy before answering architectural questions.
* `grep_search`: When implementing a new endpoint, always `grep` for `Idempotency-Key` or `JWT` to ensure security patterns are copied from existing modules.

## 2. Planning & Handoff Skills
* **Session Verification:** Before executing large file changes, always read the most recent file in `docs/plans/` or `docs/handoffs/` to understand the current build context.
* **Task Management:** Strictly update `task.md` within the `.gemini/antigravity/brain/` folder iteratively.

## 3. Strict Compliance Execution
* **OWASP Enforcement:** Before committing to a database route, check `docs/security/OWASP_SAMM_THREAT_MODEL.md` to ensure RLS is not being bypassed.
