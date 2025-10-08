# Sprint 4: Phase 9 – PresGen-Core HTTP Integration Plan

## Overview

Phase 9 replaces the mocked PresGen-Core client with a real HTTP integration. The goal is to orchestrate full presentation generation (Slides + video) by calling the PresGen-Core service that lives in the `presgen-training2` project. Completing this work removes the `⚠️ PresGen-Core mock path used` warning and enables true end-to-end runs in PresGen-Assess.

## Status Update (2025-10-08)

- ✅ Authored this integration plan and companion manual TDD guide (`Oct5_Avatar_SPRINT_4_PHASE9_TDD_MANUAL_TESTING.md`).
- ✅ Researched current PresGen-Core service surface area and identified required request/response mappings.
- ✅ Confirmed PresGen-Core HTTP contract via `docs/openapi8080.json` (POST `/training/presentation-only`, `TrainingVideoRequest`/`TrainingVideoResponse`, `/training/download/{job_id}`).
- ❌ Implementation still pending: client wiring, status propagation, logging, documentation updates, and manual validation outlined below.

## Current State

- `presgen-assess/src/service/presgen_core_client.py` handles the orchestration but **always** invokes the mock path.
- `presgen-assess/src/integrations/presgen_core/client.py` contains the actual HTTP wrapper, but it is a stub that returns a mock response.
- PresGen-Core (training2 service) already exposes HTTP routes such as `/training/presentation-only` for real processing.

## Objectives

1. Update the PresGen-Core client to POST to the real backend instead of returning a stub.
2. Provide structured logging, retries, and error handling around the new HTTP calls.
3. Surface job IDs and progress so the existing course-generation pipeline (and UI polling) behaves correctly.
4. Supply clear configuration guidance (`PRESGEN_CORE_URL`, auth headers, etc.).
5. Deliver manual test steps (separate TDD document) to validate the integration.

## Implementation Plan

### 1. Confirm PresGen-Core API contract

- Review the `presgen-training2` FastAPI routes (`src/service/http.py`) and openapi (`docs/openapi8080.json`) to document the exact contract we must honour:

| Endpoint | Method | Purpose | Request Schema | Response Schema | Notes |
|----------|--------|---------|----------------|-----------------|-------|
| `/training/presentation-only` | POST | Kick off deck + narration build | `TrainingVideoRequest` (JSON) | `TrainingVideoResponse` | Requires `mode`, `voice_profile_name`; accepts `google_slides_url` or `content_text`; `download_url` is relative. |
| `/training/download/{job_id}` | GET | Retrieve rendered MP4 | N/A | Binary stream | File lives under `output/` or `temp/training_{job_id}`; ensure 200/404 handling. |
| `/video/status/{job_id}` | GET | Poll long-running jobs | Path `job_id` | `VideoJobStatus` | Currently training-only path returns final status immediately; future-proof by allowing polling hooks. |

- Confirm required headers: JSON body plus optional `Authorization: Bearer <token>` when `PRESGEN_CORE_API_KEY` is configured.
- Record error semantics: validation returns HTTP 422 with `HTTPValidationError`; operational failures return HTTP 500 with text message inside `error` field of `TrainingVideoResponse`.

### 2. Expand `PresGenCoreClient`

- Create a real HTTP execution path while preserving the existing circuit breaker:
  1. Introduce `_post_presentations(path: str, payload: dict)` that centralises retries, timeout, and header construction using a single shared `httpx.AsyncClient`.
  2. Update `generate_presentation` to:
     - Short-circuit to mock when `settings.presgen_use_mock` is `True`.
     - Build the actual `TrainingVideoRequest` payload by mapping our internal schema to Core expectations:
       - `mode`: always `"presentation_only"` for Phase 9.
       - `voice_profile_name`: configurable via `settings.presgen_voice_profile` (fallback `"OpenAI Demo Voice (Your Audio)"`).
       - `google_slides_url`: use pre-generated Slides URL when available; otherwise send `content_text` from prompt output and set `generate_new_slides=True`.
       - `quality_level`: default `"fast"` with env override.
       - `use_cache`: mirror `settings.presgen_core_use_cache`.
       - Pass through `metadata` fields (workflow, skill) for observability.
     - Parse `TrainingVideoResponse`, normalise the relative `download_url` into an absolute URL, and populate an expanded `PresGenPresentationResponse` (job id, success flag, durations, error text).
     - Emit structured logs for `core_request_start`, `core_request_retry`, `core_request_complete`, `core_request_failed`.

```python
# presgen-assess/src/integrations/presgen_core/client.py
async def generate_presentation(self, request: PresGenPresentationRequest) -> PresGenPresentationResponse:
    if self.use_mock:
        return await self._mock_generate(request)

    payload = self._build_training_video_request(request)
    start = datetime.utcnow()

    try:
        self._log_core_stage("core_request_start", request, payload)
        response = await self._post_presentations("/training/presentation-only", payload)
        data = response.json()
    except httpx.HTTPError as exc:
        self._record_failure(exc)
        raise PresGenCoreHTTPError(f"PresGen-Core request failed: {exc}") from exc

    result = PresGenPresentationResponse.model_validate(self._normalise_response(data))
    result.duration_ms = int((datetime.utcnow() - start).total_seconds() * 1000)
    self._log_core_stage("core_request_complete", request, result.model_dump())
    self._reset_failure_state()
    return result
```

- Extend `PresGenPresentationRequest/Response` models to include new fields required for downstream processing (`voice_profile_name`, `download_url`, `processing_time`, `error`).
- Introduce dedicated exceptions (`PresGenCoreHTTPError`, `PresGenCoreTimeoutError`) so API handlers can map to 502/503 consistently.
- Ensure `_post_presentations` increments the circuit breaker on non-2xx responses and surfaces useful error messages (status code, response body snippet).

### 3. Handle asynchronous completion

- Phase 9 will treat PresGen-Core as “fire-and-track” work:
  - Persist `presgen_core_job_id`, `presgen_core_download_url`, and `presgen_core_processing_time_ms` onto `GeneratedCourse`.
  - When `success=False` or `error` is populated, mark the course as failed and surface the message via API.
  - When `success=True`, immediately stage the avatar call but retain the download URL for audit/debug.
- Implement optional status polling hooks so we can evolve with future async behaviour:
  - Add `get_job_status(job_id: str)` that calls `/video/status/{job_id}` when available; fall back to cached response.
  - Add `poll_until_complete(job_id: str, timeout=600)` with exponential backoff; currently returns immediately but ensures compatibility when Core introduces non-blocking mode.
- Expose a lightweight admin/monitoring endpoint (`/api/v1/monitoring/presgen/jobs/{job_id}/status`) that proxies the cached status to ops tooling.

### 4. Configuration updates

- Ensure `settings.presgen_core_url` reads `PRESGEN_CORE_URL` (already present).
- Introduce optional `PRESGEN_CORE_API_KEY`; if set, add `Authorization: Bearer {key}` to requests.
- Document the new env requirements (see README/TDD updates).
- Clarify that Google Slides access now relies solely on the OAuth client + token pair (`oauth_slides_client.json`, `token.json`); remove any lingering service-account guidance and add refresh/rotation steps for the OAuth credentials.
- Add new toggles:
  - `PRESGEN_CORE_VOICE_PROFILE` (default `"OpenAI Demo Voice (Your Audio)"`).
  - `PRESGEN_CORE_QUALITY_LEVEL` (default `"fast"`).
  - `PRESGEN_CORE_USE_CACHE` to align with `TrainingVideoRequest.use_cache`.
- Update README and `.env.example` to demonstrate the OAuth-focused setup (activate venv, run `python src/agent/slides_google.py --auth` to refresh token, store files in repo root).

### 5. Logging instrumentation

- Leverage existing pipeline tracing:
  - Log `stage=core_request_start`, `stage=core_request_complete`, and `stage=core_request_failed`.
  - Include workflow ID, skill ID, job ID, duration, and error string.
- Add structured logging inside the `_post` method to capture HTTP status codes.
- Extend `StructuredLogger` with helper methods (`log_presgen_core_retry`, `log_presgen_core_download_cached`) so logs remain consistent across API handlers, background jobs, and monitoring endpoints.
- Capture OAuth credential fingerprint (hash) at startup to aid support without leaking secrets.

### 6. Testing strategy

1. **Unit tests** for the HTTP client:
   - Mock `httpx.AsyncClient` to simulate success, failure, and retry scenarios.
   - Assert that relative download URLs become absolute URLs and that circuit breaker counters increment on HTTP errors.
2. **Manual end-to-end** (see `Oct5_Avatar_SPRINT_4_PHASE9_TDD_MANUAL_TESTING.md`):
   - Start both PresGen-Assess and PresGen-Core services.
   - Generate courses and verify real slides/video artifacts.
   - Confirm the warning disappears and logs include the new stages.
3. **Contract regression tests**:
   - Add `tests/integration/presgen_core` coverage that loads canned openapi fixtures to ensure request/response models stay in sync.
   - Validate monitoring endpoint responses against `openapi8002.json` expectations.
4. **OAuth smoke**:
   - Script a CLI check (`python scripts/check_slides_token.py`) that pings Google Slides, ensuring the token is refreshed before deployments.

### 7. Rollout guidance

- Keep a feature flag by honoring `PRESGEN_USE_MOCK` for rapid fallback.
- Initially deploy to local/dev environments; once stable, promote to shared environments.
- Monitor logs for the new stages and any PresGen-Core failures.
- Define a rollback script that flips `PRESGEN_USE_MOCK=true` and restarts the worker/API pods.
- Create a launch checklist (Slack announcement, token freshness verification, Core availability probe).

### 8. Documentation & UX updates

- Update README, ops runbooks, and TDD manual to describe the OAuth-based Google Slides setup, Core URL overrides, and mock toggle behaviour.
- Refresh the in-app warning banner to confirm when the real Core integration is active (include job id + download link).
- Add troubleshooting FAQs for the most common failure modes (invalid OAuth token, Core offline, video download 404, voice profile missing).

### 9. Timeline & owners (target: 3 engineering days)

| Day | Focus | Owner | Key Deliverables |
|-----|-------|-------|------------------|
| Day 1 | Schema + client implementation | Backend engineer | Updated models, HTTP client wiring, unit tests. |
| Day 2 | Workflow integration + logging | Backend engineer | `generate_skill_course` persistence changes, monitoring endpoint updates, structured logs. |
| Day 3 | Docs, manual validation, rollout prep | QA + Eng | README/TDD updates, smoke scripts, launch checklist, manual test execution report. |

### 10. Acceptance criteria (Phase 9 complete when…)

- Real course generation runs hit PresGen-Core without emitting the mock warning.
- `GeneratedCourse` rows store Core job metadata and expose valid download URLs.
- `/api/v1/monitoring/presgen/*` endpoints reflect live status without manual edits.
- Manual test plan P9-T1→P9-T4 passes against a fresh environment using OAuth credentials only.
- Feature flag can revert to mock mode within five minutes using documented steps.

### 11. Key files to touch

- `presgen-assess/src/integrations/presgen_core/client.py`
- `presgen-assess/src/integrations/presgen_core/schemas.py`
- `presgen-assess/src/service/api/v1/endpoints/workflows.py`
- `presgen-assess/src/common/structured_logger.py`
- `presgen-assess/src/services/course_generation_service.py` (log helpers)
- `presgen-assess/.env`, `presgen-assess/README.md`, `assessment_workflow_docs/Oct5_Avatar_SPRINT_4_PHASE9_TDD_MANUAL_TESTING.md`
- New/updated tests under `presgen-assess/tests/`

## Outstanding Information Required

To begin coding, we still need:

1. ~~**Voice profile defaults** – Confirm the canonical profile name & language to use in production.~~ ✅ Set to `OpenAI Demo Voice (Your Audio)` with `fast` quality mode.
2. **PresGen-Core base URL per environment** – Dev/staging/prod hostnames and any reverse-proxy requirements (HTTPS, auth).
3. **Operational ownership** – Identify on-call contact for Core outages to route alerts once monitoring is live.

## Deliverables

- Code changes in `presgen-assess/src/integrations/presgen_core/client.py`.
- Updated pipeline flow in `generate_skill_course`.
- README + TDD documentation additions.
- Manual test results recorded in sprint notes.

## Risks & Mitigations

- **PresGen-Core downtime**: circuit breaker already exists; ensure meaningful error messages propagate.
- **Schema drift**: keep JSON schema validation or Pydantic models aligned with PresGen-Core responses.
- **Performance**: add logging around total duration to catch slow responses early.

## Success Criteria

- Running course generation produces a real Google Slides deck and video using PresGen-Core without mock warnings.
- UI polling (`/status`) reports accurate progress/status updates.
- TDD manual tests pass in local and shared dev environments.
