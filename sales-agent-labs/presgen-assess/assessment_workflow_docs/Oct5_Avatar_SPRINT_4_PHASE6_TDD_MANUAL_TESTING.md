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
     "http://localhost:8000/api/v1/workflows/a25e885b465c40958d3350d292cbcef3/skills/data_engineering/generate-course" \
     -H "Content-Type: application/json"
   ```
2. **Review logs**
   ```bash
   tail -n 20 logs/course_generation.log | rg CUSTOM_PROMPT_LOADED
   ```
   - Expect `has_custom_prompt=True` and a truncated preview of the prompt.

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
   curl "http://localhost:8000/api/v1/workflows/a25e885b465c40958d3350d292cbcef3/courses" | jq
   ```
   - Ensure record shows `status":"completed"`, `presentation_url`, and (if applicable) `video_url`.
2. Inspect log sequence to confirm `PRESGEN_CORE_STARTED` → `PRESGEN_CORE_COMPLETED` with `prompt_used` attribute.

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
