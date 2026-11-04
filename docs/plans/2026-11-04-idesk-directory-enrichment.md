# iDesk organization directory enrichment — 2026-11-04

User approved implementing the recommendation presented in chat: supplement historical recipients with iDesk category directories, search live for missing organizations, preserve observations across syncs, and resolve again without uploading/OCR again.

## Shared contract

- Existing `POST /v1/sync/lookup` accepts optional `unit_directory: {elements: [...]}` containing both communication spheres. Old payloads remain valid. Historical unit lists are partial observations, never deletion authorities. Personnel sync retains existing semantics.
- Add authenticated `POST /v1/sync/organizations`: `{source: "directory" | "search", elements: [...]}`. Every node requires nonempty `code`, `name`, and `sphere` (`int_province_comm` or `ext_province_comm`); retain native `uuid`, `identifier`, `parentIdentifier`, `centerCode`. Bounded input; invalid batches fail atomically with 422. Reply includes `status` (`synced`/`no_change`), `tenant_id`, `registry_version`, `alias_policy_version`, and change counts.
- Deduplicate by tenant + sphere + code, preserve existing recipient IDs, preserve history frequency, prefer directory/search names over history. Keep source/timestamps/raw observations in tenant SQLite. Missing results never delete. Native UUIDs are metadata, not cross-source identity keys. A changed UUID must not change the recipient ID or delete another sphere.
- Add authenticated `POST /v1/outgoing/jobs/{job_id}/resolutions` (no body), returning 202 `{job_id,status}`. Create/reuse a new job snapshot with the original checkpoint; do not modify original job/result/feedback, upload or read the PDF, or rerun extraction. Enforce tenant ownership and completed source job; reject incompatible processing or unavailable extraction. Worker resolves from checkpoint as usual. Retry is idempotent for source job + snapshot + processing version. Version identity includes tenant where necessary.
- Userscript polls resolutions just like jobs. When snapshots change, reset review confirmation and decisions before displaying fresh candidates; feedback always references the new job and snapshot.
- Keep iDesk session credentials in browser. Existing API auth and CORS unchanged. No new dependencies. Never send the official iDesk transfer.

## Task 1 — backend (delegated)

Read this first: this task is your requirements. Work only in `C:/Workspaces/ai-document-sender`, branch `codex/idesk-directory-enrichment`. Implement the shared contract above in sync/contracts/api/jobs/tenant handling using existing patterns and minimal helpers. Add regression tests first and observe failures, then implement. In particular test history-only repeat retains enriched units, history does not downgrade current names, UUID changes keep identity, same code/UUID across spheres and tenants remains separate, FTS includes enriched nodes, invalid batches are atomic, cache refresh occurs, resolution reuses even partial extraction and leaves old snapshot untouched, wrong tenant rejected, retry returns same job, and stale feedback remains rejected. Update README with API/sync behavior. Run full pytest. Do not touch unrelated untracked `tests/test_target_sheet_multiline.py` or `tools/update_target_sheet_multiline.py`. Do not spawn agents. Do not commit; root will integrate and commit after review. Write report to `var/idesk-directory-backend-report.md` with changed files, RED/GREEN verification, concerns and any contract deviations. Return compact status and test results.

## Task 2 — browser client and integration (root)

Discover centers/categories from the live page's own API calls; fetch rank/type categories dynamically, then organization lists with empty keywords. Detect result limits/truncation and propagate incomplete status; never report full coverage based on a partial source. Add bounded live keyword search, validate native nodes and preserve sphere separation in `organizationDirectory`. Include directory data in existing lookup sync. On unresolved organization mentions or empty manual lookup, search iDesk, import valid observations, obtain a new resolution, and reset stale review state. Exact code/sphere checks and chip verification remain. Build installable userscript, update docs, run Node tests and backend HTTP integration. Inspect real browser behavior read-only and backfill current directory through authorized sync if available.

## Task 3 — review and finish

Review both diffs for partial-data deletion, identity collisions, wrong-sphere selection, stale snapshot handling, pagination caps, session/login failures and tenant isolation. Run project suites and userscript build; record concrete evidence and remaining limitations. Preserve unrelated working changes.

## Progress

- Baseline: backend 185 tests passed (one existing Starlette deprecation warning); userscript 80 tests passed.
- Backend base: 8d6822449ff099c29835fb38992e0175f6a3eff4.
- Userscript base: 626de08b94656e65f61ad4e83de6f17c9abba3b6.
- Both repositories on `codex/idesk-directory-enrichment`; working in place to integrate with the installed local tools and existing tenant data. Unrelated untracked files preserved.
- Preflight: tasks 1 and 2 share only the additive HTTP contracts above; neither edits the other's repository. Task 3 consumes both. No destructive external action is needed.
- Task 1 complete: backend 196 tests pass, including cached-upload checkpoint reuse after removing the PDF. Preliminary review found the missing checkpoint on cache hits; Worker now persists it in both paths. Unknown legacy owners remain audit-readable and require one reupload for fresh writes/resolution.
- Task 2 complete: userscript 1.4.0 built at `C:/Workspaces/Script-Idesk Sender/dist/idesk_outgoing.user.js`; 91 tests pass. Reload regression confirms exact code lookup fills the native directory before form selection. Category lists are bounded to 64 groups/4 concurrent requests; missing/unclassified descendants use live keyword fallback, without claiming exhaustive coverage.
- Task 3 verification: real Node HTTP/FormData -> FastAPI smoke passes, including directory import, new resolution, retry reuse and immutable original result. Browser fixture shows the live-search and fresh-resolution controls; direct search executes without runtime errors. Backend and client diff whitespace checks pass. The existing Starlette/httpx deprecation warning remains.
- Live VPUB data: added H21.01, H21.20 and H21.26 from the observed iDesk category response. Exact Vietnamese names and Ngoại vụ search verified. Original SQLite backup and source evidence are under `var/directory-enrichment/2026-11-04/`; this data is not committed.
- Final review: external review stopped at the provider usage limit after the checkpoint finding; root completed remaining review, found/fixed the page-reload identity gap, and reran the full suites and HTTP integration. No merge or remote push is part of this request.
