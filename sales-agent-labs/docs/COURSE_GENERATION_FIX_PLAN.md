# Course Generation Timeout & Polling Fix - Comprehensive Implementation Plan

**Document Version:** 1.0
**Date:** 2025-11-09
**Status:** Ready for Implementation
**Estimated Total Effort:** 8-12 hours across 4 phases

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Problem Analysis](#problem-analysis)
3. [Architecture Overview](#architecture-overview)
4. [Phase 1: Immediate Fixes](#phase-1-immediate-fixes)
5. [Phase 2: Backend Optimizations](#phase-2-backend-optimizations)
6. [Phase 3: Architectural Improvements](#phase-3-architectural-improvements)
7. [Phase 4: Monitoring & Observability](#phase-4-monitoring--observability)
8. [Testing Strategy](#testing-strategy)
9. [Deployment Plan](#deployment-plan)
10. [Rollback Procedures](#rollback-procedures)
11. [Success Metrics](#success-metrics)

---

## Executive Summary

### Problem Statement

When users click "Generate Course" in the UI, the system sometimes successfully generates videos, but often times out. The UI never displays the download link or renders the video player, even when generation succeeds. Polling continues and then stops with confusing errors.

### Root Cause

PresGen-Core takes >10 minutes to render presentations, exceeding configured timeouts. The `/course-status` endpoint blocks while retrying PresGen-Core calls, causing nginx to timeout (504). When Core eventually fails, the endpoint raises HTTP 502 instead of returning a proper failed response. The frontend receives HTTP 400/502/504 errors and cannot properly detect completion or failure states.

### Solution Overview

**Immediate (Phase 1):** Fix error handling to return proper responses instead of raising HTTP exceptions. Update nginx timeouts.

**Short-term (Phase 2):** Optimize retry logic and timeout configurations.

**Long-term (Phase 3):** Implement true async job processing using background workers.

### Impact

- **Users:** Clear error messages, proper video display when successful
- **System:** Reduced server load, better resource utilization
- **Operations:** Better observability, easier debugging

---

## Problem Analysis

### Current Flow

```
User clicks "Generate Course"
    ↓
POST /api/v1/workflows/{id}/skills/{skill}/courses
    ↓
Creates GeneratedCourse with status="pending_core_processing"
    ↓
Frontend starts polling GET /course-status every 3 seconds
    ↓
/course-status checks status:
    - If "pending_core_processing" → Calls PresGen-Core (blocks)
    - If "pending_avatar" → Calls PresGen-Avatar (blocks)
    - If "generating_video" → Polls Avatar status
    - If "completed" → Returns response with video URL
    ↓
PresGen-Core takes >10 minutes
    ↓
httpx.TimeoutException after 600s
    ↓
Client retries with backoff (3 attempts)
    ↓
Total blocking time: 20-30+ minutes
    ↓
Nginx times out after 300s → 504 error
    ↓
Backend eventually fails → Raises HTTP 502
    ↓
Frontend polls failed course → HTTP 400 "No avatar job ID found"
    ↓
User sees confusing error, video never displays
```

### Issues Identified

| ID | Issue | Location | Severity |
|----|-------|----------|----------|
| I-1 | `/course-status` blocks during PresGen-Core retries | `workflows.py:4084-4185` | CRITICAL |
| I-2 | HTTP 502 raised instead of returning failed response | `workflows.py:4166-4185` | CRITICAL |
| I-3 | HTTP 400 when polling failed course missing avatar job | `workflows.py:4290-4292` | HIGH |
| I-4 | Nginx timeout (300s) < Backend timeout (600s+) | `nginx.conf:189-191` | HIGH |
| I-5 | Frontend polls failed courses indefinitely | Frontend code | MEDIUM |
| I-6 | PresGen-Core retry logic too aggressive | `client.py:95-132` | MEDIUM |
| I-7 | PresGen-Core takes >10 minutes to render | PresGen-Core service | ROOT CAUSE |

### Log Evidence

```
2025-11-09 10:23:25 | CORE_ASYNC_START | course_id=20251108_081601
2025-11-09 10:23:42 | CORE_ASYNC_FAILED | error=PresGen-Core request timed out
2025-11-09 10:28:12 | CORE_ASYNC_FAILED | error=PresGen-Core request timed out
2025-11-09 10:33:16 | CORE_ASYNC_FAILED | error=PresGen-Core request timed out
...
10:29:15 - 10:34:03 | COURSE_STATUS_POLL | status=failed | progress=25 (every 3s)
```

### Dependency Map

```
nginx (300s timeout)
    ↓
presgen-assess /course-status endpoint
    ↓
PresGenCoreClient (600s timeout, 3 retries)
    ↓
PresGen-Core service (>10min render time)
```

---

## Architecture Overview

### Current Architecture

```
┌─────────────┐
│   Browser   │
│  (Frontend) │
└──────┬──────┘
       │ Poll every 3s
       ↓
┌─────────────┐
│    nginx    │ ← 300s timeout
│  (Reverse   │
│    Proxy)   │
└──────┬──────┘
       │
       ↓
┌─────────────────┐
│ presgen-assess  │
│  /course-status │ ← BLOCKING
│    endpoint     │
└──────┬──────────┘
       │
       ↓
┌─────────────────┐
│ PresGenCore     │ ← 600s timeout
│    Client       │    3 retries
└──────┬──────────┘
       │
       ↓
┌─────────────────┐
│ PresGen-Core    │ ← >10min render
│    Service      │
└─────────────────┘
```

### Target Architecture (Phase 3)

```
┌─────────────┐
│   Browser   │
└──────┬──────┘
       │ Poll every 3s
       ↓
┌─────────────┐
│    nginx    │ ← 60s timeout (status check only)
└──────┬──────┘
       │
       ↓
┌─────────────────┐
│ /course-status  │ ← NON-BLOCKING
│ (DB check only) │    Returns instantly
└─────────────────┘
       ↑
       │ Updates status
       │
┌──────────────────┐
│ Background Worker│
│   (Celery/      │
│    asyncio)     │
└──────┬───────────┘
       │ Async call
       ↓
┌─────────────────┐
│ PresGen-Core    │ ← 900s timeout
│    Service      │    1 retry
└─────────────────┘
```

---

## Phase 1: Immediate Fixes

**Objective:** Stop HTTP 400/502/504 errors, ensure proper error responses
**Effort:** 1-2 hours
**Priority:** P0 (Must have)
**Deployment:** Can be deployed independently

### 1.1: Fix PresGen-Core Error Handling

**File:** `presgen-assess/src/service/api/v1/endpoints/workflows.py`
**Lines:** 4166-4185
**Issue:** Raises HTTP 502 instead of returning proper failed response

#### Current Code

```python
except Exception as e:
    await presgen_core.close()
    logger.exception(
        "❌ PresGen-Core failed | workflow_id=%s | course_id=%s | skill_id=%s",
        workflow_id_str,
        course.id,
        skill_id,
    )
    log_course_event(
        "CORE_ASYNC_FAILED",
        workflow_id=workflow_id_str,
        skill_id=skill_id,
        course_id=course.id,
        error=str(e),
    )
    course.status = "failed"
    course.error_message = f"PresGen-Core failed: {str(e)}"
    await db.commit()
    await db.refresh(course)
    raise HTTPException(status_code=502, detail="PresGen-Core generation failed")
```

#### New Code

```python
except Exception as e:
    await presgen_core.close()

    # Determine error type for better messaging
    is_timeout = isinstance(e, PresGenCoreTimeoutError)
    is_circuit_open = isinstance(e, CircuitOpenError)
    is_http_error = isinstance(e, PresGenCoreHTTPError)

    # Set appropriate error message
    if is_timeout:
        error_msg = "PresGen-Core request timed out. The presentation generation took longer than expected. Please try again or contact support if this persists."
    elif is_circuit_open:
        error_msg = "PresGen-Core service is temporarily unavailable. Please try again in a few minutes."
    elif is_http_error:
        error_msg = f"PresGen-Core service error: {str(e)}"
    else:
        error_msg = f"PresGen-Core generation failed: {str(e)}"

    logger.exception(
        "❌ PresGen-Core failed | workflow_id=%s | course_id=%s | skill_id=%s | error_type=%s",
        workflow_id_str,
        course.id,
        skill_id,
        type(e).__name__,
    )
    log_course_event(
        "CORE_ASYNC_FAILED",
        workflow_id=workflow_id_str,
        skill_id=skill_id,
        course_id=course.id,
        error=str(e),
        error_type=type(e).__name__,
    )

    # Update course status in database
    course.status = "failed"
    course.error_message = error_msg
    await db.commit()
    await db.refresh(course)

    # CRITICAL: Return proper response instead of raising HTTP exception
    # This allows frontend to properly detect and display the failure
    return CourseGenerationResponse(
        course_id=course.id,
        workflow_id=workflow_id_str,
        skill_id=skill_id,
        skill_name=skill_course.skill_name,
        course_title=course.course_title,
        presentation_url=course.presentation_url,
        video_url=None,
        drive_download_url=None,
        presgen_core_job_id=course.presgen_core_job_id,
        presgen_core_download_url=None,
        presgen_avatar_job_id=None,
        local_video_path=None,
        status="failed",
        progress=course.progress,
        error_message=error_msg,
        created_at=course.created_at,
        updated_at=course.updated_at,
        completed_at=None,
    )
```

#### Import Additions

Add to top of file:

```python
from src.integrations.presgen_core.client import (
    PresGenCoreTimeoutError,
    PresGenCoreHTTPError,
    CircuitOpenError,
)
```

#### Rationale

1. **No HTTP Exception:** Returns `CourseGenerationResponse` with `status="failed"` instead of raising HTTP 502
2. **Clear Error Messages:** User-friendly error messages based on error type
3. **Frontend Compatibility:** Frontend receives expected schema, can display error properly
4. **Logging:** Enhanced logging includes error type for debugging

#### Testing

```python
# Test 1: Verify timeout returns failed response
async def test_core_timeout_returns_failed_response():
    # Mock PresGen-Core to raise timeout
    with patch.object(PresGenCoreClient, 'generate_presentation') as mock_gen:
        mock_gen.side_effect = PresGenCoreTimeoutError("Timeout")

        response = await client.get(
            f"/api/v1/workflows/{workflow_id}/skills/{skill_id}/course-status"
        )

        # Should return 200 with failed status, NOT 502
        assert response.status_code == 200
        data = response.json()
        assert data['status'] == 'failed'
        assert 'timed out' in data['error_message']
        assert data['presgen_avatar_job_id'] is None

# Test 2: Verify circuit breaker returns failed response
async def test_circuit_open_returns_failed_response():
    with patch.object(PresGenCoreClient, 'generate_presentation') as mock_gen:
        mock_gen.side_effect = CircuitOpenError("Circuit open")

        response = await client.get(
            f"/api/v1/workflows/{workflow_id}/skills/{skill_id}/course-status"
        )

        assert response.status_code == 200
        data = response.json()
        assert data['status'] == 'failed'
        assert 'temporarily unavailable' in data['error_message']
```

---

### 1.2: Fix Avatar Error Handling

**File:** `presgen-assess/src/service/api/v1/endpoints/workflows.py`
**Lines:** 4247-4266
**Issue:** Raises HTTP 502 on Avatar submission failure

#### Current Code

```python
except Exception as e:
    await avatar_client.close()
    logger.exception(
        "❌ PresGen-Avatar failed | workflow_id=%s | course_id=%s | skill_id=%s",
        workflow_id_str,
        course.id,
        skill_id,
    )
    log_course_event(
        "AVATAR_SUBMISSION_FAILED",
        workflow_id=workflow_id_str,
        skill_id=skill_id,
        course_id=course.id,
        error=str(e),
    )
    course.status = "failed"
    course.error_message = f"PresGen-Avatar failed: {str(e)}"
    await db.commit()
    await db.refresh(course)
    raise HTTPException(status_code=502, detail="PresGen-Avatar generation failed")
```

#### New Code

```python
except Exception as e:
    await avatar_client.close()

    # Determine error type
    from src.integrations.presgen_avatar.client import (
        PresGenAvatarTimeoutError,
        PresGenAvatarHTTPError,
    )

    is_timeout = isinstance(e, PresGenAvatarTimeoutError)
    is_http_error = isinstance(e, PresGenAvatarHTTPError)

    # Set appropriate error message
    if is_timeout:
        error_msg = "Video generation timed out. Please try again or contact support."
    elif is_http_error:
        error_msg = f"Video generation service error: {str(e)}"
    else:
        error_msg = f"Video generation failed: {str(e)}"

    logger.exception(
        "❌ PresGen-Avatar submission failed | workflow_id=%s | course_id=%s | skill_id=%s | error_type=%s",
        workflow_id_str,
        course.id,
        skill_id,
        type(e).__name__,
    )
    log_course_event(
        "AVATAR_SUBMISSION_FAILED",
        workflow_id=workflow_id_str,
        skill_id=skill_id,
        course_id=course.id,
        error=str(e),
        error_type=type(e).__name__,
    )

    course.status = "failed"
    course.error_message = error_msg
    await db.commit()
    await db.refresh(course)

    # Return proper response instead of raising
    return CourseGenerationResponse(
        course_id=course.id,
        workflow_id=workflow_id_str,
        skill_id=skill_id,
        skill_name=course.skill_name,
        course_title=course.course_title,
        presentation_url=course.presentation_url,
        video_url=None,
        drive_download_url=None,
        presgen_core_job_id=course.presgen_core_job_id,
        presgen_core_download_url=course.presgen_core_download_url,
        presgen_avatar_job_id=None,
        local_video_path=None,
        status="failed",
        progress=course.progress,
        error_message=error_msg,
        created_at=course.created_at,
        updated_at=course.updated_at,
        completed_at=None,
    )
```

---

### 1.3: Remove Avatar Job ID Validation

**File:** `presgen-assess/src/service/api/v1/endpoints/workflows.py`
**Lines:** 4290-4292
**Issue:** Raises HTTP 400 when polling failed course without avatar job

#### Current Code

```python
# Check avatar job status
if not course.presgen_avatar_job_id:
    raise HTTPException(status_code=400, detail="No avatar job ID found")

avatar_client = PresGenAvatarClient(base_url=os.getenv("PRESGEN_AVATAR_URL"))
```

#### New Code

```python
# If course already failed (e.g., Core timeout), return failed status
# without requiring avatar job ID
if course.status == "failed":
    logger.info(
        "Course already failed | workflow_id=%s | course_id=%s | error=%s",
        workflow_id_str,
        course.id,
        course.error_message,
    )
    return CourseGenerationResponse(
        course_id=course.id,
        workflow_id=workflow_id_str,
        skill_id=skill_id,
        skill_name=course.skill_name,
        course_title=course.course_title,
        presentation_url=course.presentation_url,
        video_url=course.video_url,
        drive_download_url=None,
        presgen_core_job_id=course.presgen_core_job_id,
        presgen_core_download_url=course.presgen_core_download_url,
        presgen_avatar_job_id=course.presgen_avatar_job_id,
        local_video_path=None,
        status="failed",
        progress=course.progress,
        error_message=course.error_message,
        created_at=course.created_at,
        updated_at=course.updated_at,
        completed_at=None,
    )

# Check avatar job ID for non-failed courses
if not course.presgen_avatar_job_id:
    # This shouldn't happen in normal flow, but handle gracefully
    logger.warning(
        "Course in status '%s' but missing avatar job ID | workflow_id=%s | course_id=%s",
        course.status,
        workflow_id_str,
        course.id,
    )
    # Return current status instead of raising error
    return CourseGenerationResponse(
        course_id=course.id,
        workflow_id=workflow_id_str,
        skill_id=skill_id,
        skill_name=course.skill_name,
        course_title=course.course_title,
        presentation_url=course.presentation_url,
        video_url=course.video_url,
        drive_download_url=course.drive_download_url,
        presgen_core_job_id=course.presgen_core_job_id,
        presgen_core_download_url=course.presgen_core_download_url,
        presgen_avatar_job_id=None,
        local_video_path=None,
        status=course.status,
        progress=course.progress,
        error_message=course.error_message,
        created_at=course.created_at,
        updated_at=course.updated_at,
        completed_at=course.completed_at,
    )

avatar_client = PresGenAvatarClient(base_url=os.getenv("PRESGEN_AVATAR_URL"))
```

#### Rationale

1. **Early Return for Failed Courses:** If course failed during Core processing, return failed status immediately
2. **Graceful Degradation:** If avatar job ID missing for other reasons, log warning and return current status
3. **No HTTP Exceptions:** Never raises 400 error, always returns valid response
4. **Better UX:** Frontend receives proper failed status and can display error message

#### Testing

```python
async def test_failed_course_without_avatar_job_returns_failed():
    # Create course that failed during Core processing
    course = GeneratedCourse(
        status="failed",
        error_message="PresGen-Core request timed out",
        presgen_avatar_job_id=None,  # No avatar job created yet
    )

    response = await client.get(
        f"/api/v1/workflows/{workflow_id}/skills/{skill_id}/course-status"
    )

    # Should return 200 with failed status, NOT 400
    assert response.status_code == 200
    data = response.json()
    assert data['status'] == 'failed'
    assert data['error_message'] == 'PresGen-Core request timed out'
    assert data['presgen_avatar_job_id'] is None
```

---

### 1.4: Update Nginx Configuration

**File:** `nginx/nginx.conf`
**Lines:** 174-195
**Issue:** Nginx times out before backend finishes retrying Core

#### Current Code

```nginx
# ===== Assess API =====
location /api/ {
    # Rate limiting
    limit_req zone=api_limit burst=20 nodelay;

    proxy_pass http://presgen_assess;
    proxy_http_version 1.1;

    # Headers
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;

    # Long timeouts for AI processing
    proxy_connect_timeout 300s;
    proxy_send_timeout 300s;
    proxy_read_timeout 300s;

    # Buffering for file uploads
    proxy_request_buffering off;
}
```

#### New Code

```nginx
# ===== Course Status Polling (Extended Timeout) =====
# MUST come BEFORE general /api/ location block
# Specific route for course status polling needs longer timeout
# to allow PresGen-Core retries to complete
location ~ ^/api/v1/workflows/[^/]+/skills/[^/]+/course-status$ {
    # Rate limiting - allow frequent polling
    limit_req zone=api_limit burst=30 nodelay;

    proxy_pass http://presgen_assess;
    proxy_http_version 1.1;

    # Headers
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;

    # Extended timeouts for PresGen-Core processing
    # Must be > PRESGEN_CORE_TIMEOUT_SECONDS * max_retry_attempts
    # Current: 600s * 3 attempts = 1800s, use 2100s for safety
    proxy_connect_timeout 900s;    # 15 minutes
    proxy_send_timeout 900s;       # 15 minutes
    proxy_read_timeout 2100s;      # 35 minutes (covers all retries)

    # Disable buffering for real-time status updates
    proxy_request_buffering off;
    proxy_buffering off;
}

# ===== Assess API (General) =====
location /api/ {
    # Rate limiting
    limit_req zone=api_limit burst=20 nodelay;

    proxy_pass http://presgen_assess;
    proxy_http_version 1.1;

    # Headers
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;

    # Standard timeouts for most API endpoints
    proxy_connect_timeout 300s;
    proxy_send_timeout 300s;
    proxy_read_timeout 300s;

    # Buffering for file uploads
    proxy_request_buffering off;
}
```

#### Location Block Ordering

**CRITICAL:** In nginx, location blocks are matched in a specific order:

1. Exact match: `location = /path`
2. Preferential prefix: `location ^~ /path`
3. Regex match: `location ~ regex` (processed in order of appearance)
4. Prefix match: `location /path`

Our regex location `location ~ ^/api/v1/workflows/[^/]+/skills/[^/]+/course-status$` MUST appear BEFORE the prefix location `location /api/` to be matched first.

#### Rationale

1. **Specific Route:** Only applies extended timeout to course-status endpoint
2. **Safety Margin:** 2100s timeout covers worst case (600s * 3 retries + overhead)
3. **Other Endpoints Unaffected:** General API endpoints keep 300s timeout
4. **Prevents 504 Errors:** Nginx waits long enough for backend to complete

#### Testing

```bash
# Test 1: Verify nginx config is valid
docker-compose exec nginx nginx -t

# Test 2: Reload nginx configuration
docker-compose exec nginx nginx -s reload

# Test 3: Check access logs show no 504 errors for course-status
docker-compose exec nginx tail -f /var/log/nginx/access.log | grep course-status

# Test 4: Verify timeout settings are applied
# Make a request and check it doesn't timeout before 2100s
curl -v -u demo:demo123 \
  'http://localhost/api/v1/workflows/{workflow_id}/skills/{skill_id}/course-status' \
  --max-time 2200
```

---

### 1.5: Update CourseGenerationResponse Schema

**File:** `presgen-assess/src/service/api/v1/schemas.py` (or wherever response schemas are defined)
**Issue:** Ensure `error_message` field is properly included in response

#### Check Current Schema

```python
class CourseGenerationResponse(BaseModel):
    course_id: str
    workflow_id: str
    skill_id: str
    skill_name: str
    course_title: str
    presentation_url: Optional[str] = None
    video_url: Optional[str] = None
    drive_download_url: Optional[str] = None
    presgen_core_job_id: Optional[str] = None
    presgen_core_download_url: Optional[str] = None
    presgen_avatar_job_id: Optional[str] = None
    local_video_path: Optional[str] = None
    status: str
    progress: int
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime] = None
    # ADD THIS if not present:
    error_message: Optional[str] = None
```

#### If Missing, Add Field

```python
class CourseGenerationResponse(BaseModel):
    # ... existing fields ...

    # Error message when status="failed"
    error_message: Optional[str] = Field(
        None,
        description="User-friendly error message when course generation fails"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "course_id": "20251108_081601",
                "workflow_id": "4b152322-48ae-4ff5-a49f-757950b3686a",
                "skill_id": "data_engineering",
                "status": "failed",
                "progress": 25,
                "error_message": "PresGen-Core request timed out. Please try again.",
                # ... other fields ...
            }
        }
```

---

### Phase 1 Implementation Checklist

- [ ] 1.1: Update PresGen-Core error handling in workflows.py
- [ ] 1.2: Update PresGen-Avatar error handling in workflows.py
- [ ] 1.3: Remove avatar job ID validation in workflows.py
- [ ] 1.4: Add course-status specific nginx location block
- [ ] 1.5: Verify error_message field in CourseGenerationResponse
- [ ] Add imports for exception types
- [ ] Run unit tests for error scenarios
- [ ] Run integration tests for full flow
- [ ] Update API documentation if needed
- [ ] Deploy to staging environment
- [ ] Test in staging with real PresGen-Core timeouts
- [ ] Deploy to production

---

## Phase 2: Backend Optimizations

**Objective:** Reduce retry attempts, optimize timeout configurations
**Effort:** 1-2 hours
**Priority:** P1 (Should have)
**Deployment:** Can be deployed with or after Phase 1

### 2.1: Reduce PresGen-Core Retry Attempts

**File:** `presgen-assess/src/integrations/presgen_core/client.py`
**Lines:** 37-49
**Issue:** 3 retry attempts means 30+ minutes of blocking on timeout

#### Current Code

```python
def __init__(
    self,
    base_url: Optional[str] = None,
    api_key: Optional[str] = None,
    use_mock: Optional[bool] = None,
    voice_profile_name: Optional[str] = None,
    quality_level: Optional[str] = None,
    use_cache: Optional[bool] = None,
    max_attempts: int = 3,  # ← CURRENT DEFAULT
    base_backoff_seconds: float = 1.0,  # ← CURRENT DEFAULT
    failure_threshold: int = 3,
    recovery_seconds: int = 60,
    timeout_seconds: Optional[float] = None,
) -> None:
```

#### New Code

```python
def __init__(
    self,
    base_url: Optional[str] = None,
    api_key: Optional[str] = None,
    use_mock: Optional[bool] = None,
    voice_profile_name: Optional[str] = None,
    quality_level: Optional[str] = None,
    use_cache: Optional[bool] = None,
    max_attempts: int = 2,  # ← REDUCED FROM 3 TO 2
    base_backoff_seconds: float = 3.0,  # ← INCREASED FROM 1.0 TO 3.0
    failure_threshold: int = 3,
    recovery_seconds: int = 60,
    timeout_seconds: Optional[float] = None,
) -> None:
```

#### Rationale

**Why Reduce Retries?**

1. If PresGen-Core takes >10 minutes on first attempt, it's unlikely to succeed on retry
2. The timeout is due to slow rendering, not transient network issues
3. Retrying just delays the inevitable failure and blocks the endpoint longer

**Why Increase Backoff?**

1. If we do retry, give PresGen-Core more time to recover
2. Longer backoff reduces load on Core service
3. 3 seconds is still short enough for good UX

**Impact:**
- Reduces worst-case blocking time from ~30 minutes to ~20 minutes
- Faster failure detection → better UX
- Reduced load on PresGen-Core service

#### Testing

```python
async def test_core_timeout_retries_once():
    """Verify client retries exactly once after timeout"""
    call_count = 0

    async def mock_generate(request):
        nonlocal call_count
        call_count += 1
        raise PresGenCoreTimeoutError("Timeout")

    client = PresGenCoreClient(max_attempts=2)
    with patch.object(client, '_generate_via_http', side_effect=mock_generate):
        with pytest.raises(PresGenCoreTimeoutError):
            await client.generate_presentation(request)

    assert call_count == 2  # Initial + 1 retry
```

---

### 2.2: Make Timeout Configurable via Environment

**File:** `presgen-assess/.env` or `docker-compose.yml`
**Objective:** Allow operators to adjust timeout without code changes

#### Add Environment Variable

**Option A: .env file**

```bash
# PresGen-Core timeout configuration
# How long to wait for Core presentation generation before timing out (seconds)
# Increase if presentations legitimately take longer than 10 minutes
PRESGEN_CORE_TIMEOUT_SECONDS=900

# Maximum retry attempts for Core requests
# Set to 1 to disable retries (fail fast)
PRESGEN_CORE_MAX_ATTEMPTS=2

# Backoff time between retries (seconds)
PRESGEN_CORE_BACKOFF_SECONDS=3
```

**Option B: docker-compose.yml**

```yaml
services:
  presgen-assess:
    environment:
      - PRESGEN_CORE_TIMEOUT_SECONDS=900
      - PRESGEN_CORE_MAX_ATTEMPTS=2
      - PRESGEN_CORE_BACKOFF_SECONDS=3
```

#### Update Config File

**File:** `presgen-assess/src/common/config.py`

```python
class Settings(BaseSettings):
    # Existing settings...

    # PresGen-Core configuration
    presgen_core_url: str = "http://presgen-core:8080"
    presgen_core_timeout_seconds: float = Field(
        default=900,
        description="Timeout for PresGen-Core presentation generation (seconds)"
    )
    presgen_core_max_attempts: int = Field(
        default=2,
        description="Maximum retry attempts for PresGen-Core requests"
    )
    presgen_core_backoff_seconds: float = Field(
        default=3.0,
        description="Backoff time between PresGen-Core retries (seconds)"
    )
```

#### Update Client Initialization

**File:** `presgen-assess/src/service/api/v1/endpoints/workflows.py`

```python
# Current
presgen_core = PresGenCoreClient(base_url=os.getenv("PRESGEN_CORE_URL"))

# New - use settings for configuration
from src.common.config import settings

presgen_core = PresGenCoreClient(
    base_url=settings.presgen_core_url,
    timeout_seconds=settings.presgen_core_timeout_seconds,
    max_attempts=settings.presgen_core_max_attempts,
    base_backoff_seconds=settings.presgen_core_backoff_seconds,
)
```

#### Testing

```bash
# Test different timeout values
docker-compose down
PRESGEN_CORE_TIMEOUT_SECONDS=1200 docker-compose up -d presgen-assess

# Verify setting is picked up
docker-compose exec presgen-assess env | grep PRESGEN_CORE

# Test timeout behavior with short timeout
PRESGEN_CORE_TIMEOUT_SECONDS=30 pytest tests/test_core_timeout.py
```

---

### 2.3: Add Circuit Breaker Tuning

**File:** `presgen-assess/src/integrations/presgen_core/client.py`
**Current:** Circuit opens after 3 failures, recovers after 60 seconds
**Issue:** May be too aggressive for transient issues

#### Current Circuit Breaker Settings

```python
def __init__(
    # ...
    failure_threshold: int = 3,      # Opens circuit after 3 failures
    recovery_seconds: int = 60,      # Recovers after 60 seconds
):
```

#### Make Configurable

**Config:**

```python
class Settings(BaseSettings):
    # Circuit breaker settings
    presgen_core_circuit_failure_threshold: int = Field(
        default=5,  # Increased from 3
        description="Number of failures before circuit opens"
    )
    presgen_core_circuit_recovery_seconds: int = Field(
        default=120,  # Increased from 60
        description="Seconds before circuit attempts recovery"
    )
```

**Client Initialization:**

```python
presgen_core = PresGenCoreClient(
    base_url=settings.presgen_core_url,
    timeout_seconds=settings.presgen_core_timeout_seconds,
    max_attempts=settings.presgen_core_max_attempts,
    base_backoff_seconds=settings.presgen_core_backoff_seconds,
    failure_threshold=settings.presgen_core_circuit_failure_threshold,
    recovery_seconds=settings.presgen_core_circuit_recovery_seconds,
)
```

#### Rationale

- Timeouts don't necessarily mean the service is down
- Opening circuit too quickly prevents legitimate retries
- Longer recovery time prevents cascade failures

---

### Phase 2 Implementation Checklist

- [ ] 2.1: Reduce max_attempts from 3 to 2 in PresGenCoreClient
- [ ] 2.1: Increase base_backoff from 1.0 to 3.0 seconds
- [ ] 2.2: Add timeout configuration to Settings class
- [ ] 2.2: Add max_attempts configuration to Settings class
- [ ] 2.2: Add backoff configuration to Settings class
- [ ] 2.2: Update client initialization to use settings
- [ ] 2.3: Make circuit breaker thresholds configurable
- [ ] 2.3: Update environment variables documentation
- [ ] Add unit tests for new configuration
- [ ] Update deployment documentation
- [ ] Deploy to staging
- [ ] Verify configuration changes take effect
- [ ] Monitor retry behavior in logs

---

## Phase 3: Architectural Improvements

**Objective:** Implement true async job processing
**Effort:** 6-8 hours
**Priority:** P2 (Nice to have, long-term solution)
**Deployment:** Requires coordinated backend + infrastructure changes

### 3.1: Background Job Queue Architecture

#### Overview

Currently, the `/course-status` endpoint is synchronous - it blocks while calling PresGen-Core and PresGen-Avatar. This is the root cause of timeout issues.

**Solution:** Decouple status polling from actual processing:

1. Status endpoint only reads from database (instant response)
2. Background worker processes PresGen-Core/Avatar calls asynchronously
3. Worker updates database when complete
4. Frontend polls status endpoint (fast, never times out)

#### Architecture Diagram

```
┌──────────────────────────────────────────────────────────┐
│                     User Request                         │
└────────────┬─────────────────────────────────────────────┘
             │
             ↓
┌────────────────────────────────────────────────────────┐
│  POST /workflows/{id}/skills/{skill}/courses           │
│                                                         │
│  1. Create GeneratedCourse (status="queued")           │
│  2. Submit job to background queue                     │
│  3. Return immediately with course ID                  │
└────────────┬───────────────────────────────────────────┘
             │
             │  Job submitted
             ↓
┌─────────────────────────────────────────────────────────┐
│           Background Worker (Celery/AsyncIO)            │
│                                                          │
│  1. Pick up job from queue                              │
│  2. Update status → "pending_core_processing"           │
│  3. Call PresGen-Core (can take >10 min, doesn't matter)│
│  4. Update status → "pending_avatar"                    │
│  5. Call PresGen-Avatar                                 │
│  6. Poll Avatar until complete                          │
│  7. Upload to Drive                                     │
│  8. Update status → "completed" with URLs               │
└─────────────────────────────────────────────────────────┘
             │
             │  Updates database
             ↓
┌─────────────────────────────────────────────────────────┐
│             PostgreSQL Database                          │
│                                                          │
│  GeneratedCourse table with status field                │
└──────────┬──────────────────────────────────────────────┘
           │
           │  Frontend polls (every 3s)
           ↓
┌─────────────────────────────────────────────────────────┐
│  GET /workflows/{id}/skills/{skill}/course-status       │
│                                                          │
│  1. Read course from database (instant)                 │
│  2. Return current status                               │
│  3. NO blocking calls to external services              │
└─────────────────────────────────────────────────────────┘
```

#### Benefits

1. **No Timeout Issues:** Status endpoint returns instantly
2. **Scalability:** Can run multiple background workers
3. **Resilience:** Worker can retry without blocking HTTP requests
4. **Monitoring:** Easy to track job queue depth, processing times
5. **Better UX:** Responsive UI, clear progress indicators

---

### 3.2: Implementation Options

#### Option A: Celery + Redis (Recommended)

**Pros:**
- Industry standard for Python async tasks
- Built-in retry logic, monitoring, scheduling
- Horizontal scalability
- Good tooling (Flower for monitoring)

**Cons:**
- Requires Redis infrastructure
- Additional complexity

**Setup:**

```python
# requirements.txt
celery[redis]==5.3.4
redis==5.0.1
```

```python
# src/celery_app.py
from celery import Celery
from src.common.config import settings

celery_app = Celery(
    'presgen_assess',
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)

celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600,  # 1 hour hard limit
    task_soft_time_limit=3300,  # 55 minutes soft limit
)
```

```python
# src/tasks/course_generation.py
from src.celery_app import celery_app
from src.integrations.presgen_core.client import PresGenCoreClient
from src.integrations.presgen_avatar.client import PresGenAvatarClient
from src.models.generated_course import GeneratedCourse
from sqlalchemy.orm import Session

@celery_app.task(bind=True, max_retries=2)
def generate_course_async(
    self,
    workflow_id: str,
    skill_id: str,
    course_id: str,
):
    """
    Background task to generate course presentation and video.

    This runs in a separate worker process, so it can take as long as needed
    without blocking HTTP requests.
    """
    logger.info(
        "Starting course generation task | workflow_id=%s | skill_id=%s | course_id=%s",
        workflow_id, skill_id, course_id
    )

    # Create new database session (not shared with web process)
    db = SessionLocal()

    try:
        # Step 1: Get course from database
        course = db.query(GeneratedCourse).filter_by(id=course_id).first()
        if not course:
            raise ValueError(f"Course {course_id} not found")

        # Step 2: Call PresGen-Core (can take >10 minutes, no problem)
        course.status = "pending_core_processing"
        course.progress = 25
        db.commit()

        core_client = PresGenCoreClient()
        try:
            core_response = await core_client.generate_presentation(...)

            course.presgen_core_job_id = core_response.job_id
            course.presgen_core_download_url = core_response.download_url
            course.presentation_url = core_response.presentation_url
            course.status = "pending_avatar"
            course.progress = 50
            db.commit()

        except Exception as e:
            logger.error("Core generation failed: %s", e)
            course.status = "failed"
            course.error_message = f"Presentation generation failed: {str(e)}"
            db.commit()
            raise

        # Step 3: Call PresGen-Avatar
        course.status = "generating_video"
        course.progress = 60
        db.commit()

        avatar_client = PresGenAvatarClient()
        try:
            avatar_result = await avatar_client.generate_video(...)

            course.presgen_avatar_job_id = avatar_result.job_id
            course.progress = 70
            db.commit()

            # Step 4: Poll Avatar until complete
            final_result = await avatar_client.poll_until_complete(
                avatar_result.job_id,
                max_wait_seconds=1800,  # 30 minutes
                poll_interval_seconds=10,
            )

            course.local_video_path = final_result.output_path
            course.progress = 90
            db.commit()

        except Exception as e:
            logger.error("Avatar generation failed: %s", e)
            course.status = "failed"
            course.error_message = f"Video generation failed: {str(e)}"
            db.commit()
            raise

        # Step 5: Upload to Google Drive
        course.status = "uploading_to_drive"
        course.progress = 95
        db.commit()

        drive_service = GoogleDriveService()
        drive_url = await drive_service.upload_video(
            course.local_video_path,
            f"{course.course_title}.mp4"
        )

        course.drive_download_url = drive_url
        course.video_url = drive_url
        course.status = "completed"
        course.progress = 100
        course.completed_at = datetime.utcnow()
        db.commit()

        logger.info(
            "Course generation completed | workflow_id=%s | course_id=%s | drive_url=%s",
            workflow_id, course_id, drive_url
        )

    except Exception as e:
        logger.exception(
            "Course generation task failed | workflow_id=%s | course_id=%s",
            workflow_id, course_id
        )
        # Celery will retry based on max_retries setting
        raise self.retry(exc=e, countdown=60)

    finally:
        db.close()
```

**Modified Course Creation Endpoint:**

```python
@router.post(
    "/workflows/{workflow_id}/skills/{skill_id}/courses",
    response_model=CourseGenerationResponse,
)
async def create_course(
    workflow_id: str,
    skill_id: str,
    db: AsyncSession = Depends(get_async_db),
):
    """
    Create a new course generation job.
    Returns immediately with course ID.
    Frontend polls /course-status for progress.
    """

    # Create course record
    course = GeneratedCourse(
        id=generate_course_id(),
        workflow_id=workflow_id,
        skill_id=skill_id,
        status="queued",
        progress=0,
        created_at=datetime.utcnow(),
    )
    db.add(course)
    await db.commit()
    await db.refresh(course)

    # Submit to background queue (non-blocking)
    generate_course_async.delay(
        workflow_id=workflow_id,
        skill_id=skill_id,
        course_id=course.id,
    )

    logger.info(
        "Course generation queued | workflow_id=%s | skill_id=%s | course_id=%s",
        workflow_id, skill_id, course.id
    )

    # Return immediately
    return CourseGenerationResponse(
        course_id=course.id,
        workflow_id=workflow_id,
        skill_id=skill_id,
        status="queued",
        progress=0,
        created_at=course.created_at,
    )
```

**Modified Status Endpoint:**

```python
@router.get(
    "/workflows/{workflow_id}/skills/{skill_id}/course-status",
    response_model=CourseGenerationResponse,
)
async def get_course_status(
    workflow_id: str,
    skill_id: str,
    db: AsyncSession = Depends(get_async_db),
):
    """
    Get current course generation status.

    This endpoint now ONLY reads from the database.
    It does NOT call PresGen-Core or PresGen-Avatar.
    Background worker handles all external service calls.
    """

    # Find most recent course for this workflow + skill
    course = await db.execute(
        select(GeneratedCourse)
        .where(GeneratedCourse.workflow_id == workflow_id)
        .where(GeneratedCourse.skill_id == skill_id)
        .order_by(GeneratedCourse.created_at.desc())
        .limit(1)
    )
    course = course.scalar_one_or_none()

    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    logger.info(
        "Course status polled | workflow_id=%s | course_id=%s | status=%s | progress=%s",
        workflow_id, course.id, course.status, course.progress
    )

    # Return current status (instant, no external calls)
    return CourseGenerationResponse(
        course_id=course.id,
        workflow_id=workflow_id,
        skill_id=skill_id,
        skill_name=course.skill_name,
        course_title=course.course_title,
        presentation_url=course.presentation_url,
        video_url=course.video_url,
        drive_download_url=course.drive_download_url,
        presgen_core_job_id=course.presgen_core_job_id,
        presgen_core_download_url=course.presgen_core_download_url,
        presgen_avatar_job_id=course.presgen_avatar_job_id,
        local_video_path=course.local_video_path,
        status=course.status,
        progress=course.progress,
        error_message=course.error_message,
        created_at=course.created_at,
        updated_at=course.updated_at,
        completed_at=course.completed_at,
    )
```

**Docker Compose Changes:**

```yaml
services:
  # Add Redis for Celery
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 3s
      retries: 3

  # Existing presgen-assess service
  presgen-assess:
    # ... existing config ...
    environment:
      - CELERY_BROKER_URL=redis://redis:6379/0
      - CELERY_RESULT_BACKEND=redis://redis:6379/0
    depends_on:
      - redis

  # New Celery worker service
  presgen-assess-worker:
    build:
      context: ./presgen-assess
      dockerfile: Dockerfile
    command: celery -A src.celery_app worker --loglevel=info --concurrency=2
    environment:
      - CELERY_BROKER_URL=redis://redis:6379/0
      - CELERY_RESULT_BACKEND=redis://redis:6379/0
      - DATABASE_URL=${DATABASE_URL}
      - PRESGEN_CORE_URL=http://presgen-core:8080
      - PRESGEN_AVATAR_URL=http://presgen-avatar:8081
    depends_on:
      - redis
      - postgres
      - presgen-core
    volumes:
      - ./presgen-assess:/app
      - course_videos:/app/output
    restart: unless-stopped

volumes:
  redis_data:
  course_videos:
```

---

#### Option B: asyncio.create_task() (Simpler, Current Approach)

**Pros:**
- No additional infrastructure needed
- Simpler to implement
- Already partially implemented in codebase

**Cons:**
- Tasks lost on server restart
- No built-in monitoring
- Harder to scale horizontally
- No persistence of job state

**Current Implementation:**

```python
# src/service/background_jobs.py (existing)
class PresentationGenerationJob:
    """Async job for background presentation generation"""

    def __init__(self, workflow_id, skill_id, presentation_id):
        self.workflow_id = workflow_id
        self.skill_id = skill_id
        self.presentation_id = presentation_id
        self.task = None

    async def run(self):
        """Execute the presentation generation in background"""
        # Similar logic to Celery task above
        pass

# Create task
job = PresentationGenerationJob(workflow_id, skill_id, presentation_id)
job.task = asyncio.create_task(job.run())
job_queue.add_job(presentation_id, job)
```

**Recommendation:** Use Option A (Celery) for production, it's more robust.

---

### 3.3: Investigate PresGen-Core Performance

**Objective:** Understand why Core takes >10 minutes and optimize if possible

#### Investigation Steps

1. **Enable PresGen-Core Debug Logging**

```yaml
# docker-compose.yml
services:
  presgen-core:
    environment:
      - LOG_LEVEL=DEBUG
      - PROFILE_REQUESTS=true
```

2. **Check PresGen-Core Logs**

```bash
# View Core logs during generation
docker-compose logs -f presgen-core | grep -E "presentation-only|TIMING|PERFORMANCE"

# Look for:
# - Google Slides API call times
# - LLM content generation times
# - Slide population times
# - Total request duration
```

3. **Profile a Request**

```python
# Add timing to Core client
import time

start = time.time()
response = await presgen_core.generate_presentation(request)
elapsed = time.time() - start

logger.info(
    "Core generation timing | total=%.2fs | breakdown=%s",
    elapsed,
    response.timing_breakdown  # If Core returns this
)
```

4. **Check for Common Bottlenecks**

- **Google Slides API Rate Limits:** Core may be hitting rate limits
- **LLM Token Limits:** Large presentations may hit token limits
- **Slide Count:** More slides = longer generation time
- **Cache Misses:** Check if cache is enabled and working
- **Network Latency:** Check Core → Google APIs latency

5. **Optimization Opportunities**

```python
# Enable caching in Core client
presgen_core = PresGenCoreClient(
    use_cache=True,  # ← Enable this
    quality_level="fast",  # Use fast mode for testing
)
```

```python
# Reduce slide count in request
request = PresGenPresentationRequest(
    target_duration_minutes=5,  # Fewer slides, faster generation
    # ...
)
```

6. **Monitor Core Service Resources**

```bash
# Check CPU/Memory usage
docker stats presgen-core

# Check if Core is CPU or I/O bound
docker-compose exec presgen-core top
```

#### Expected Findings

Based on the logs showing 10+ minute renders, likely causes:

1. **Google Slides API Calls:** Each slide may require multiple API calls
2. **LLM Generation:** GPT-4 content generation for slides is slow
3. **No Caching:** Same presentations being regenerated from scratch
4. **Rate Limiting:** Hitting Google API quotas

#### Recommended Optimizations

1. Enable aggressive caching in PresGen-Core
2. Use faster LLM model (GPT-3.5) for testing
3. Reduce slide count for demos
4. Implement slide template caching
5. Batch Google Slides API calls

---

### Phase 3 Implementation Checklist

- [ ] 3.1: Decide between Celery vs asyncio approach
- [ ] 3.1: Set up Redis if using Celery
- [ ] 3.1: Create celery_app.py configuration
- [ ] 3.1: Implement generate_course_async task
- [ ] 3.1: Modify POST /courses endpoint to queue job
- [ ] 3.1: Modify GET /course-status to only read database
- [ ] 3.1: Update docker-compose.yml with worker service
- [ ] 3.1: Add Celery monitoring (Flower)
- [ ] 3.1: Test background job execution
- [ ] 3.1: Test job retry on failure
- [ ] 3.1: Test status polling during long-running job
- [ ] 3.2: Enable PresGen-Core debug logging
- [ ] 3.2: Profile several generation requests
- [ ] 3.2: Identify performance bottlenecks
- [ ] 3.2: Implement optimizations
- [ ] 3.2: Measure improvement
- [ ] Update nginx timeout (can reduce to 60s for status endpoint)
- [ ] Update API documentation
- [ ] Create migration plan from sync to async
- [ ] Test complete flow end-to-end
- [ ] Deploy to staging
- [ ] Monitor job queue in production

---

## Phase 4: Monitoring & Observability

**Objective:** Better visibility into system behavior
**Effort:** 2-3 hours
**Priority:** P2
**Deployment:** Can be deployed incrementally

### 4.1: Enhanced Logging

#### Add Structured Logging

**File:** `presgen-assess/src/utils/logging_config.py`

```python
import logging
import json
from datetime import datetime
from typing import Any, Dict

class StructuredFormatter(logging.Formatter):
    """
    Output logs as structured JSON for easier parsing and analysis.
    """

    def format(self, record: logging.LogRecord) -> str:
        log_data: Dict[str, Any] = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        # Add custom fields
        if hasattr(record, "workflow_id"):
            log_data["workflow_id"] = record.workflow_id
        if hasattr(record, "course_id"):
            log_data["course_id"] = record.course_id
        if hasattr(record, "skill_id"):
            log_data["skill_id"] = record.skill_id
        if hasattr(record, "duration_ms"):
            log_data["duration_ms"] = record.duration_ms

        return json.dumps(log_data)

# Configure root logger
def configure_structured_logging():
    handler = logging.StreamHandler()
    handler.setFormatter(StructuredFormatter())

    root_logger = logging.getLogger()
    root_logger.addHandler(handler)
    root_logger.setLevel(logging.INFO)
```

#### Add Timing Metrics

**File:** `presgen-assess/src/service/api/v1/endpoints/workflows.py`

```python
import time
from contextlib import contextmanager

@contextmanager
def log_timing(operation: str, **kwargs):
    """Context manager to log operation timing"""
    start = time.time()
    try:
        yield
    finally:
        duration_ms = int((time.time() - start) * 1000)
        logger.info(
            f"{operation} completed",
            extra={
                "duration_ms": duration_ms,
                **kwargs
            }
        )

# Usage in endpoint:
async def get_course_status(...):
    with log_timing("course_status_poll", workflow_id=workflow_id, course_id=course.id):
        # ... existing logic ...
```

#### Add Course Generation Metrics

```python
async def generate_course_async(...):
    start_time = datetime.utcnow()

    try:
        # ... generation logic ...

        if course.status == "completed":
            total_duration = (datetime.utcnow() - start_time).total_seconds()

            logger.info(
                "Course generation completed",
                extra={
                    "workflow_id": workflow_id,
                    "course_id": course_id,
                    "total_duration_seconds": total_duration,
                    "core_duration_ms": course.presgen_core_processing_time_ms,
                    "avatar_duration_ms": course.presgen_avatar_processing_time_ms,
                }
            )
```

---

### 4.2: Metrics Collection

#### Add Prometheus Metrics

**Install:**

```bash
pip install prometheus-client
```

**Setup:**

```python
# src/utils/metrics.py
from prometheus_client import Counter, Histogram, Gauge
import time

# Course generation metrics
course_generation_total = Counter(
    'course_generation_total',
    'Total course generation attempts',
    ['status']  # success, failed, timeout
)

course_generation_duration = Histogram(
    'course_generation_duration_seconds',
    'Course generation duration',
    ['stage']  # core, avatar, upload, total
)

course_generation_in_progress = Gauge(
    'course_generation_in_progress',
    'Number of courses currently being generated'
)

presgen_core_timeout_total = Counter(
    'presgen_core_timeout_total',
    'Total PresGen-Core timeouts'
)

presgen_core_request_duration = Histogram(
    'presgen_core_request_duration_seconds',
    'PresGen-Core request duration',
    buckets=[60, 120, 300, 600, 900, 1200, 1800]  # 1min to 30min
)

# Usage in code:
def generate_course_async(...):
    course_generation_in_progress.inc()
    start = time.time()

    try:
        # ... generation logic ...

        if course.status == "completed":
            course_generation_total.labels(status='success').inc()
        else:
            course_generation_total.labels(status='failed').inc()

    except PresGenCoreTimeoutError:
        presgen_core_timeout_total.inc()
        course_generation_total.labels(status='timeout').inc()
        raise

    finally:
        course_generation_in_progress.dec()
        duration = time.time() - start
        course_generation_duration.labels(stage='total').observe(duration)
```

**Expose Metrics Endpoint:**

```python
# src/service/api/v1/endpoints/metrics.py
from fastapi import APIRouter
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
from starlette.responses import Response

router = APIRouter()

@router.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint"""
    return Response(
        generate_latest(),
        media_type=CONTENT_TYPE_LATEST
    )
```

---

### 4.3: Alerting

#### Define Alert Conditions

```yaml
# prometheus/alerts.yml
groups:
  - name: course_generation
    interval: 30s
    rules:
      # Alert if timeout rate > 50%
      - alert: HighCourseTimeoutRate
        expr: |
          rate(presgen_core_timeout_total[5m]) /
          rate(course_generation_total[5m]) > 0.5
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High course generation timeout rate"
          description: "{{ $value | humanizePercentage }} of courses are timing out"

      # Alert if generation takes > 20 minutes on average
      - alert: SlowCourseGeneration
        expr: |
          histogram_quantile(0.5,
            rate(course_generation_duration_seconds_bucket{stage="total"}[10m])
          ) > 1200
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "Course generation is slow"
          description: "Median generation time is {{ $value | humanizeDuration }}"

      # Alert if queue depth > 10
      - alert: HighCourseQueueDepth
        expr: course_generation_in_progress > 10
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High course generation queue depth"
          description: "{{ $value }} courses are currently being generated"
```

---

### 4.4: Dashboard

#### Grafana Dashboard JSON

```json
{
  "dashboard": {
    "title": "Course Generation Monitoring",
    "panels": [
      {
        "title": "Course Generation Rate",
        "targets": [
          {
            "expr": "rate(course_generation_total[5m])",
            "legendFormat": "{{status}}"
          }
        ],
        "type": "graph"
      },
      {
        "title": "Generation Duration (p50, p95, p99)",
        "targets": [
          {
            "expr": "histogram_quantile(0.50, rate(course_generation_duration_seconds_bucket[5m]))",
            "legendFormat": "p50"
          },
          {
            "expr": "histogram_quantile(0.95, rate(course_generation_duration_seconds_bucket[5m]))",
            "legendFormat": "p95"
          },
          {
            "expr": "histogram_quantile(0.99, rate(course_generation_duration_seconds_bucket[5m]))",
            "legendFormat": "p99"
          }
        ],
        "type": "graph"
      },
      {
        "title": "Timeout Rate",
        "targets": [
          {
            "expr": "rate(presgen_core_timeout_total[5m]) / rate(course_generation_total[5m])",
            "legendFormat": "Timeout Rate"
          }
        ],
        "type": "graph"
      },
      {
        "title": "Courses In Progress",
        "targets": [
          {
            "expr": "course_generation_in_progress",
            "legendFormat": "In Progress"
          }
        ],
        "type": "gauge"
      }
    ]
  }
}
```

---

### Phase 4 Implementation Checklist

- [ ] 4.1: Implement structured logging formatter
- [ ] 4.1: Add timing context manager
- [ ] 4.1: Add duration logging to key operations
- [ ] 4.2: Install prometheus-client
- [ ] 4.2: Define Prometheus metrics
- [ ] 4.2: Add metrics collection to course generation
- [ ] 4.2: Expose /metrics endpoint
- [ ] 4.3: Configure Prometheus scraping
- [ ] 4.3: Define alert rules
- [ ] 4.3: Set up alert notifications (Slack/PagerDuty)
- [ ] 4.4: Create Grafana dashboard
- [ ] 4.4: Add dashboard to repository
- [ ] Test metrics collection
- [ ] Test alerts fire correctly
- [ ] Document metrics and alerts

---

## Testing Strategy

### Unit Tests

#### Test Error Handling

```python
# tests/test_course_status_errors.py
import pytest
from unittest.mock import AsyncMock, patch
from src.integrations.presgen_core.client import PresGenCoreTimeoutError
from src.service.api.v1.endpoints.workflows import get_course_status

class TestCourseStatusErrors:

    @pytest.mark.asyncio
    async def test_core_timeout_returns_failed_response(self, test_client, test_db):
        """Verify timeout returns proper failed response, not HTTP 502"""

        # Create course in pending_core_processing state
        course = await create_test_course(
            status="pending_core_processing",
            workflow_id="test-workflow",
            skill_id="test-skill"
        )

        # Mock PresGen-Core to raise timeout
        with patch('src.service.api.v1.endpoints.workflows.PresGenCoreClient') as mock_client:
            mock_client.return_value.generate_presentation = AsyncMock(
                side_effect=PresGenCoreTimeoutError("Timeout after 600s")
            )

            # Call status endpoint
            response = await test_client.get(
                f"/api/v1/workflows/test-workflow/skills/test-skill/course-status"
            )

            # Should return 200 with failed status, NOT 502
            assert response.status_code == 200, f"Expected 200, got {response.status_code}"

            data = response.json()
            assert data['status'] == 'failed'
            assert 'timed out' in data['error_message'].lower()
            assert data['presgen_avatar_job_id'] is None

            # Verify course was updated in database
            updated_course = await test_db.get(GeneratedCourse, course.id)
            assert updated_course.status == 'failed'
            assert updated_course.error_message is not None

    @pytest.mark.asyncio
    async def test_failed_course_without_avatar_job_returns_gracefully(self, test_client, test_db):
        """Verify failed course without avatar job doesn't raise HTTP 400"""

        # Create course that failed during Core processing
        course = await create_test_course(
            status="failed",
            error_message="PresGen-Core request timed out",
            presgen_avatar_job_id=None,  # No avatar job created
            workflow_id="test-workflow",
            skill_id="test-skill"
        )

        # Poll status
        response = await test_client.get(
            f"/api/v1/workflows/test-workflow/skills/test-skill/course-status"
        )

        # Should return 200 with failed status, NOT 400
        assert response.status_code == 200

        data = response.json()
        assert data['status'] == 'failed'
        assert data['error_message'] == 'PresGen-Core request timed out'
        assert data['presgen_avatar_job_id'] is None

    @pytest.mark.asyncio
    async def test_avatar_failure_returns_failed_response(self, test_client, test_db):
        """Verify Avatar errors return proper failed response, not HTTP 502"""

        course = await create_test_course(
            status="pending_avatar",
            presgen_core_job_id="core-123",
            presgen_core_download_url="https://example.com/video.mp4",
            workflow_id="test-workflow",
            skill_id="test-skill"
        )

        with patch('src.service.api.v1.endpoints.workflows.PresGenAvatarClient') as mock_client:
            mock_client.return_value.generate_video = AsyncMock(
                side_effect=Exception("Avatar service unavailable")
            )

            response = await test_client.get(
                f"/api/v1/workflows/test-workflow/skills/test-skill/course-status"
            )

            assert response.status_code == 200  # Not 502

            data = response.json()
            assert data['status'] == 'failed'
            assert 'Avatar' in data['error_message'] or 'Video generation' in data['error_message']
```

#### Test Retry Logic

```python
# tests/test_presgen_core_retry.py
import pytest
from unittest.mock import AsyncMock, patch
from src.integrations.presgen_core.client import PresGenCoreClient, PresGenCoreTimeoutError

class TestPresGenCoreRetry:

    @pytest.mark.asyncio
    async def test_retries_on_timeout(self):
        """Verify client retries configured number of times"""

        call_count = 0

        async def mock_generate(request):
            nonlocal call_count
            call_count += 1
            raise PresGenCoreTimeoutError("Timeout")

        client = PresGenCoreClient(max_attempts=2, base_backoff_seconds=0.1)

        with patch.object(client, '_generate_via_http', side_effect=mock_generate):
            with pytest.raises(PresGenCoreTimeoutError):
                await client.generate_presentation(mock_request)

        assert call_count == 2  # Initial + 1 retry

    @pytest.mark.asyncio
    async def test_succeeds_on_second_attempt(self):
        """Verify retry succeeds if subsequent attempt works"""

        call_count = 0

        async def mock_generate(request):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise PresGenCoreTimeoutError("Timeout")
            return PresGenPresentationResponse(success=True, job_id="test-123")

        client = PresGenCoreClient(max_attempts=2)

        with patch.object(client, '_generate_via_http', side_effect=mock_generate):
            response = await client.generate_presentation(mock_request)

        assert call_count == 2
        assert response.success is True
```

---

### Integration Tests

#### Test Complete Course Generation Flow

```python
# tests/integration/test_course_generation_flow.py
import pytest
from unittest.mock import patch, AsyncMock

@pytest.mark.integration
@pytest.mark.asyncio
async def test_successful_course_generation_flow(test_client, test_db):
    """
    Test complete happy path:
    1. Create course
    2. Poll status (pending_core_processing)
    3. Mock Core completes
    4. Poll status (pending_avatar)
    5. Mock Avatar completes
    6. Poll status (completed)
    """

    # Step 1: Create course
    create_response = await test_client.post(
        "/api/v1/workflows/test-workflow/skills/test-skill/courses",
        json={"custom_prompt": "Test prompt"}
    )
    assert create_response.status_code == 200

    course_data = create_response.json()
    assert course_data['status'] in ['queued', 'pending_core_processing']

    # Step 2: Poll while in Core processing
    with patch('src.service.api.v1.endpoints.workflows.PresGenCoreClient') as mock_core:
        mock_core.return_value.generate_presentation = AsyncMock(
            return_value=PresGenPresentationResponse(
                success=True,
                job_id="core-123",
                presentation_url="https://slides.google.com/...",
                download_url="https://example.com/video.mp4"
            )
        )

        status_response = await test_client.get(
            "/api/v1/workflows/test-workflow/skills/test-skill/course-status"
        )
        assert status_response.status_code == 200

        status_data = status_response.json()
        assert status_data['status'] == 'pending_avatar'
        assert status_data['presgen_core_job_id'] == 'core-123'

    # Step 3: Poll while in Avatar processing
    with patch('src.service.api.v1.endpoints.workflows.PresGenAvatarClient') as mock_avatar:
        mock_avatar.return_value.generate_video = AsyncMock(
            return_value=AvatarJobResponse(job_id="avatar-456")
        )
        mock_avatar.return_value.get_job_status = AsyncMock(
            return_value=AvatarJobStatus(
                job_id="avatar-456",
                status="completed",
                progress=100,
                output_path="/tmp/video.mp4"
            )
        )

        status_response = await test_client.get(
            "/api/v1/workflows/test-workflow/skills/test-skill/course-status"
        )

        # Should eventually reach completed
        assert status_response.status_code == 200
        status_data = status_response.json()
        assert status_data['status'] in ['generating_video', 'uploading_to_drive', 'completed']

@pytest.mark.integration
@pytest.mark.asyncio
async def test_course_generation_with_core_timeout(test_client, test_db):
    """
    Test timeout scenario:
    1. Create course
    2. Mock Core times out
    3. Verify status returns failed
    4. Verify subsequent polls return same failed status
    """

    # Create course
    create_response = await test_client.post(
        "/api/v1/workflows/test-workflow/skills/test-skill/courses",
        json={"custom_prompt": "Test prompt"}
    )
    assert create_response.status_code == 200

    # Mock Core timeout
    with patch('src.service.api.v1.endpoints.workflows.PresGenCoreClient') as mock_core:
        mock_core.return_value.generate_presentation = AsyncMock(
            side_effect=PresGenCoreTimeoutError("Timeout after 600s")
        )

        status_response = await test_client.get(
            "/api/v1/workflows/test-workflow/skills/test-skill/course-status"
        )

        # Should return failed status
        assert status_response.status_code == 200  # Not 502!

        status_data = status_response.json()
        assert status_data['status'] == 'failed'
        assert 'timeout' in status_data['error_message'].lower()

    # Poll again - should return same failed status without calling Core again
    status_response = await test_client.get(
        "/api/v1/workflows/test-workflow/skills/test-skill/course-status"
    )

    assert status_response.status_code == 200
    status_data = status_response.json()
    assert status_data['status'] == 'failed'
```

---

### Load Tests

```python
# tests/load/test_course_polling.py
import asyncio
import aiohttp
from datetime import datetime

async def poll_course_status(session, workflow_id, skill_id, max_polls=100):
    """Simulate frontend polling behavior"""

    url = f"http://localhost:8000/api/v1/workflows/{workflow_id}/skills/{skill_id}/course-status"

    for i in range(max_polls):
        async with session.get(url) as response:
            if response.status != 200:
                print(f"Poll {i}: HTTP {response.status}")
                return False

            data = await response.json()
            status = data['status']

            print(f"Poll {i}: status={status}, progress={data['progress']}")

            if status in ['completed', 'failed']:
                return True

        await asyncio.sleep(3)  # Poll every 3 seconds

    return False

async def test_concurrent_polling():
    """Test multiple courses being polled simultaneously"""

    async with aiohttp.ClientSession() as session:
        # Start 10 concurrent course generations
        tasks = []
        for i in range(10):
            task = poll_course_status(
                session,
                workflow_id=f"load-test-{i}",
                skill_id="test-skill"
            )
            tasks.append(task)

        start = datetime.utcnow()
        results = await asyncio.gather(*tasks)
        elapsed = (datetime.utcnow() - start).total_seconds()

        success_rate = sum(results) / len(results)

        print(f"Completed {len(results)} courses in {elapsed}s")
        print(f"Success rate: {success_rate * 100}%")

        assert success_rate >= 0.9, "Success rate should be >= 90%"

if __name__ == "__main__":
    asyncio.run(test_concurrent_polling())
```

---

### Manual Testing Checklist

#### Phase 1 Testing

- [ ] Deploy Phase 1 fixes to staging
- [ ] Start new course generation
- [ ] Verify course created with status="queued" or "pending_core_processing"
- [ ] Poll /course-status endpoint
- [ ] If Core times out:
  - [ ] Verify response is HTTP 200 (not 502)
  - [ ] Verify response has status="failed"
  - [ ] Verify error_message contains user-friendly text
  - [ ] Verify presgen_avatar_job_id is null
- [ ] Continue polling failed course
  - [ ] Verify subsequent polls return HTTP 200 (not 400)
  - [ ] Verify status remains "failed"
  - [ ] Verify error message persists
- [ ] Check nginx logs: `docker-compose logs nginx | grep 504`
  - [ ] Verify no 504 errors for /course-status
- [ ] Check presgen-assess logs
  - [ ] Verify proper error logging with context
  - [ ] Verify Core retry attempts logged
- [ ] Check frontend UI
  - [ ] Verify error message displayed clearly
  - [ ] Verify polling stops after receiving failed status
  - [ ] Verify no JavaScript errors in console

#### Phase 2 Testing

- [ ] Set PRESGEN_CORE_TIMEOUT_SECONDS=900 in env
- [ ] Set PRESGEN_CORE_MAX_ATTEMPTS=2 in env
- [ ] Restart presgen-assess service
- [ ] Verify environment variables picked up: `docker-compose exec presgen-assess env | grep PRESGEN_CORE`
- [ ] Start course generation
- [ ] If timeout occurs, verify only 2 attempts (initial + 1 retry)
- [ ] Measure time from start to failure
  - [ ] Should be ~18-20 minutes (900s * 2) instead of 30+ minutes
- [ ] Verify backoff between retries is 3 seconds

#### Phase 3 Testing (if implemented)

- [ ] Verify Redis is running: `docker-compose ps redis`
- [ ] Verify Celery worker is running: `docker-compose ps presgen-assess-worker`
- [ ] Check Celery worker logs: `docker-compose logs -f presgen-assess-worker`
- [ ] Start course generation
- [ ] Verify POST /courses returns immediately (< 1 second)
- [ ] Verify course created with status="queued"
- [ ] Verify Celery task picked up: check worker logs for "Starting course generation task"
- [ ] Poll /course-status
  - [ ] Verify each poll returns in < 1 second
  - [ ] Verify status updates: queued → pending_core_processing → pending_avatar → generating_video → completed
- [ ] Test worker failure handling:
  - [ ] Stop worker: `docker-compose stop presgen-assess-worker`
  - [ ] Start course generation
  - [ ] Verify status stays "queued"
  - [ ] Start worker: `docker-compose start presgen-assess-worker`
  - [ ] Verify job is picked up and processed
- [ ] Test Flower monitoring (if installed):
  - [ ] Access http://localhost:5555
  - [ ] Verify tasks visible
  - [ ] Verify task success/failure rates

#### Phase 4 Testing

- [ ] Access /metrics endpoint: `curl http://localhost:8000/metrics`
- [ ] Verify metrics present:
  - [ ] course_generation_total
  - [ ] course_generation_duration_seconds
  - [ ] presgen_core_timeout_total
- [ ] Start course generation
- [ ] Verify metrics increment
- [ ] Access Grafana dashboard (if configured)
- [ ] Verify graphs updating
- [ ] Test alerting:
  - [ ] Trigger timeout condition (mock Core to always timeout)
  - [ ] Verify alert fires
  - [ ] Verify alert notification received

---

## Deployment Plan

### Pre-Deployment Checklist

- [ ] All Phase 1 code changes reviewed
- [ ] Unit tests passing
- [ ] Integration tests passing
- [ ] Staging environment testing complete
- [ ] Database migrations prepared (if any)
- [ ] Documentation updated
- [ ] Rollback plan documented
- [ ] Team notified of deployment

### Deployment Steps

#### Phase 1 Deployment (Immediate Fixes)

**Step 1: Backup**

```bash
# Backup database
docker-compose exec postgres pg_dump -U presgen presgen_assess > backup_$(date +%Y%m%d_%H%M%S).sql

# Backup current code
git tag pre-phase1-deployment
git push origin pre-phase1-deployment
```

**Step 2: Update Code**

```bash
# Pull latest changes
git checkout main
git pull origin main

# Verify you're on correct commit
git log -1
```

**Step 3: Update Nginx Configuration**

```bash
# Backup current nginx config
docker-compose exec nginx cat /etc/nginx/nginx.conf > nginx.conf.backup

# Update nginx.conf with new course-status location block
# (Already done in code repo)

# Verify syntax
docker-compose exec nginx nginx -t
```

**Step 4: Deploy**

```bash
# Rebuild and restart services
docker-compose build presgen-assess nginx
docker-compose up -d presgen-assess nginx

# Watch logs for errors
docker-compose logs -f presgen-assess nginx
```

**Step 5: Verify**

```bash
# Check services are healthy
docker-compose ps

# Test status endpoint
curl -v -u demo:demo123 \
  'http://localhost/api/v1/workflows/test/skills/test/course-status'

# Should return 404 (not 500/502) if course doesn't exist
```

**Step 6: Monitor**

```bash
# Watch logs for errors
docker-compose logs -f presgen-assess | grep -E "ERROR|CRITICAL|500|502"

# Monitor nginx access logs
docker-compose logs -f nginx | grep -E "502|504"

# Check application logs
tail -f logs/assess/course_generation.log
```

---

#### Phase 2 Deployment (Backend Optimizations)

**Step 1: Update Environment Variables**

```bash
# Edit .env file
PRESGEN_CORE_TIMEOUT_SECONDS=900
PRESGEN_CORE_MAX_ATTEMPTS=2
PRESGEN_CORE_BACKOFF_SECONDS=3
```

**Step 2: Deploy Code Changes**

```bash
git pull origin main
docker-compose build presgen-assess
docker-compose up -d presgen-assess
```

**Step 3: Verify Configuration**

```bash
# Verify environment variables
docker-compose exec presgen-assess env | grep PRESGEN_CORE

# Test timeout behavior (should timeout faster now)
```

---

#### Phase 3 Deployment (Background Workers)

**Step 1: Add Redis**

```bash
# Add Redis to docker-compose.yml (already in plan)
docker-compose up -d redis

# Verify Redis is running
docker-compose exec redis redis-cli ping
# Should return: PONG
```

**Step 2: Deploy Worker Service**

```bash
# Build worker image (uses same Dockerfile as presgen-assess)
docker-compose build presgen-assess-worker

# Start worker
docker-compose up -d presgen-assess-worker

# Verify worker is processing tasks
docker-compose logs -f presgen-assess-worker
# Should see: "celery@... ready"
```

**Step 3: Deploy Updated API**

```bash
# Deploy presgen-assess with new async endpoints
docker-compose build presgen-assess
docker-compose up -d presgen-assess
```

**Step 4: Migrate Existing In-Progress Courses (if any)**

```python
# Migration script: migrate_to_async.py
from src.models.generated_course import GeneratedCourse
from src.tasks.course_generation import generate_course_async
from src.database import SessionLocal

db = SessionLocal()

# Find courses stuck in processing
stuck_courses = db.query(GeneratedCourse).filter(
    GeneratedCourse.status.in_(['pending_core_processing', 'pending_avatar'])
).all()

for course in stuck_courses:
    print(f"Re-queueing course {course.id}")

    # Reset to queued and submit to Celery
    course.status = 'queued'
    db.commit()

    generate_course_async.delay(
        workflow_id=course.workflow_id,
        skill_id=course.skill_id,
        course_id=course.id,
    )

db.close()
```

---

### Post-Deployment Verification

#### Phase 1 Verification

- [ ] Start 3 test course generations
- [ ] Verify no HTTP 502 errors in logs
- [ ] Verify no HTTP 504 errors in nginx logs
- [ ] If timeout occurs, verify proper failed response returned
- [ ] Verify frontend displays error message
- [ ] Verify polling stops after failure

#### Phase 2 Verification

- [ ] Verify timeouts occur faster (check logs for timestamps)
- [ ] Verify only 2 retry attempts occur
- [ ] Verify 3-second backoff between retries

#### Phase 3 Verification

- [ ] Verify course creations return immediately
- [ ] Verify Celery tasks are picked up by worker
- [ ] Verify status endpoint responds in < 1 second
- [ ] Verify successful completions update database correctly
- [ ] Check Redis queue depth: `docker-compose exec redis redis-cli llen celery`

---

## Rollback Procedures

### Phase 1 Rollback

If deployment causes issues, rollback:

```bash
# Step 1: Revert code
git revert HEAD
git push origin main

# Step 2: Rebuild
docker-compose build presgen-assess nginx
docker-compose up -d presgen-assess nginx

# Step 3: Restore nginx config
docker-compose exec nginx cp /etc/nginx/nginx.conf.backup /etc/nginx/nginx.conf
docker-compose exec nginx nginx -s reload

# Step 4: Verify
docker-compose logs -f presgen-assess nginx
```

### Phase 2 Rollback

```bash
# Revert environment variables
PRESGEN_CORE_TIMEOUT_SECONDS=600
PRESGEN_CORE_MAX_ATTEMPTS=3
PRESGEN_CORE_BACKOFF_SECONDS=1

# Restart service
docker-compose restart presgen-assess
```

### Phase 3 Rollback

```bash
# Step 1: Stop worker
docker-compose stop presgen-assess-worker

# Step 2: Revert presgen-assess code
git revert <commit-hash>
docker-compose build presgen-assess
docker-compose up -d presgen-assess

# Step 3: Migrate in-flight jobs back to synchronous processing
# (Manual intervention may be required for courses stuck in "queued" state)

# Step 4: Optionally remove Redis if not needed
docker-compose stop redis
```

---

## Success Metrics

### Key Performance Indicators (KPIs)

| Metric | Current | Target (Phase 1) | Target (Phase 3) |
|--------|---------|------------------|------------------|
| Nginx 504 error rate | ~50% | < 5% | 0% |
| HTTP 502 error rate | ~30% | 0% | 0% |
| HTTP 400 error rate | ~20% | 0% | 0% |
| Course completion rate | ~50% | ~50% (unchanged) | > 90% |
| Time to failure detection | 20-30 min | 18-20 min | < 15 min |
| Status endpoint response time | 300s+ | 300s+ | < 1s |
| Frontend error display | Broken | Clear message | Clear message |
| User satisfaction | Low | Medium | High |

### Success Criteria

**Phase 1 Success:**
- ✅ No HTTP 502/504 errors when PresGen-Core times out
- ✅ Proper failed response returned with user-friendly error message
- ✅ Frontend displays error clearly and stops polling
- ✅ No HTTP 400 errors when polling failed courses

**Phase 2 Success:**
- ✅ Timeout configuration adjustable via environment variables
- ✅ Retry attempts reduced from 3 to 2
- ✅ Faster failure detection (18-20 min vs 30+ min)

**Phase 3 Success:**
- ✅ Status endpoint responds in < 1 second
- ✅ No nginx timeouts regardless of PresGen-Core duration
- ✅ Background workers processing jobs successfully
- ✅ Course completion rate > 90%
- ✅ Horizontal scalability (can add more workers)

---

## Appendix

### A. Related Files

#### Backend Files

- `presgen-assess/src/service/api/v1/endpoints/workflows.py` - Course status endpoint
- `presgen-assess/src/integrations/presgen_core/client.py` - PresGen-Core client
- `presgen-assess/src/integrations/presgen_avatar/client.py` - PresGen-Avatar client
- `presgen-assess/src/models/generated_course.py` - Course database model
- `presgen-assess/src/common/config.py` - Configuration settings
- `presgen-assess/src/service/background_jobs.py` - Background job queue

#### Infrastructure Files

- `nginx/nginx.conf` - Nginx reverse proxy configuration
- `docker-compose.yml` - Service orchestration
- `.env` - Environment variables

#### Frontend Files (to investigate)

- Frontend polling logic
- Error display components
- Course status state management

---

### B. Log Examples

#### Successful Flow

```
2025-11-09 14:00:00 | INFO | COURSE_CREATED | course_id=20251109_140000 | status=queued
2025-11-09 14:00:03 | INFO | COURSE_STATUS_POLL | status=pending_core_processing
2025-11-09 14:00:03 | INFO | CORE_ASYNC_START | presentation_url=https://slides.google.com/...
2025-11-09 14:08:45 | INFO | CORE_ASYNC_COMPLETED | job_id=core-123 | download_url=https://...
2025-11-09 14:08:45 | INFO | AVATAR_SUBMISSION_START
2025-11-09 14:08:47 | INFO | AVATAR_JOB_QUEUED | job_id=avatar-456
2025-11-09 14:15:23 | INFO | AVATAR_JOB_COMPLETED | output_path=/tmp/video.mp4
2025-11-09 14:15:30 | INFO | DRIVE_UPLOAD_COMPLETED | drive_url=https://drive.google.com/...
2025-11-09 14:15:30 | INFO | COURSE_COMPLETED | total_duration=930s
```

#### Timeout Flow (Current - Broken)

```
2025-11-09 10:23:25 | INFO | CORE_ASYNC_START
2025-11-09 10:33:25 | ERROR | PresGen-Core TIMEOUT after 600s
2025-11-09 10:33:28 | WARNING | Retrying PresGen-Core (attempt 1/3) in 1s
2025-11-09 10:43:28 | ERROR | PresGen-Core TIMEOUT after 600s
2025-11-09 10:43:31 | WARNING | Retrying PresGen-Core (attempt 2/3) in 2s
2025-11-09 10:53:33 | ERROR | PresGen-Core TIMEOUT after 600s
2025-11-09 10:53:33 | ERROR | PresGen-Core generation failed after 3 attempts
[nginx] 2025-11-09 10:28:25 | ERROR | upstream timed out (110: Connection timed out) reading response header
[frontend] ApiError: Unexpected server response shape
```

#### Timeout Flow (After Phase 1 - Fixed)

```
2025-11-09 14:00:00 | INFO | CORE_ASYNC_START
2025-11-09 14:15:00 | ERROR | PresGen-Core TIMEOUT after 900s
2025-11-09 14:15:03 | WARNING | Retrying PresGen-Core (attempt 1/2) in 3s
2025-11-09 14:30:06 | ERROR | PresGen-Core TIMEOUT after 900s
2025-11-09 14:30:06 | ERROR | PresGen-Core generation failed after 2 attempts | error_type=PresGenCoreTimeoutError
2025-11-09 14:30:06 | INFO | Course status updated | status=failed | error=PresGen-Core request timed out
2025-11-09 14:30:06 | INFO | Returning failed response (HTTP 200)
[frontend] Course generation failed: PresGen-Core request timed out. Please try again.
```

---

### C. Environment Variables Reference

```bash
# PresGen-Core Configuration
PRESGEN_CORE_URL=http://presgen-core:8080
PRESGEN_CORE_TIMEOUT_SECONDS=900           # Timeout for Core requests (seconds)
PRESGEN_CORE_MAX_ATTEMPTS=2                # Maximum retry attempts
PRESGEN_CORE_BACKOFF_SECONDS=3             # Backoff between retries (seconds)
PRESGEN_CORE_CIRCUIT_FAILURE_THRESHOLD=5   # Failures before circuit opens
PRESGEN_CORE_CIRCUIT_RECOVERY_SECONDS=120  # Seconds before circuit recovery

# PresGen-Avatar Configuration
PRESGEN_AVATAR_URL=http://presgen-avatar:8081
PRESGEN_AVATAR_TIMEOUT_SECONDS=1800        # Timeout for Avatar requests (30 min)

# Celery Configuration (Phase 3)
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/0

# Database
DATABASE_URL=postgresql://user:pass@postgres:5432/presgen_assess

# Logging
LOG_LEVEL=INFO
STRUCTURED_LOGGING=true
```

---

### D. API Response Schemas

#### CourseGenerationResponse (Updated)

```json
{
  "course_id": "20251109_140000",
  "workflow_id": "4b152322-48ae-4ff5-a49f-757950b3686a",
  "skill_id": "data_engineering",
  "skill_name": "Data Engineering",
  "course_title": "Introduction to Data Engineering",
  "presentation_url": "https://docs.google.com/presentation/d/...",
  "video_url": "https://drive.google.com/file/d/.../view",
  "drive_download_url": "https://drive.google.com/uc?export=download&id=...",
  "presgen_core_job_id": "core-abc123",
  "presgen_core_download_url": "https://example.com/video.mp4",
  "presgen_avatar_job_id": "avatar-def456",
  "local_video_path": "/app/output/20251109_140000.mp4",
  "status": "completed",
  "progress": 100,
  "error_message": null,
  "created_at": "2025-11-09T14:00:00Z",
  "updated_at": "2025-11-09T14:15:30Z",
  "completed_at": "2025-11-09T14:15:30Z"
}
```

#### CourseGenerationResponse (Failed)

```json
{
  "course_id": "20251109_140000",
  "workflow_id": "4b152322-48ae-4ff5-a49f-757950b3686a",
  "skill_id": "data_engineering",
  "skill_name": "Data Engineering",
  "course_title": "Introduction to Data Engineering",
  "presentation_url": "https://docs.google.com/presentation/d/...",
  "video_url": null,
  "drive_download_url": null,
  "presgen_core_job_id": null,
  "presgen_core_download_url": null,
  "presgen_avatar_job_id": null,
  "local_video_path": null,
  "status": "failed",
  "progress": 25,
  "error_message": "PresGen-Core request timed out. The presentation generation took longer than expected. Please try again or contact support if this persists.",
  "created_at": "2025-11-09T14:00:00Z",
  "updated_at": "2025-11-09T14:30:06Z",
  "completed_at": null
}
```

---

## Next Steps

1. **Review this plan** with team
2. **Get approval** for Phase 1 deployment
3. **Schedule deployment window** (recommend off-hours)
4. **Execute Phase 1 fixes** (1-2 hours)
5. **Monitor for 24-48 hours**
6. **Gather metrics** on improvement
7. **Plan Phase 2 deployment** if Phase 1 successful
8. **Consider Phase 3** for long-term solution

---

**Document Owner:** Engineering Team
**Last Updated:** 2025-11-09
**Next Review:** After Phase 1 deployment
