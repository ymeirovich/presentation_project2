# Sprint 4: Phase 3 Enhanced Logging - TDD Manual Testing Guide

**Created**: 2025-10-05
**Sprint**: Sprint 4 - PresGen-Avatar Integration
**Scope**: Phase 3 (Course Generation Logging)
**Status**: Ready for execution

---

## Overview
Phase 3 hardens observability for individual course generation. These checks verify the rotating logger, event sequencing, and error-path coverage so support teams can diagnose avatar workflows from `logs/course_generation.log`.

---

## Prerequisites
- Phase 2 tests completed and mock course generation endpoint verified.
- Local API running: `./venv/bin/uvicorn src.service.app:app --port 8000 --reload`.
- Ensure clean log slate: `rm -f logs/course_generation.log` before the first test (optional but recommended).
- `PRESGEN_USE_MOCK=true` for success-path scenarios; toggle to `false` for failure injection.

---

## Test Matrix
| ID | Objective | Pass Criteria |
|----|-----------|---------------|
| P3-T1 | Logger bootstrap | File created, single handler attached, repeated imports do not duplicate events |
| P3-T2 | Success flow logging | All eleven events from plan appear once with workflow/skill context |
| P3-T3 | Progress updates | `PRESGEN_AVATAR_PROGRESS` logged when polling continues beyond initial queue |
| P3-T4 | Failure logging | With avatar failure, `COURSE_GENERATION_FAILED` captures error message |
| P3-T5 | Rotation safety | Logger keeps size < 10MB and writes to backup when threshold simulated |

---

## Test Cases

### P3-T1 – Logger Bootstrap
1. Drop into Python shell:
   ```python
   from src.services.course_generation_service import log_course_event, _ensure_logger
   log_course_event("LOGGER_SMOKE", foo="bar")
   logger = _ensure_logger()
   print(len(logger.handlers))
   ```
2. Expected: prints `1`. Re-running the snippet must keep the count at 1. Confirm `logs/course_generation.log` exists and contains `LOGGER_SMOKE` line.

### P3-T2 – Success Flow Logging
1. Set `PRESGEN_USE_MOCK=true`.
2. Trigger course generation (reuse workflow/skill from Phase 2):
   ```bash
   curl -X POST "http://localhost:8000/api/v1/workflows/<workflow_uuid>/skills/<skill_id>/generate-course"
   ```
3. Inspect log:
   ```bash
   tail -n 15 logs/course_generation.log
   ```
4. Expected: Sequential entries for `COURSE_GENERATION_STARTED` through `COURSE_GENERATION_COMPLETED`, all including `workflow_id` and `course_id`/`job_id` fields.

### P3-T3 – Progress Updates
1. Temporarily modify poll interval when testing (e.g. `?poll_interval_seconds=0` to speed up).
2. Verify log contains at least one `PRESGEN_AVATAR_PROGRESS` entry with `progress=100` for the mock flow.

### P3-T4 – Failure Logging
1. Stop the avatar service or set `PRESGEN_USE_MOCK=false` with no backend running.
2. Re-run the POST request.
3. Expected log tail shows `PRESGEN_AVATAR_STARTED` followed by `COURSE_GENERATION_FAILED` and `error=PresGen-Avatar generation failed`. API responds 502 as captured in Phase 2.
4. Reset `PRESGEN_USE_MOCK=true` afterwards.

### P3-T5 – Rotation Safety (Manual)
1. Use a helper script to write ~11MB of test log lines:
   ```python
   from src.services.course_generation_service import log_course_event
   for i in range(0, 120000):
       log_course_event("ROTATION_TEST", seq=i)
   ```
2. Expected: `logs/course_generation.log` remains under 10MB and an archive file such as `logs/course_generation.log.1` appears.
3. Clean up by removing rotation test entries if desired.

---

## Exit Criteria
- Success and failure flows produce complete event traces in the prescribed format.
- Logger handler count remains 1 after repeated imports.
- Rotation confirmed by presence of `.1` backup (or manual verification if skipped).
- Findings captured in Sprint 4 QA notes prior to handing off Phase 3.
