# Sprint 4: Phase 4 API Endpoints - TDD Manual Testing Guide

**Created**: 2025-10-05
**Sprint**: Sprint 4 - PresGen-Avatar Integration
**Scope**: Phase 4 (Generate Course + Status APIs)
**Status**: Ready for execution

---

## Overview
Phase 4 finalises backend endpoints for individual course generation. These tests validate idempotent POST behaviour, PresGen-Core/Avatar orchestration, and the status polling contract required by the UI.

---

## Prerequisites
- Phases 1-3 completed and validated.
- Local API running: `./venv/bin/uvicorn src.service.app:app --port 8000 --reload`.
- Known workflow + skill (e.g. use `sqlite3 test_database.db "SELECT workflow_id, skill_id FROM recommended_courses LIMIT 1;"`).

(venv) yitzchak@MacBookPro presgen-assess % sqlite3 test_database.db "SELECT workflow_id, skill_id FROM recommended_courses LIMIT 1;"
19952bd09cfe44bc9460c4f521caca89|security

- Environment vars:
  - `PRESGEN_USE_MOCK=true` for success path.
  - Optional: set to `false` to simulate avatar failure in P4-T4.
- Ensure database has no stale `generated_courses` rows for the test workflow (`sqlite3 ... DELETE FROM generated_courses WHERE workflow_id='<workflow_hex>';`).

---

## Test Matrix
| ID | Objective | Pass Criteria |
|----|-----------|---------------|
| P4-T1 | Successful course generation | POST returns 200 with completed payload; DB row reflects final state |
| P4-T2 | Idempotent re-request | Second POST returns existing record with `COURSE_GENERATION_ALREADY_EXISTS` log |
| P4-T3 | Status polling | GET endpoint mirrors DB fields and progresses after generation |
| P4-T4 | Failure recovery | With mock disabled, POST returns 502 and log shows `COURSE_GENERATION_FAILED` |
| P4-T5 | Retry after failure | Re-enable mock, POST retries and succeeds, log includes `COURSE_GENERATION_RETRY` |

---

## Test Cases

### P4-T1 – Successful Course Generation
1. Ensure `PRESGEN_USE_MOCK=true`.
2. Trigger generation:
   ```bash
   curl -X POST "http://localhost:8000/api/v1/workflows/19952bd09cfe44bc9460c4f521caca89/skills/security/generate-course" -H "Content-Type: application/json"
   ```
   --
   (venv) yitzchak@MacBookPro presgen-assess % curl -X POST "http://localhost:8000/api/v1/workflows/19952bd09cfe44bc9460c4f521caca89/skills/security/generate-course" -H "Content-Type: application/json"

{"course_id":"7fcc45cbfb4942759b3208d185386ca8","workflow_id":"19952bd0-9cfe-44bc-9460-c4f521caca89","skill_id":"security","skill_name":"Security","course_title":"Mastering Security","presentation_url":"https://drive.google.com/presentation/d/core_ddfdbe6ca1044767883b191be345d394/edit","video_url":"https://storage.googleapis.com/avatar-videos/avatar_5c8b1f674d5f42f1b0a1c8a1b42a1369.mp4","status":"completed","progress":100,"created_at":"2025-10-05T15:54:10.976611","updated_at":"2025-10-05T15:54:10.996887","completed_at":"2025-10-05T15:54:10.996608"}%   


3. Expected response: HTTP 200 with `status":"completed"`, `presentation_url`, and `video_url` populated.
4. Verify DB:
   ```bash
   sqlite3 test_database.db "SELECT status, progress, presentation_url, video_url FROM generated_courses WHERE workflow_id='19952bd09cfe44bc9460c4f521caca89' AND skill_id='security'"

   --
   (venv) yitzchak@MacBookPro presgen-assess % sqlite3 test_database.db "SELECT status, progress, presentation_url, video_url FROM generated_courses WHERE workflow_id='19952bd09cfe44bc9460c4f521caca89' AND skill_id='security'"
completed|100|https://drive.google.com/presentation/d/core_ddfdbe6ca1044767883b191be345d394/edit|https://storage.googleapis.com/avatar-videos/avatar_5c8b1f674d5f42f1b0a1c8a1b42a1369.mp4
   ```
5. Log tail contains full event sequence ending with `COURSE_GENERATION_COMPLETED`.

### P4-T2 – Idempotent Re-Request
1. Rerun the POST from P4-T1.
2. Expected: Response matches existing record (same `course_id`), no new DB row, log includes `COURSE_GENERATION_ALREADY_EXISTS`.

### P4-T3 – Status Polling Endpoint
1. Immediately after P4-T1, call:
   ```bash
   curl "http://localhost:8000/api/v1/workflows/19952bd09cfe44bc9460c4f521caca89/courses/7fcc45cbfb4942759b3208d185386ca8/status"

   --
   (venv) yitzchak@MacBookPro presgen-assess % curl "http://localhost:8000/api/v1/workflows/19952bd09cfe44bc9460c4f521caca89/courses/7fcc45cbfb4942759b3208d185386ca8/status"
{"course_id":"7fcc45cbfb4942759b3208d185386ca8","status":"completed","progress":100,"presentation_url":"https://drive.google.com/presentation/d/core_ddfdbe6ca1044767883b191be345d394/edit","video_url":"https://storage.googleapis.com/avatar-videos/avatar_5c8b1f674d5f42f1b0a1c8a1b42a1369.mp4","error_message":null}%                 
(venv) yitzchak@MacBookPro presgen-assess % 
   ```
2. Expected: JSON mirrors `generated_courses` fields (`status`, `progress`, URLs, error_message=None).
3. Optional: Run step during in-progress run (set poll interval to 5s) to observe `generating_video` status before completion.

### P4-T4 – Failure Handling
1. Set `PRESGEN_USE_MOCK=false` and ensure no avatar backend is running.
2. Delete existing course row (if any) for clean retry.
3. POST again; expect HTTP 502 with detail `PresGen-Avatar generation failed`.
4. Log shows `COURSE_GENERATION_FAILED` and DB row stores `status='failed'` with `error_message` populated.

### P4-T5 – Retry After Failure
1. Re-enable mock: `PRESGEN_USE_MOCK=true`.
2. POST once more with same workflow/skill.
3. Expected: Response succeeds, log contains `COURSE_GENERATION_RETRY` followed by normal completion events, DB row reset with fresh URLs and timestamps.

---

## Exit Criteria
- Both endpoints validated for success, idempotency, failure, and retry flows.
- Database records reflect expected state transitions.
- Log file documents `COURSE_GENERATION_ALREADY_EXISTS`, `COURSE_GENERATION_RETRY`, and failure events as applicable.
- QA notes updated with results prior to handing Sprint 4 to frontend integration.
