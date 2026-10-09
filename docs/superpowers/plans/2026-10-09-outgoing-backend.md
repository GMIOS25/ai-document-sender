# Outgoing Recipient Backend Implementation Plan

> **For agentic workers:** Use subagent-driven-development or executing-plans task by task. Steps use checkboxes. User instruction on 2026-10-09 authorizes execution of both designs in this session; extraction and backend core have disjoint file ownership.

**Goal:** Extract recipient mentions and resolve current registry identities through an asynchronous outgoing.v1 API.

**Architecture:** Read-only base lookup with verified policy/overlay, PDF/LLM extraction, conservative resolver, persisted SQLite jobs/checkpoints/feedback and one durable worker. No GPU or model training.

**Tech Stack:** Python 3.12+, FastAPI/Pydantic/Uvicorn/HTTPX/python-multipart/pypdf/pdfplumber, SQLite FTS5; Poppler when vision rendering is needed.

**Spec:** ../specs/2026-10-07-outgoing-backend-design.md

## Global Constraints

- Base lookup.db is opened mode=ro; do not rebuild source DB or modify crawler tools.
- OpenRouter key only in backend env, never in logs/results/client bundles.
- Resolve current snapshot independently of document_date; policy and registry have separate versions.
- Keep unresolved raw evidence and needs_review for partial/ambiguous output; VT stays policy_unknown until verified.
- No automatic role assignment or rule activation from feedback; no paid fallback.

## Review Focus

1. Group and role ambiguity must abstain; test bare PCT, PCVP and missing membership.
2. Current V-code assignments can change; test anchored tokens and snapshot cache invalidation.
3. A text PDF can have a scanned recipient region; test mixed pages and regional incompleteness.
4. Provider can return invalid JSON or invented IDs; test schema validation and candidate allowlist.
5. Restart/retry can duplicate work or strand jobs; test idempotency conflict, lease recovery and checkpoint reuse.

## Task 1: Contracts, registry and conservative resolution

**Files:** pyproject.toml; src/ai_document_sender/{__init__,config,contracts,registry,resolver}.py; resources/policies/recipient_aliases.v1.json; tests/test_registry.py, tests/test_resolver.py.

**Interfaces:** Settings contains lookup_db, policy_path, runtime_dir, provider config and limits. Pydantic `DocumentMetadata`, `Evidence`, `Mention`, `Extraction`, `Recipient`, `OutgoingResult`, `Feedback`. `Extraction` has mentions, status, review_reasons. `Registry(settings)` exposes version properties, readonly candidates and exact identities. Async `resolve_mentions(extraction,registry,metadata,job_id,input_sha256,provider=None) -> OutgoingResult`.

- [x] Add tests with miniature SQLite snapshots for exact unique chair, ambiguous roles/names/scopes, initials, aliases, live V-codes and group membership.
- [x] Observe tests fail before implementation; implement validated models and registry/policy rules without frequency top-1 decisions.
- [x] Preserve raw evidence/dedupe identities and assert every result ID exists in snapshot.
- [x] Add invalid candidate model choice test, implement optional constrained decision; no invented ID accepted.
- [x] Run registry/resolver suite and commit explicit source/policy/test paths.

## Task 2: PDF extraction, OpenRouter and evaluation tools

**Files:** src/ai_document_sender/{extraction,mentions,provider}.py; tools/evaluate_outgoing.py; tests/test_extraction.py, tests/test_provider.py, tests/test_evaluation.py; docs/evaluation.md.

**Interfaces:** async `extract_document(path,provider,metadata,settings) -> Extraction`. Provider exposes async `extract_mentions(pages,metadata,images=None) -> dict` and `choose_candidate(mention,candidates,context) -> str|None`. pages contain `{page,text}`; images are `{page,data_url}` rendered pages/regions. Output mention JSON is validated by contracts and grounded to page/source text where available.

- [x] Write tests for Nơi nhận/Kính gửi/Như trên/Lưu, hybrid PDF, no-provider partial and OCR failure.
- [x] Implement layout extraction and bounded regional/page vision fallback, retaining reference evidence and skipping signature-only names.
- [x] Add provider tests for invalid JSON repair, 429/Retry-After/timeout, text/vision models and no paid fallback; implement HTTP adapter.
- [x] Implement evaluator with separate extraction/resolution gold, exact set/precision/recall/coverage and explicit excluded/incomplete annotation counts; no score claimed from historical truncated labels.
- [x] Run deterministic tests; inspect extraction of latest real examples without external provider calls; commit explicit paths.

## Task 3: Durable jobs, API, feedback and operations

**Files:** src/ai_document_sender/{jobs,api,__main__}.py; .env.example; .gitignore; tests/test_api.py, tests/test_jobs.py; README.md.

**Interfaces:** POST multipart file+metadata, required Idempotency-Key; HTTP202 create. GET job envelope; POST feedback→201 feedback_id; GET health→versions/capabilities. Worker uses extract_document then resolve_mentions. Settings read env and local .env; host defaults127.0.0.1 port8001.

- [x] Write API/job tests for upload validation, authentication, idempotency conflict, version differences, recovery, failure and feedback version/identity validation.
- [x] Implement runtime SQLite schema, atomic claim/lease recovery, checkpoint/cache and persisted result/error.
- [x] Implement routes, safe error bodies, request/file/page bounds and startup/shutdown worker lifecycle.
- [x] Add verified overlay/membership administration through explicit local policy import/CLI, not unreviewed feedback; expose no credential data.
- [x] Document pip install/run/env/model selection, Poppler dependency, offline limits and annotation workflow.
- [x] Run all backend tests and HTTP create/poll/feedback smoke; verify source DB hash unchanged.
- [x] Commit explicit paths, excluding runtime DB/tokens/PDF corpus.

## Task 4: Cross-repo qualification

- [x] Verify frontend and backend share all schema fields/status/version/review semantics.
- [x] Run newest local examples and report unresolved/policy/directory issues without treating historical labels as complete gold.
- [x] Independently review core resolver/worker/extraction; fix important findings and rerun affected tests.
- [x] Publish local artifacts and actual validation results. Live OpenRouter and ≥95% holdout qualification require configured keys and reviewed gold; report these honestly as separate from technical completion.

## Execution record — 2026-10-09

All implementation tasks completed. Full backend suite: 59 passed, one Starlette TestClient deprecation warning. Real Node provider to FastAPI loopback passed multipart create/poll/idempotency/search/feedback, including a resolved candidate identity link. Newest real-PDF diagnostics and unchanged source DB hash are recorded in ../../implementation-validation-2026-10-09.md; no cloud calls were made.

Independent review added regression coverage for fabricated body references, nonterminal/empty evaluation predictions, conflicting aliases, resolve feedback without identity, SQLite handle closure, leases/checkpoints and exact verified department suffix fallback. Live model invocation, business alias/group confirmation and a reviewed temporal holdout are explicit qualification requirements, not claimed as achieved by offline tests.
