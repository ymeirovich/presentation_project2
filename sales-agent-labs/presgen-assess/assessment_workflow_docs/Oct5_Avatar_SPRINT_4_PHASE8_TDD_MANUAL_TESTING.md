# Sprint 4: Phase 8 Local MP4 Output – TDD Manual Testing Guide

**Created**: 2025-10-06  
**Sprint**: Sprint 4 – PresGen-Avatar Integration  
**Scope**: Phase 8 (timestamp job IDs, local avatar storage, UI download link)  
**Status**: Ready for execution

---

## Overview
Phase 8 locks down the non-mock flow: Course generations now produce timestamp-based job IDs, persist avatar MP4s under `avatar-output/jobs/{job_id}`, and surface a download link in the UI.

---

## Prerequisites
- PresGen-Assess running with `PRESGEN_USE_MOCK=false` and real Core/Avatar endpoints reachable.
- `.env` updated with `AVATAR_OUTPUT_DIR` (defaults to `presgen-assess/avatar-output`).
- OAuth token and service account credentials refreshed per Phase 6/7 steps.
- Clean log recommendation: `rm -f presgen-assess/logs/course_generation.log`.

---

## Test Matrix
| ID | Objective | Pass Criteria |
|----|-----------|---------------|
| P8-T1 | Timestamped course IDs | `generated_courses.id` matches `YYYYMMDD_HHMMSS[_suffix]` |
| P8-T2 | Local MP4 storage | MP4 saved to `avatar-output/workflow/jobs/{job_id}/avatar.mp4` |
| P8-T3 | Download endpoint | `GET /api/v1/workflows/{workflow}/courses/{course}/video` streams MP4 |
| P8-T4 | UI download link | Recommended Courses tab shows working “Download Video” link |

---

## Test Cases

### P8-T1 – Timestamped Course IDs
1. Trigger a generate-course POST or click “Generate Course” in the UI.
2. Inspect DB:  
   ```bash
   sqlite3 presgen-assess/test_database.db "SELECT id FROM generated_courses ORDER BY created_at DESC LIMIT 1;"
   ```
3. Expect `id` resembles `20251006_213612` (with optional short suffix).

### P8-T2 – Local MP4 Storage
1. After completion, list the job folder:  
   ```bash
   ls presgen-assess/avatar-output/<workflow_uuid>/jobs/
   ```
2. Ensure a file named `avatar-<skill>-<timestamp>.mp4` exists under the new job folder.
3. Optional: verify filename matches the skill/timestamp pattern and inspect metadata (`ffprobe` or `ls -lh`).

### P8-T3 – Backend Download Endpoint
1. Call the new endpoint:  
   ```bash
   curl -I "http://localhost:8000/api/v1/workflows/<workflow_uuid>/courses/<course_id>/video"
   ```
2. Response should be `200 OK` with `Content-Type: video/mp4`.
3. `curl -O` or browser navigation should download/stream the file.

### P8-T4 – UI Download Link
1. Open the Recommended Courses tab, locate the skill just generated.
2. Confirm a “Download Video” button/link appears.
3. Clicking should initiate download (verify file contents match local MP4).

---

## Exit Criteria
- Timestamp IDs verified across several skills.
- Avatar MP4s persist under `avatar-output` for completed courses.
- Download endpoint returns MP4 with no errors; UI link works in browser.
- Findings (including any issues) documented before closing Phase 8.
