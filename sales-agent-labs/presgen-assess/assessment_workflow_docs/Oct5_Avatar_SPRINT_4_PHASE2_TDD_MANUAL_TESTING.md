# Sprint 4: Phase 2 PresGen-Avatar Client - TDD Manual Testing Guide

**Created**: 2025-10-05
**Sprint**: Sprint 4 - PresGen-Avatar Integration
**Scope**: Phase 2 (Client + Schemas)
**Status**: Ready for execution

---

## Overview
Phase 2 introduces the production-aligned PresGen-Avatar client and schema contract. These manual checks validate the async HTTP wrapper, mock fallback, and the workflow endpoint that orchestrates avatar generation.

---

## Prerequisites
- Python virtualenv activated for `presgen-assess`
- Environment variables exported:
  - `PRESGEN_CORE_URL=http://localhost:8080`
  - `PRESGEN_AVATAR_URL=http://localhost:8002`
  - `PRESGEN_USE_MOCK=true` (set to `false` only when the real Avatar service is available)
- Local SQLite test database refreshed: `sqlite3 test_database.db "DELETE FROM generated_courses;"`
- Logging directory available: `mkdir -p logs`

---

## Test Matrix
| ID | Objective | Pass Criteria |
|----|-----------|---------------|
| P2-T1 | Schema validation | `AvatarGenerationRequest` builds with default voice config and rejects invalid URLs |
| P2-T2 | Mocked queueing flow | `PresGenAvatarClient.generate_video` returns job id + pending status when mock enabled |
| P2-T3 | Polling completion | `PresGenAvatarClient.poll_until_complete` resolves to completed status |
| P2-T4 | Workflow endpoint | `POST /api/v1/workflows/{workflow_id}/skills/{skill_id}/generate-course` produces stored record + video URL |
| P2-T5 | Error handling | Simulated failure populates `error_message` and returns HTTP 502 |

---

## Test Cases

### P2-T1 – Schema Validation
1. Run `./venv/bin/python - <<'PY'` and execute:
   ```python
./venv/bin/python - <<'PY'
from src.integrations.presgen_avatar.schemas import AvatarGenerationRequest
payload = AvatarGenerationRequest(presentation_url="https://example.com/deck", mode="presentation-only")
print(payload.voice_config.provider, payload.mode)
PY
--
openai presentation-only
   ```
2. Expected: prints `openai presentation-only`.
3. Negative check: rerun with `presentation_url="notaurl"` → Pydantic raises validation error.

### P2-T2 – Mocked Queueing Flow
1. Ensure `PRESGEN_USE_MOCK=true`.
2. Run:
   ```python
./venv/bin/python - <<'PY'
import asyncio
from src.integrations.presgen_avatar.client import PresGenAvatarClient
async def main():
      client = PresGenAvatarClient()
      resp = await client.generate_video("https://example.com/deck")
      print(resp.job_id.startswith("avatar_"), resp.status)
      await client.close()
asyncio.run(main())
PY
--
True pending
   ```
3. Expected: `True pending` printed; log file shows `PRESGEN_AVATAR_QUEUED` event when endpoint invoked later.

### P2-T3 – Polling Completion
1. With mock mode still on, extend previous script:
   ```python

./venv/bin/python - <<'PY'
import asyncio
from src.integrations.presgen_avatar.client import PresGenAvatarClient
async def main():
       client = PresGenAvatarClient()
       resp = await client.generate_video("https://example.com/deck")
       status = await client.poll_until_complete(resp.job_id, poll_interval_seconds=0)
       print(status.status, status.progress)
       await client.close()
asyncio.run(main())
PY

   --
   completed 100
   ```
2. Expected: `completed 100` output, no timeout.

### P2-T4 – Workflow Endpoint Integration
1. Seed a workflow + recommended course using existing fixtures or `test_database.db` helpers.
2. Start API locally: `./venv/bin/uvicorn src.service.app:app --port 8000 --reload`.
3. Issue request:
   ```bash
   curl -X POST "http://localhost:8000/api/v1/workflows/{workflow_id}/skills/{skill_id}/generate-course" -H "Content-Type: application/json"
   ```

   --
yitzchak@MacBookPro presgen-assess % curl -X POST "http://localhost:8000/api/v1/workflows/52014fe9-6b77-4e91-b770-ff20b24d7ff7/skills/modeling/generate-course" -H "Content-Type: application/json"
{"course_id":"29571b8cd18b4e1591fb17918935dae6","workflow_id":"52014fe9-6b77-4e91-b770-ff20b24d7ff7","skill_id":"modeling","skill_name":"Modeling","course_title":"Mastering Modeling","presentation_url":"https://drive.google.com/presentation/d/core_0db1869504d14c71accbca86017061f1/edit","video_url":"https://storage.googleapis.com/avatar-videos/avatar_b7e41277798c4e8d81ed30a1e3ff412c.mp4","status":"completed","progress":100,"created_at":"2025-10-05T14:05:36.447890","updated_at":null,"completed_at":"2025-10-05T14:05:36.469018"}%  

4. Expected: JSON response includes `status":"completed"`, `video_url`, and persisted row in `generated_courses` table (`sqlite3 ... SELECT * FROM generated_courses;`).

### P2-T5 – Error Handling Path
1. Temporarily force failure by setting `PRESGEN_USE_MOCK=false` and stopping the avatar service.
2. Rerun the workflow endpoint call.
3. Expected: Endpoint returns HTTP 502 with message `PresGen-Avatar generation failed`; database row records `status='failed'` and populated `error_message`.
4. Reset `PRESGEN_USE_MOCK=true` after test.

---

## Exit Criteria
- All five test cases executed and outcomes captured in sprint QA notes.
- `logs/course_generation.log` contains `PRESGEN_AVATAR_*` events for at least one successful run.
- Any deviations documented with follow-up Jira tasks before promoting Phase 2 to QA sign-off.
