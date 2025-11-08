# Gap Analysis Course Generation – Implementation Notes

This document captures the end-to-end plan for finishing the async course generation pipeline, uploading avatar videos to the shared Google Drive folder (`1iRBfFiD4fp_rsAUv2RN8J6K4Xrt1_t8f`), surfacing the public download link, and ensuring the embedded player loads the finished video. Each section includes concrete steps and code samples pulled from the current codebase.

---

## 1. Objectives
1. **Stop 504s** by returning from `generate_skill_course` immediately after the Google Slides deck is created.
2. **Move the long-running work** (PresGen-Core, PresGen-Avatar, Drive upload) into `poll_course_status`.
3. **Add rich telemetry** whenever a video is downloaded, uploaded to Drive, assigned a public link, and bound to the UI player.
4. **Update the UI workflow** so it polls the backend and renders both the download link and the embedded video when ready.

---

## 2. Backend Changes

### 2.1 Early return in `generate_skill_course`
File: `presgen-assess/src/service/api/v1/endpoints/workflows.py`

When slides finish uploading, we immediately mark the course as queued and return.

```python
# L3219-L3262 (abbrev.)
course.status = "pending_core_processing"
course.progress = 25
await db.commit()
await db.refresh(course)

return CourseGenerationResponse(
    course_id=course.id,
    status=course.status,
    progress=course.progress,
    presentation_url=course.presentation_url,
    drive_download_url=None,
    ...
)
```

**Action items**
1. Double-check that no blocking code remains below the return. Remove the legacy synchronous block or guard it behind feature flags/tests to prevent regressions.
2. Emit a `COURSE_GENERATION_QUEUED` event (already in place) so dashboards show the queued state.

### 2.2 `poll_course_status` orchestrates the pipeline
File: `presgen-assess/src/service/api/v1/endpoints/workflows.py`

The polling endpoint now owns the four phases:

```python
if course.status == "pending_core_processing":
    core_response = await presgen_core.generate_presentation(...)
    course.presgen_core_job_id = core_response.job_id
    course.status = "pending_avatar"
    course.progress = 50

if course.status == "pending_avatar":
    avatar_result = await avatar_client.generate_video(...)
    course.presgen_avatar_job_id = avatar_result.job_id
    course.status = "generating_video"
    course.progress = 60

avatar_status = await avatar_client.get_job_status(course.presgen_avatar_job_id)
if avatar_status.status == "completed":
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    filename = f"{{assessment_name}}-{{assessment_domain}}-{timestamp}.mp4"
    mp4_path = job_output_dir / filename
    ...
```

**Action items**
1. Ensure every branch commits progress before returning so the frontend sees monotonic status updates.
2. Guard Core/Avatar calls with retries or `CircuitOpenError` handling if those clients expose it.
3. Return `CourseGenerationResponse` on every poll so the UI always receives the latest progress + URLs.

### 2.3 Enhanced Drive upload telemetry
Files:
- `presgen-assess/src/service/api/v1/endpoints/workflows.py` (video download + Drive upload block @ L4217-L4284)
- `presgen-assess/src/services/google_forms_service.py` (`upload_video_to_drive` @ L446-L515)

Recommended log additions:

```python
logger.info(
    "📥 Downloading avatar output | workflow_id=%s | course_id=%s | src=%s | dest=%s",
    workflow_id_str,
    course.id,
    avatar_status.video_url,
    mp4_path,
)
...
logger.info(
    "📤 Uploading video to Drive | workflow_id=%s | course_id=%s | file=%s | folder=%s",
    workflow_id_str,
    course.id,
    mp4_path.name,
    drive_folder_id,
)
...
logger.info(
    "🔗 Drive link ready | workflow_id=%s | course_id=%s | url=%s",
    workflow_id_str,
    course.id,
    drive_download_url,
)
```

Inside `GoogleFormsService.upload_video_to_drive`, mirror the same metadata so future debugging only needs Drive logs:

```python
logger.info(
    "drive.upload.start | filename=%s | folder_id=%s | size_bytes=%s",
    filename,
    folder_id,
    Path(video_path).stat().st_size,
)
...
logger.info("drive.upload.permission_granted | file_id=%s", file_id)
```

Finally, log when the DB update finishes so we know the UI should refresh:

```python
logger.info(
    "🎬 Course assets persisted | workflow_id=%s | course_id=%s | video_url=%s",
    workflow_id_str,
    course.id,
    course.video_url,
)
```

### 2.4 API response schema additions
`presgen-assess/src/schemas/gap_analysis.py`

Verify the `CourseGenerationResponse` includes `drive_download_url`, `progress`, and `status` so the UI can consume everything from a single payload.

---

## 3. Frontend Integration Checklist
1. **Trigger:** On “Generate Course”, call the existing POST endpoint and look for `course_id` in the response (status should now be `pending_core_processing`).
2. **Polling:** Start polling `/api/presgen-assess/workflows/{workflowId}/skills/{skillId}/course-status` every 5–10 seconds until status becomes `completed` or `failed`. (The dashboard now calls this endpoint directly so the async pipeline and logging are exercised every poll.)
3. **Download Link:** When `drive_download_url` is non-null, render a button/link to the left of the “Generate Course” CTA.
4. **Embedded Player:** Use `video_url` (local proxy endpoint) as the `src` for the `<video>` element. Show a placeholder until status ≥ `generating_video`.
5. **Error State:** If `status === 'failed'`, surface `error_message` and stop polling.

---

## 4. Verification Steps
1. **Unit/Integration Tests**
   - Add async tests covering the new polling flow (mock Core/Avatar clients and assert progress transitions).
   - Test `upload_video_to_drive` by injecting a fake Drive client; assert logging payloads when possible.
2. **Manual QA**
   - Trigger a course, watch `logs/assess/workflows.log` for the new telemetry messages.
   - Confirm `generated_courses.drive_download_url` is populated in `data/assess/presgen_assess.db` once the poll endpoint finishes.
   - Load the dashboard to ensure the download link and embedded player appear.
3. **Regression Monitoring**
   - Inspect `uvicorn_access.log` to confirm POST `/generate-course` returns < 3s and no 504s appear.
   - Watch `presgen_assess_errors.log` for Drive or Avatar failures.

---

## 5. Rollout Notes
- Because migrations already added `drive_download_url`, no additional DB work is required.
- If a job was mid-flight during deployment, instruct users to hit the polling endpoint once to push it through the remaining stages.
- Keep `GOOGLE_DRIVE_COURSE_FOLDER_ID` in `.env` synchronized across environments so uploads land in the shared folder named in the requirements.

---

## 6. Appendix – Sample Poll Response
```json
{
  "course_id": "20251108_084947",
  "status": "completed",
  "progress": 100,
  "presentation_url": "https://docs.google.com/presentation/d/...",
  "video_url": "/api/presgen-assess/workflows/4b152322-.../courses/20251108_084947/video",
  "drive_download_url": "https://drive.google.com/uc?export=download&id=...",
  "presgen_core_job_id": "d1c6...",
  "presgen_avatar_job_id": "a7b3..."
}
```

Use this contract when wiring up the UI.
