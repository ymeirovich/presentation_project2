# Sprint 4: Phase 7 Resilience & Error Handling – TDD Manual Testing Guide

**Created**: 2025-10-05  
**Sprint**: Sprint 4 – PresGen-Avatar Integration  
**Scope**: Phase 7 (Retry, backoff, and circuit breaker safeguards for PresGen-Core & PresGen-Avatar)  
**Status**: Ready for execution

---

## Overview
Phase 7 validates the new retry/backoff logic and circuit breaker safeguards added to the PresGen-Core and PresGen-Avatar clients. Tests cover successful runs, transient retries, forced failures, circuit-open responses, and recovery.

---

## Prerequisites
1. **Services running**
   ```bash
   # PresGen-Assess API
   cd /Users/yitzchak/Documents/learn/presentation_project/sales-agent-labs/presgen-assess
   ./venv/bin/uvicorn src.service.app:app --reload --port 8000
   ```

2. **Workflow + skill** – Use the prompt-enabled workflow validated in Phase 6:
   ```bash
   export WORKFLOW=52014fe9-6b77-4e91-b770-ff20b24d7ff7
   export SKILL=data_engineering
   ```

3. **Clean logs (optional)**
   ```bash
   rm -f logs/course_generation.log
   ```

4. **Environment** – Default mock mode is fine; the retry/circuit paths are exercised via env toggles below.

---

## Test Matrix
| ID | Objective | Command Snapshot |
|----|-----------|------------------|
| P7-T1 | Baseline success | `curl -X POST .../generate-course` (env defaults) |
| P7-T2 | PresGen-Core retry | Force failure once, observe retry + success |
| P7-T3 | PresGen-Core circuit break | Force repeated failures until 503 returned |
| P7-T4 | PresGen-Avatar retry/circuit | Same steps for avatar client |
| P7-T5 | Recovery | Unset toggles, wait for reset, confirm successful run |

---

## Detailed Test Cases

### P7-T1 – Baseline Success (Control)
1. Trigger generation:
   ```bash
   curl -X POST "http://localhost:8000/api/v1/workflows/$WORKFLOW/skills/$SKILL/generate-course" \
     -H "Content-Type: application/json"

     --
     (.venv) yitzchak@MacBookPro sales-agent-labs % curl -X POST "http://localhost:8000/api/v1/workflows/$WORKFLOW/skills/$SKILL/generate-course" \
     -H "Content-Type: application/json"
{"course_id":"bf55ea8d206b4e27ba2fa4acc940fe14","workflow_id":"52014fe9-6b77-4e91-b770-ff20b24d7ff7","skill_id":"data_engineering","skill_name":"Data Engineering","course_title":"Mastering Data Engineering","presentation_url":"https://drive.google.com/presentation/d/core_f6a32623bc68425391f3fae9fcb223a5/edit","video_url":"https://storage.googleapis.com/avatar-videos/avatar_c97b65871b4f48ab9ac5e7c086540c28.mp4","status":"completed","progress":100,"created_at":"2025-10-05T16:22:47.150474","updated_at":"2025-10-05T16:22:47.177008","completed_at":"2025-10-05T16:22:47.176754"}%      
   ```
2. Confirm response `status":"completed"` and log entries show normal flow.
3. Clear course record if desired (`sqlite3 ... DELETE FROM generated_courses WHERE workflow_id='<hex>' AND skill_id='$SKILL';`).

### P7-T2 – PresGen-Core Retry Path
1. Force a single failure:
   ```bash
   export PRESGEN_CORE_FORCE_FAIL=true
   ```
2. Trigger generation (same curl command). Expect initial failure logged with retries.
3. Inspect log:
   ```bash
   tail -n 40 logs/course_generation.log | rg "PRESGEN_CORE"
   ```
   - Look for `PRESGEN_CORE_FAILED` entries followed by retry warnings.
4. Unset toggle and rerun to ensure success:
   ```bash
   unset PRESGEN_CORE_FORCE_FAIL
   curl -X POST "http://localhost:8000/api/v1/workflows/$WORKFLOW/skills/$SKILL/generate-course" -H "Content-Type: application/json"
   ```

### P7-T3 – PresGen-Core Circuit Breaker
1. Trip circuit by forcing consecutive failures:
   ```bash
   export PRESGEN_CORE_FORCE_FAIL=true
   for i in {1..3}; do
     curl -s -o /dev/null -w "%{http_code}\n" \
       "http://localhost:8000/api/v1/workflows/$WORKFLOW/skills/$SKILL/generate-course" \
       -H "Content-Type: application/json"
   done
   ```
2. Final response should be HTTP `503` with detail `PresGen-Core temporarily unavailable`.
3. Log should contain `PRESGEN_CORE_CIRCUIT_OPEN`.
4. Wait ~60 seconds (circuit recovery window) or restart server, then `unset PRESGEN_CORE_FORCE_FAIL` and rerun to ensure success.

### P7-T4 – PresGen-Avatar Retry & Circuit
1. Repeat steps similar to T2/T3 using avatar toggle:
   ```bash
   export PRESGEN_AVATAR_FORCE_FAIL=true
   curl -X POST "http://localhost:8000/api/v1/workflows/$WORKFLOW/skills/$SKILL/generate-course" \
     -H "Content-Type: application/json"
   ```
   - Expect retries logged with `PRESGEN_AVATAR_CIRCUIT_OPEN` when threshold reached.
2. Clear toggle and rerun:
   ```bash
   unset PRESGEN_AVATAR_FORCE_FAIL
   curl -X POST "http://localhost:8000/api/v1/workflows/$WORKFLOW/skills/$SKILL/generate-course" -H "Content-Type: application/json"
   ```

### P7-T5 – Recovery Verification
1. After unsetting both toggles, wait 60 seconds (or restart API) to ensure circuits reset.
2. Trigger generation again; expect immediate success.
3. Verify `logs/course_generation.log` shows `PRESGEN_CORE_STARTED` → `PRESGEN_CORE_COMPLETED` with no circuit events.

---

## Exit Criteria
- Retries logged for forced failures; backoff behavior observed.
- Circuit breaker returns HTTP 503 with appropriate log entries when thresholds reached.
- After recovery window or toggles removal, normal operation resumes without manual DB cleanup.
- QA notes include timestamps/HTTP codes confirming resilience behavior.
