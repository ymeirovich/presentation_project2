# Sprint 4 – Phase 9 PresGen-Core HTTP Integration: TDD Manual Testing

**Created**: 2025-10-08  
**Scope**: Validate real PresGen-Core HTTP integration (Phase 9)  
**Status**: Ready for execution

---

## 1. Prerequisites

- `PRESGEN_USE_MOCK=false` in both root and `presgen-assess/.env`.
- `PRESGEN_CORE_VOICE_PROFILE=OpenAI Demo Voice (Your Audio)` and `PRESGEN_CORE_QUALITY_LEVEL=fast` unless testing overrides.
- PresGen-Assess virtualenv activated and `PYTHONPATH` set to the repository root:
  ```bash
  cd /Users/yitzchak/Documents/learn/presentation_project/sales-agent-labs
  source .venv/bin/activate
  export PYTHONPATH=/Users/yitzchak/Documents/learn/presentation_project/sales-agent-labs:$PYTHONPATH
  ```
- PresGen-Core (training2) service running locally with HTTP routes enabled (e.g., `uvicorn src.service.http:app --port 8080`).
- Google OAuth token and client credentials present (`token.json`, `oauth_slides_client.json`).
- Database seeded with a workflow that has recommended courses (use existing fixture or run Gap Analysis flow).

2025-10-08 15:28:38 | INFO     | PRESGEN_CORE_STARTED | workflow_id=913f4bce-fa1a-40a8-a749-26a610bdb60a | course_id=20251008_122838


---

## 2. Test Matrix

| ID | Scenario | Expected Outcome |
|----|----------|------------------|
| P9-T1 | Core client import & env | `python -c "import src.agent.slides_google"` succeeds; no mock warning on bootstrap. |
| P9-T2 | Generate course (happy path) | PresGen-Assess posts to real PresGen-Core, completes without mock warning, creates Slides & video. |
| P9-T3 | PresGen-Core failure handling | Simulate HTTP failure (e.g., stop Core service); ensure retry + clear error propagated. |
| P9-T4 | UI polling | `/status` endpoint reflects progress and final `video_url` is accessible via download link. |

---

## 3. Test Cases

### P9-T1 – Environment & Dependency Check
1. In repository root, run:
   ```bash
   source .venv/bin/activate
   export PYTHONPATH=/Users/yitzchak/Documents/learn/presentation_project/sales-agent-labs:$PYTHONPATH
   python -c "import src.agent.slides_google"
   ```
2. Expected: no error output.
3. Start PresGen-Assess:
   ```bash
   cd presgen-assess
   uvicorn src.service.app:app --reload --port 8000
   ```
4. Observe startup logs; confirm absence of `⚠️ PresGen-Core mock path used`.

### P9-T2 – Course Generation Happy Path
1. Launch PresGen-Core backend (`presgen-training2`). Note the port.
2. Trigger course generation via UI or direct `curl`:
   ```bash
   curl -X POST "http://localhost:8000/api/v1/workflows/913f4bce-fa1a-40a8-a749-26a610bdb60a/skills/modeling/generate-course"
   ```
   --
   (.venv) yitzchak@MacBookPro sales-agent-labs % curl -X POST "http://localhost:8000/api/v1/workflows/913f4bce-fa1a-40a8-a749-26a610bdb60a/skills/modeling/generate-course"
{"course_id":"20251008_123156","workflow_id":"913f4bce-fa1a-40a8-a749-26a610bdb60a","skill_id":"modeling","skill_name":"Modeling","course_title":"Mastering Modeling","presentation_url":"https://drive.google.com/presentation/d/core_a75139a2f40c4bc5a1b699e6d457209f/edit","video_url":null,"presgen_core_job_id":null,"presgen_core_download_url":null,"presgen_avatar_job_id":null,"local_video_path":null,"status":"generating_video","progress":60,"created_at":"2025-10-08T12:31:56.824705","updated_at":"2025-10-08T12:31:56.884493","completed_at":null}%  

3. Monitor `course_generation.log`, `presgen_assess_combined.log`, and PresGen-Core logs.
4. Expected:
   - Logs show new stages (`core_request_start`, `core_request_complete`) without mock warning.
   - Google Slides URL points to a real deck created by PresGen-Core.
   - `presgen_core_download_url` stored on the course row and resolves to `/training/download/{job_id}`.
   - Avatar client runs and produces a video; status progresses to `completed`.
   - UI displays “Download Video” link that streams the generated MP4.

### P9-T3 – Failure & Retry Behavior
1. Stop PresGen-Core service (or set `PRESGEN_CORE_FORCE_FAIL=true`) and rerun course generation.
2. Expected:
   - PresGen-Assess logs `stage=core_circuit_open` or `stage=core_failure`.
   - API returns HTTP 502/503 with descriptive message (`PresGen-Core temporarily unavailable`).
   - No zombie job remains; course status reverts to `failed`.
3. Restart PresGen-Core, clear `PRESGEN_CORE_FORCE_FAIL`, and verify subsequent request succeeds.

### P9-T4 – UI Polling & Status Endpoint
1. From the web UI, click “Generate Course”.
2. Observe browser console logs (`scope=ui.generateCourse`, `scope=ui.courseStatus`).
3. Confirm `/api/presgen-assess/workflows/{id}/courses/{courseId}/status` returns `pending → running → completed`.
4. Verify final `video_url` resolves to a downloadable MP4 and embedded player renders the video inline.

---

## 4. Exit Criteria

- All test cases pass on local environment with real PresGen-Core service.
- `course_generation.log` reflects real pipeline (no mock warning) for each generated skill.
- UI download link delivers the generated MP4.
- Error path (P9-T3) produces clear logs and user-visible error message.
- README/TDD documentation updated and shared with the team.

---

## 5. Observations & Follow-ups

| Date | Tester | Result | Notes/Follow-up |
|------|--------|--------|-----------------|
|      |        |        |                 |
