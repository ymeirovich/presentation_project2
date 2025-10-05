# Sprint 4: Phase 5 Frontend Integration - TDD Manual Testing Guide

**Created**: 2025-10-05
**Sprint**: Sprint 4 - PresGen-Avatar Integration
**Scope**: Phase 5 (Recommended Courses UI + Avatar Video Playback)
**Status**: Ready for execution

---

## Overview
Phase 5 surfaces the per-skill course generation workflow inside the PresGen UI. These tests ensure the new "Generate Course" control, progress feedback, and inline video playback wire up correctly to the Phase 4 API endpoints.

---

## Prerequisites
- PresGen-Assess API running locally (`./venv/bin/uvicorn src.service.app:app --port 8000 --reload`).
- PresGen-UI dev server running (`npm run dev` inside `presgen-ui/`).
- Known workflow ID with recommended courses available (use `sqlite3 test_database.db "SELECT DISTINCT workflow_id, skill_id FROM recommended_courses LIMIT 1;"`).
yitzchak@MacBookPro presgen-assess % sqlite3 test_database.db "SELECT DISTINCT workflow_id, skill_id FROM recommended_courses LIMIT 1;"
19952bd09cfe44bc9460c4f521caca89|security

- Browser cleared of prior local storage/session data for a clean run.
- Optional: toggle `PRESGEN_USE_MOCK=false` to verify failure handling (see P5-T4).

---

## Test Matrix
| ID | Objective | Pass Criteria |
|----|-----------|---------------|
| P5-T1 | Button renders and triggers POST | "Generate Course" button enabled; clicking shows spinner and success toast |
| P5-T2 | Progress indicator updates | Progress bar moves from 0 → 100 as status API reports progress |
| P5-T3 | Video playback | Completed run surfaces inline video player with working controls |
| P5-T4 | Failure path feedback | With mock disabled, UI shows error toast, status badge flips to "Failed" |
| P5-T5 | Retry after failure | Re-enabling mock allows successful rerun; badge resets and video reappears |

---

## Test Cases

### P5-T1 – Trigger Generation
1. Navigate to `http://localhost:3001` (or configured UI port) and open the workflow's Recommended Courses tab.
2. Locate a course row with `generation_status` = `pending`.
3. Click **Generate Course**.
4. Expected: Button switches to spinner text "Generating…" and toast displays "Course generation started".

--
Clicked button, spinner, toast successful, loaded video player

### P5-T2 – Observe Progress
1. While generation is active, note the progress bar beneath the controls.
2. Expected: Value increments as the backend polls (mock mode jumps to 100 quickly).
3. Confirm status badge transitions from `Not Generated` → `Generating` → `Completed`.
--
Done

### P5-T3 – Video Playback
1. After success, ensure the video element renders below the card.
2. Click play; video starts streaming clip URL returned by backend. *(Note: current mock URL points to `storage.googleapis.com/avatar-videos/...` and returns HTTP 403 without signed credentials; treat presence of the video player as success in mock mode.)*
3. Refresh the page: course remains `Completed` and video persists (cached in component state after new POST, or triggers `already generated` toast).
4. Optional: `curl http://localhost:8000/api/v1/workflows/<workflow_uuid>/courses` to confirm the generated course row includes `status":"completed"` and the stored video URL.

### P5-T4 – Failure Handling
1. Stop/disable the avatar backend (`PRESGEN_USE_MOCK=false`).
2. Click **Generate Course** again.
3. Expected: Toast shows error message, badge changes to `Failed`, progress resets, and UI invites retry.
4. Restore `PRESGEN_USE_MOCK=true` afterwards.

--
Toast: Course Already Generated!

### P5-T5 – Retry Flow
1. With mock mode restored, click **Generate Course** for the failed skill.
2. Expected: Toast indicates restart, progress reaches 100, badge returns to `Completed`, video player reappears with the new asset.

---

## Exit Criteria
- Generate button, progress bar, and status badge behave as described across success/failure pathways.
- Video playback verified end-to-end inside the UI.
- QA notes include timestamps/screenshots of success, failure, and retry states before Sprint 4 hand-off.
