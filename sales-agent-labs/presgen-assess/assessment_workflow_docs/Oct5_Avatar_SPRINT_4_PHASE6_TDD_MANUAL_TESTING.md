# Sprint 4: Phase 6 Custom Prompt Integration – TDD Manual Testing Guide

**Created**: 2025-10-05  
**Sprint**: Sprint 4 – PresGen-Avatar Integration  
**Scope**: Phase 6 (Certification prompt overrides flowing into PresGen-Core)  
**Status**: Ready for execution

---

## Overview
Phase 6 verifies that `presentation_prompt` overrides stored on certification profiles propagate through the course-generation pipeline, are sent to PresGen-Core, and persist in logs/records. These steps assume Phase 1–5 changes are already deployed locally.

---

## Prerequisites
1. **Services running**
   ```bash
   # Terminal 1: PresGen-Assess API
   cd /Users/yitzchak/Documents/learn/presentation_project/sales-agent-labs/presgen-assess
   ./venv/bin/uvicorn src.service.app:app --reload --port 8000
   ```
   ```bash
   # Terminal 2: (Optional) PresGen-Core mock/real server
   cd /Users/yitzchak/Documents/learn/presentation_project/sales-agent-labs
   ./start_video_server.sh   # optional, mock mode acceptable
   ```

2. **Database record with prompt** – There is a seeded workflow whose certification profile has a non-empty prompt: `a25e885b465c40958d3350d292cbcef3`.
   ```bash
   sqlite3 test_database.db "SELECT id, presentation_prompt FROM certification_profiles WHERE TRIM(presentation_prompt) <> '' LIMIT 3;"

   ---
   (.venv) yitzchak@MacBookPro presgen-assess % sqlite3 test_database.db "SELECT id, presentation_prompt FROM certification_profiles WHERE TRIM(presentation_prompt) <> '' LIMIT 3;"
59596658655141f4ba61c6e84a5a8100|Create engaging AWS learning presentations
455dae60065c4038b3df6d769b955dbb|You are an expert instructional designer creating educational presentations for professional certification preparation.

PRESENTATION DESIGN PRINCIPLES:
- Learning Objectives Alignment: Clear, measurable objectives for each section
- Progressive Skill Building: From basic to advanced concepts
- Real-world Application: Practical implementation examples
- Engagement Strategies: Visual elements and interactive components

PERSONALIZATION FACTORS:
- Prioritize content based on identified learning gaps
- Adapt to different learning styles (Visual, Auditory, Kinesthetic)
- Progressive difficulty from current competency level

Create {slide_count} slides using the knowledge base materials and gap analysis insights.
(.venv) yitzchak@MacBookPro presgen-assess % 
   ```

3. **Environment** – Leave `PRESGEN_USE_MOCK=true` unless performing failure scenarios.

4. **Clean logs** (recommended):
   ```bash
   rm -f logs/course_generation.log
   ```

---

## Test Matrix
| ID | Objective | Steps Snapshot |
|----|-----------|----------------|
| P6-T1 | Confirm prompt extraction | Trigger course generation; inspect log for `has_custom_prompt=True` |
| P6-T2 | Validate PresGen-Core payload | Temporarily log request payload; ensure `custom_prompt`/`prompt_used` are populated |
| P6-T3 | Verify default fallback | Use workflow without prompt; log should show `has_custom_prompt=False` |
| P6-T4 | Logging & persistence | Ensure presentation URL stored; logs include prompt info |
| P6-T5 | Failure & retry | Simulate PresGen-Core failure then retry with prompt intact |

---

## Detailed Test Cases

### P6-T1 – Prompt Extraction
1. **Trigger generation**
   ```bash
   curl -X POST \
     "http://localhost:8000/api/v1/workflows/52014fe96b774e91b770ff20b24d7ff7/skills/data_engineering/generate-course" \
     -H "Content-Type: application/json"

     --
     (.venv) yitzchak@MacBookPro presgen-assess % curl -X POST \
     "http://localhost:8000/api/v1/workflows/52014fe96b774e91b770ff20b24d7ff7/skills/data_engineering/generate-course" \
     -H "Content-Type: application/json"
{"course_id":"bf55ea8d206b4e27ba2fa4acc940fe14","workflow_id":"52014fe9-6b77-4e91-b770-ff20b24d7ff7","skill_id":"data_engineering","skill_name":"Data Engineering","course_title":"Mastering Data Engineering","presentation_url":"https://drive.google.com/presentation/d/core_f6a32623bc68425391f3fae9fcb223a5/edit","video_url":"https://storage.googleapis.com/avatar-videos/avatar_c97b65871b4f48ab9ac5e7c086540c28.mp4","status":"completed","progress":100,"created_at":"2025-10-05T16:22:47.150474","updated_at":"2025-10-05T16:22:47.177008","completed_at":"2025-10-05T16:22:47.176754"}%  
   ```
2. **Review logs**
   ```bash
   tail -n 20 logs/course_generation.log | rg CUSTOM_PROMPT_LOADED
   ```
   - Expect `has_custom_prompt=True` and a truncated preview of the prompt.

   --
   (.venv) yitzchak@MacBookPro presgen-assess %    tail -n 20 logs/course_generation.log | rg CUSTOM_PROMPT_LOADED

2025-10-05 22:30:36 | INFO     | CUSTOM_PROMPT_LOADED | workflow_id=52014fe9-6b77-4e91-b770-ff20b24d7ff7 | has_custom_prompt=True | prompt_preview=You are an expert instructional designer creating educational presentations for professional certification preparation.

### P6-T2 – PresGen-Core Payload/Response
1. **Enable payload logging (temporary)**
   ```bash
   sed -n '1,160p' src/integrations/presgen_core/client.py
   ```
   - Optionally insert `print(payload)` before the mock return, or run under debugger.
2. **Run POST again (same command as P6-T1).**
3. **Inspect console/log** – Confirm payload includes `"custom_prompt": "..."` and response JSON contains `"prompt_used": "..."`.
4. **Remove temporary prints** after validating.

### P6-T3 – Default Fallback
1. **Identify workflow with empty prompt**
   ```bash
   sqlite3 test_database.db "SELECT workflow_executions.id FROM workflow_executions JOIN certification_profiles ON certification_profiles.id = workflow_executions.certification_profile_id WHERE certification_profiles.presentation_prompt IS NULL OR TRIM(certification_profiles.presentation_prompt) = '' LIMIT 1;"
   ```
2. **Trigger generation** using that workflow id and a valid `skill_id`:
   ```bash
   curl -X POST "http://localhost:8000/api/v1/workflows/<workflow_without_prompt>/skills/<skill_id>/generate-course" -H "Content-Type: application/json"
   ```
3. **Check log** – `CUSTOM_PROMPT_LOADED` should show `has_custom_prompt=False` yet subsequent core events should appear.

### P6-T4 – Logging & Persistence
1. After P6-T1 run, list generated courses:
   ```bash
   curl "http://localhost:8000/api/v1/workflows/52014fe96b774e91b770ff20b24d7ff7/courses" | jq
   ```
   - Ensure record shows `status":"completed"`, `presentation_url`, and (if applicable) `video_url`.
2. Inspect log sequence to confirm `PRESGEN_CORE_STARTED` → `PRESGEN_CORE_COMPLETED` with `prompt_used` attribute.

--
(.venv) yitzchak@MacBookPro presgen-assess % curl "http://localhost:8000/api/v1/workflows/52014fe96b774e91b770ff20b24d7ff7/courses" | jq
  % Total    % Received % Xferd  Average Speed   Time    Time     Time  Current
                                 Dload  Upload   Total   Spent    Left  Speed
  0     0    0     0    0     0      0      0 --:--:-- --:--:-- --:--:--    100  3945  100  3945    0     0  45911      0 --:--:-- --:--:-- --:--:-- 46411
[
  {
    "course_id": "bf55ea8d206b4e27ba2fa4acc940fe14",
    "workflow_id": "52014fe9-6b77-4e91-b770-ff20b24d7ff7",
    "skill_id": "data_engineering",
    "skill_name": "Data Engineering",
    "course_title": "Mastering Data Engineering",
    "presentation_url": "https://drive.google.com/presentation/d/core_f6a32623bc68425391f3fae9fcb223a5/edit",
    "video_url": "https://storage.googleapis.com/avatar-videos/avatar_c97b65871b4f48ab9ac5e7c086540c28.mp4",
    "status": "completed",
    "progress": 100,
    "created_at": "2025-10-05T16:22:47.150474",
    "updated_at": "2025-10-05T16:22:47.177008",
    "completed_at": "2025-10-05T16:22:47.176754"
  },
  {
    "course_id": "914c997aa25e46fdb2be71b5b6ec7091",
    "workflow_id": "52014fe9-6b77-4e91-b770-ff20b24d7ff7",
    "skill_id": "modeling",
    "skill_name": "Modeling",
    "course_title": "Mastering Modeling",
    "presentation_url": "https://drive.google.com/presentation/d/core_466bf19b76034be782e017bb0233bb1f/edit",
    "video_url": "https://storage.googleapis.com/avatar-videos/avatar_ee1c962cd1f34e03bee4c1716bc6291b.mp4",
    "status": "completed",
    "progress": 100,
    "created_at": "2025-10-05T14:08:10.169636",
    "updated_at": "2025-10-05T14:08:10.187085",
    "completed_at": "2025-10-05T14:08:10.186735"
  },
  {
    "course_id": "29571b8cd18b4e1591fb17918935dae6",
    "workflow_id": "52014fe9-6b77-4e91-b770-ff20b24d7ff7",
    "skill_id": "modeling",
    "skill_name": "Modeling",
    "course_title": "Mastering Modeling",
    "presentation_url": "https://drive.google.com/presentation/d/core_0db1869504d14c71accbca86017061f1/edit",
    "video_url": "https://storage.googleapis.com/avatar-videos/avatar_b7e41277798c4e8d81ed30a1e3ff412c.mp4",
    "status": "completed",
    "progress": 100,
    "created_at": "2025-10-05T14:05:36.447890",
    "updated_at": "2025-10-05T14:05:36.469575",
    "completed_at": "2025-10-05T14:05:36.469018"
  },
  {
    "course_id": "1ef268bfb2c44415b5a75377ca9258fc",
    "workflow_id": "52014fe9-6b77-4e91-b770-ff20b24d7ff7",
    "skill_id": "modeling",
    "skill_name": "Modeling",
    "course_title": "Mastering Modeling",
    "presentation_url": "https://drive.google.com/presentation/d/core_0c92c48187534120a10fbca1ef08f4d1/edit",
    "video_url": null,
    "status": "generating_video",
    "progress": 60,
    "created_at": "2025-10-05T14:04:30.188739",
    "updated_at": "2025-10-05T14:04:30.193212",
    "completed_at": null
  },
  {
    "course_id": "0db99146223c41f090e960754d0c68e4",
    "workflow_id": "52014fe9-6b77-4e91-b770-ff20b24d7ff7",
    "skill_id": "modeling",
    "skill_name": "Modeling",
    "course_title": "Mastering Modeling",
    "presentation_url": "https://drive.google.com/presentation/d/core_d66dbd39604d4518972cb9f9fc43457a/edit",
    "video_url": null,
    "status": "generating_video",
    "progress": 60,
    "created_at": "2025-10-05T14:04:16.681643",
    "updated_at": "2025-10-05T14:04:16.688244",
    "completed_at": null
  },
  {
    "course_id": "c5b43f7e81724705977ce7d8fc749221",
    "workflow_id": "52014fe9-6b77-4e91-b770-ff20b24d7ff7",
    "skill_id": "modeling",
    "skill_name": "Modeling",
    "course_title": "Mastering Modeling",
    "presentation_url": "https://drive.google.com/presentation/d/core_68b25828be8c4d73bb9b60ced986aa70/edit",
    "video_url": null,
    "status": "generating_video",
    "progress": 60,
    "created_at": "2025-10-05T14:01:11.908982",
    "updated_at": "2025-10-05T14:01:11.913732",
    "completed_at": null
  },
  {
    "course_id": "ee7a85c9149e4d4184a64899122e1dcf",
    "workflow_id": "52014fe9-6b77-4e91-b770-ff20b24d7ff7",
    "skill_id": "modeling",
    "skill_name": "Modeling",
    "course_title": "Mastering Modeling",
    "presentation_url": "https://drive.google.com/presentation/d/core_9709c1cf9c5a4862bfcccf6c6d0e6bf0/edit",
    "video_url": null,
    "status": "generating_video",
    "progress": 60,
    "created_at": "2025-10-05T14:00:58.814853",
    "updated_at": "2025-10-05T14:00:58.821557",
    "completed_at": null
  },
  {
    "course_id": "bf0d09642aee409998a2ed8eb25ef100",
    "workflow_id": "52014fe9-6b77-4e91-b770-ff20b24d7ff7",
    "skill_id": "modeling",
    "skill_name": "Modeling",
    "course_title": "Mastering Modeling",
    "presentation_url": "https://drive.google.com/presentation/d/core_c1fc68a8613a4686b3d45f30c9ead0e4/edit",
    "video_url": null,
    "status": "generating_video",
    "progress": 60,
    "created_at": "2025-10-05T13:51:26.532062",
    "updated_at": "2025-10-05T13:51:26.537444",
    "completed_at": null
  }
]

### P6-T5 – Failure & Retry
1. **Force failure** – Temporarily modify `PresGenCoreClient.generate_presentation` to raise an exception (e.g., `raise RuntimeError("Forced failure")`) or patch in a test harness.
2. **Trigger POST** (same as P6-T1) – API should return HTTP 502.
3. **Validate DB** – course row set to `status='failed'`, `error_message` populated.
4. **Revert code/enable mock**, rerun POST – logs should again show `has_custom_prompt=True` and success path with new presentation URL.

---

## Exit Criteria
- Prompt overrides surface in payloads, responses (`prompt_used`), and logs.
- Workflows without a prompt continue to function using defaults.
- Failure states capture prompt context and allow retries without manual cleanup.
- Documentation updated with findings/screenshots before closing Phase 6.
