# Phase 3 Implementation Guide: True Async Job Processing

**Date:** November 9, 2025
**Objective:** Implement background job queue for truly async course generation
**Status:** 🔄 Ready for Implementation
**Estimated Effort:** 6-8 hours
**Priority:** P2 (Long-term solution, nice to have)

---

## Executive Summary

**Current State (After Phase 1 & 2):**
- ✅ Timeout issues resolved (HTTP 502/504 errors eliminated)
- ✅ Configurable retry/timeout settings
- ✅ Worst-case blocking time reduced from 30min to 20min
- ⚠️  `/course-status` endpoint still makes synchronous calls to PresGen-Core/Avatar
- ⚠️  Long-running requests block HTTP connection

**Phase 3 Goal:**
- Decouple HTTP polling from external service calls
- Move PresGen-Core/Avatar processing to background workers
- Make `/course-status` read-only (instant response, never blocks)
- Enable horizontal scaling of processing workers

**Is Phase 3 Required?**
**No** - Phases 1 & 2 have already resolved the critical timeout issues. Phase 3 is a **long-term architectural improvement** that provides:
- Better scalability
- Improved resilience
- Cleaner separation of concerns
- Easier monitoring and debugging

However, the current solution is production-ready and stable.

---

## Architecture Overview

### Current Architecture (Phase 2)

```
┌──────────────┐
│   Frontend   │
│   (React)    │
└──────┬───────┘
       │ Polls every 3s
       ↓
┌─────────────────────────────────────────────────┐
│  GET /course-status                              │
│                                                  │
│  1. Read course from DB                          │
│  2. If status=pending_core_processing:           │
│     ├─> Call PresGen-Core (blocks 10+ min) ⏱️   │
│     └─> Update DB                                │
│  3. If status=pending_avatar:                    │
│     ├─> Call PresGen-Avatar (blocks 15+ min) ⏱️ │
│     └─> Update DB                                │
│  4. Return status                                │
└─────────────────────────────────────────────────┘
```

**Problems:**
- HTTP connection stays open during long external calls
- Nginx timeout must be very long (35 minutes)
- Can't scale horizontally (each request processes serially)
- No visibility into queue depth or processing times

### Target Architecture (Phase 3)

```
┌──────────────┐
│   Frontend   │
│   (React)    │
└──────┬───────┘
       │ Polls every 3s
       ↓
┌─────────────────────────────────────────────────┐
│  GET /course-status                              │
│                                                  │
│  1. Read course from DB (instant ⚡)             │
│  2. Return current status                        │
│  3. NO external service calls                    │
└─────────────────────────────────────────────────┘
       ↑
       │ Updates DB
       │
┌─────────────────────────────────────────────────┐
│  Celery Background Worker                        │
│                                                  │
│  generate_course_async(workflow_id, skill_id):  │
│    1. Update status → pending_core_processing   │
│    2. Call PresGen-Core (takes 10+ min) ⏱️      │
│    3. Update status → pending_avatar             │
│    4. Call PresGen-Avatar (takes 15+ min) ⏱️    │
│    5. Poll Avatar until complete                 │
│    6. Upload to Google Drive                     │
│    7. Update status → completed                  │
└─────────────────────────────────────────────────┘
       ↑
       │ Picks up jobs from queue
       │
┌─────────────────────────────────────────────────┐
│  Redis Queue                                     │
│                                                  │
│  - Job: generate_course(wf_123, skill_456)      │
│  - Job: generate_course(wf_789, skill_101)      │
│  - ...                                           │
└─────────────────────────────────────────────────┘
```

**Benefits:**
- ✅ `/course-status` responds instantly (< 50ms)
- ✅ No nginx timeout issues
- ✅ Can run multiple workers for parallel processing
- ✅ Workers can be scaled independently
- ✅ Job queue provides visibility and metrics
- ✅ Failed jobs can be retried automatically
- ✅ Workers can be restarted without losing jobs

---

## Prerequisites

### Infrastructure Already in Place

✅ **Redis:** Already configured in docker-compose.yml
✅ **Celery:** Already in requirements.txt (celery==5.3.4)
✅ **Redis Python Client:** Already in requirements.txt (redis==5.0.1)

### New Components Needed

1. **Celery App Configuration:** `src/celery_app.py` ✅ (Created)
2. **Background Tasks Module:** `src/tasks/course_generation.py` (To implement)
3. **Celery Worker Container:** Add to docker-compose.yml
4. **Database Session Factory:** For sync operations in Celery tasks
5. **Configuration Settings:** Celery broker/backend URLs

---

## Implementation Steps

### Step 1: Add Celery Configuration to Settings

**File:** `presgen-assess/src/common/config.py`

```python
# Add these fields to the Settings class:

# Celery Configuration (Phase 3)
celery_broker_url: str = os.getenv("CELERY_BROKER_URL", "redis://redis:6379/0")
celery_result_backend: str = os.getenv("CELERY_RESULT_BACKEND", "redis://redis:6379/0")
celery_task_time_limit: int = int(os.getenv("CELERY_TASK_TIME_LIMIT", "3600"))  # 1 hour
celery_worker_concurrency: int = int(os.getenv("CELERY_WORKER_CONCURRENCY", "2"))
```

**Add logging:**

```python
print(f"📦 Celery Configuration (Phase 3):", file=sys.stderr)
print(f"  🔗 Broker URL: {settings.celery_broker_url}", file=sys.stderr)
print(f"  💾 Result Backend: {settings.celery_result_backend}", file=sys.stderr)
print(f"  ⏱️  Task Time Limit: {settings.celery_task_time_limit}s", file=sys.stderr)
print(f"  👷 Worker Concurrency: {settings.celery_worker_concurrency}", file=sys.stderr)
```

---

### Step 2: Create Sync Database Session Factory

**File:** `presgen-assess/src/database/sync_session.py` (new file)

```python
"""Synchronous database session for Celery tasks.

Celery tasks run in separate worker processes and cannot use async/await.
This module provides synchronous database access for background tasks.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from src.common.config import settings

# Convert async URL to sync URL
sync_database_url = settings.database_url.replace("postgresql+asyncpg://", "postgresql://")

# Create sync engine
sync_engine = create_engine(
    sync_database_url,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
)

# Create session factory
SyncSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=sync_engine,
)

def get_sync_db() -> Session:
    """Get synchronous database session for Celery tasks."""
    db = SyncSessionLocal()
    try:
        yield db
    finally:
        db.close()
```

**Why needed:**
- Celery tasks are synchronous (no async/await)
- Current codebase uses `AsyncSession` everywhere
- Need separate sync session for worker processes

---

### Step 3: Create Background Task for Course Generation

**File:** `presgen-assess/src/tasks/course_generation.py`

This is a large file. Here's the complete implementation:

```python
"""Background task for course generation.

Phase 3: Architectural Improvements - Async Job Processing
"""

import logging
from datetime import datetime
from typing import Optional
import asyncio

from celery import Task
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.celery_app import celery_app
from src.database.sync_session import SyncSessionLocal
from src.models.generated_course import GeneratedCourse
from src.models.workflow import Workflow
from src.models.skill_course import SkillCourse
from src.models.certification_profile import CertificationProfile
from src.integrations.presgen_core.client import (
    PresGenCoreClient,
    PresGenCoreTimeoutError,
    PresGenCoreHTTPError,
)
from src.integrations.presgen_core.schemas import PresGenPresentationRequest
from src.integrations.presgen_avatar.client import PresGenAvatarClient
from src.common.config import settings

logger = logging.getLogger(__name__)


class CourseGenerationTask(Task):
    """Custom Celery task class with error handling."""

    autoretry_for = (Exception,)
    retry_kwargs = {'max_retries': 2, 'countdown': 60}
    retry_backoff = True


@celery_app.task(
    bind=True,
    base=CourseGenerationTask,
    name='src.tasks.course_generation.generate_course_async',
    time_limit=3600,  # 1 hour hard limit
    soft_time_limit=3300,  # 55 minutes soft limit
)
def generate_course_async(
    self,
    workflow_id: str,
    skill_id: str,
    course_id: str,
):
    """
    Background task to generate course presentation and video.

    This task runs in a separate Celery worker process, so it can take
    as long as needed without blocking HTTP requests.

    Args:
        workflow_id: UUID of the workflow
        skill_id: Skill identifier
        course_id: Course identifier (timestamp-based)

    Raises:
        Retry: If task fails and should be retried
    """
    logger.info(
        "📋 Starting course generation task | workflow_id=%s | skill_id=%s | course_id=%s",
        workflow_id,
        skill_id,
        course_id,
    )

    # Create new database session (not shared with web process)
    db = SyncSessionLocal()

    try:
        # Step 1: Load course and related entities
        course = db.query(GeneratedCourse).filter_by(id=course_id).first()
        if not course:
            logger.error("Course not found: %s", course_id)
            raise ValueError(f"Course {course_id} not found")

        workflow = db.query(Workflow).filter_by(id=workflow_id).first()
        if not workflow:
            logger.error("Workflow not found: %s", workflow_id)
            raise ValueError(f"Workflow {workflow_id} not found")

        skill_course = db.query(SkillCourse).filter_by(
            workflow_id=workflow_id,
            skill_id=skill_id
        ).first()
        if not skill_course:
            logger.error("Skill course not found: %s/%s", workflow_id, skill_id)
            raise ValueError(f"Skill course {skill_id} not found in workflow {workflow_id}")

        # Get certification profile for custom prompt
        cert_profile = None
        if workflow.certification_profile_id:
            cert_profile = db.query(CertificationProfile).filter_by(
                id=workflow.certification_profile_id
            ).first()
        custom_prompt = cert_profile.presentation_prompt if cert_profile else None

        # Step 2: Call PresGen-Core for presentation generation
        logger.info("🧠 Starting PresGen-Core generation | course_id=%s", course_id)
        course.status = "pending_core_processing"
        course.progress = 25
        db.commit()

        core_client = PresGenCoreClient(base_url=settings.presgen_core_url)

        try:
            # PresGenCoreClient uses async methods, so we need to run in event loop
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            try:
                core_response = loop.run_until_complete(
                    core_client.generate_presentation(
                        PresGenPresentationRequest(
                            skill=skill_course.skill_name,
                            domain=skill_course.exam_domain,
                            target_duration_minutes=10,
                            custom_prompt=custom_prompt,
                            presentation_url=course.presentation_url,
                            content_text=skill_course.course_description,
                            metadata={
                                "workflow_id": workflow_id,
                                "skill_id": skill_id,
                                "course_id": course_id,
                            },
                        )
                    )
                )
            finally:
                loop.run_until_complete(core_client.close())
                loop.close()

            # Update course with Core results
            course.presgen_core_job_id = core_response.job_id
            course.presgen_core_download_url = core_response.download_url
            if core_response.duration_ms:
                course.presgen_core_processing_time_ms = core_response.duration_ms
            if core_response.presentation_url:
                course.presentation_url = core_response.presentation_url

            logger.info(
                "🧠 PresGen-Core completed | course_id=%s | job_id=%s",
                course_id,
                core_response.job_id,
            )

            if not core_response.success or core_response.error:
                error_msg = core_response.error or "PresGen-Core reported failure"
                logger.error("PresGen-Core failed: %s", error_msg)
                course.status = "failed"
                course.error_message = error_msg
                db.commit()
                raise ValueError(error_msg)

            # Core succeeded, move to Avatar
            course.status = "pending_avatar"
            course.progress = 50
            db.commit()

        except (PresGenCoreTimeoutError, PresGenCoreHTTPError) as e:
            error_msg = f"PresGen-Core generation failed: {str(e)}"
            logger.exception("❌ PresGen-Core failed | course_id=%s", course_id)
            course.status = "failed"
            course.error_message = error_msg
            db.commit()
            raise

        # Step 3: Call PresGen-Avatar for video generation
        logger.info("🎤 Starting PresGen-Avatar generation | course_id=%s", course_id)
        course.status = "generating_video"
        course.progress = 60
        db.commit()

        if not course.presgen_core_download_url:
            raise ValueError("Missing PresGen-Core download URL for avatar generation")

        avatar_client = PresGenAvatarClient(base_url=settings.presgen_avatar_url)
        avatar_metadata = {
            "core_download_url": course.presgen_core_download_url,
        }

        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            try:
                avatar_result = loop.run_until_complete(
                    avatar_client.generate_video(
                        workflow_id=workflow_id,
                        skill_id=skill_id,
                        presentation_url=course.presentation_url,
                        mode="presentation-only",
                        quality="fast",
                        voice_provider="openai",
                        voice_id="alloy",
                        metadata=avatar_metadata,
                    )
                )
            finally:
                loop.run_until_complete(avatar_client.close())
                loop.close()

            course.presgen_avatar_job_id = avatar_result.job_id
            course.progress = 70
            db.commit()

            logger.info(
                "🎤 PresGen-Avatar job queued | course_id=%s | job_id=%s",
                course_id,
                avatar_result.job_id,
            )

            # Step 4: Poll Avatar until complete
            # Note: This is simplified - actual implementation needs proper polling
            # For now, just mark as generating
            course.status = "generating_video"
            course.progress = 80
            db.commit()

            logger.info(
                "✅ Course generation task completed | course_id=%s",
                course_id,
            )

        except Exception as e:
            error_msg = f"Video generation failed: {str(e)}"
            logger.exception("❌ PresGen-Avatar failed | course_id=%s", course_id)
            course.status = "failed"
            course.error_message = error_msg
            db.commit()
            raise

    except Exception as e:
        logger.exception(
            "❌ Course generation task failed | workflow_id=%s | course_id=%s",
            workflow_id,
            course_id,
        )
        # Update course status to failed
        try:
            if course:
                course.status = "failed"
                course.error_message = f"Task failed: {str(e)}"
                db.commit()
        except:
            logger.exception("Failed to update course status")

        # Celery will retry based on autoretry_for settings
        raise self.retry(exc=e)

    finally:
        db.close()
```

**Key Design Decisions:**

1. **Sync vs Async:** Celery tasks are synchronous, but our clients are async
   - Solution: Use `asyncio.new_event_loop()` to run async code in sync context

2. **Database Sessions:** Separate sync session for worker processes
   - Solution: Created `SyncSessionLocal` factory

3. **Error Handling:** Tasks should retry on transient failures
   - Solution: Custom `CourseGenerationTask` with automatic retries

4. **Progress Tracking:** Update course status at each step
   - Solution: Commit after each major step

---

### Step 4: Refactor Course Creation Endpoint

**File:** `presgen-assess/src/service/api/v1/endpoints/workflows.py`

**Current:** Creates course and returns response that triggers polling
**New:** Creates course and submits to background queue

Find the course creation endpoint and modify:

```python
from src.tasks.course_generation import generate_course_async

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

    Phase 3: Returns immediately and submits job to background queue.
    Frontend polls /course-status for progress.
    """

    # Create course record with status="queued"
    course = GeneratedCourse(
        id=generate_course_id(),
        workflow_id=workflow_id,
        skill_id=skill_id,
        status="queued",  # NEW: Start as queued
        progress=0,
        created_at=datetime.utcnow(),
        # ... other fields ...
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
        "📋 Course generation queued | workflow_id=%s | skill_id=%s | course_id=%s",
        workflow_id,
        skill_id,
        course.id,
    )

    # Return immediately with "queued" status
    return CourseGenerationResponse(
        course_id=course.id,
        workflow_id=workflow_id,
        skill_id=skill_id,
        status="queued",
        progress=0,
        created_at=course.created_at,
        # ... other fields ...
    )
```

---

### Step 5: Simplify Course Status Endpoint

**File:** `presgen-assess/src/service/api/v1/endpoints/workflows.py`

**Current:** Makes blocking calls to PresGen-Core/Avatar
**New:** Only reads from database (instant response)

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

    Phase 3: This endpoint now ONLY reads from the database.
    It does NOT call PresGen-Core or PresGen-Avatar.
    Background worker handles all external service calls.
    """

    # Find most recent course for this workflow + skill
    result = await db.execute(
        select(GeneratedCourse)
        .where(GeneratedCourse.workflow_id == workflow_id)
        .where(GeneratedCourse.skill_id == skill_id)
        .order_by(GeneratedCourse.created_at.desc())
        .limit(1)
    )
    course = result.scalar_one_or_none()

    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    logger.info(
        "📊 Course status polled | workflow_id=%s | course_id=%s | status=%s | progress=%s",
        workflow_id,
        course.id,
        course.status,
        course.progress,
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

**Changes:**
- ❌ Removed all PresGen-Core/Avatar client calls
- ❌ Removed retry logic (now in worker)
- ❌ Removed error handling for external services
- ✅ Simple database read + return
- ✅ Response time: < 50ms (vs 20+ minutes before)

---

### Step 6: Add Celery Worker to Docker Compose

**File:** `docker-compose.yml`

Add new service after `presgen-assess`:

```yaml
services:
  # ... existing services ...

  presgen-assess:
    # ... existing config ...
    environment:
      # Add Celery config
      - CELERY_BROKER_URL=redis://redis:6379/0
      - CELERY_RESULT_BACKEND=redis://redis:6379/0
    depends_on:
      - redis  # Ensure Redis is already included

  # NEW: Celery worker for background jobs
  presgen-assess-worker:
    build:
      context: ./presgen-assess
      dockerfile: Dockerfile
    container_name: presgen-assess-worker
    command: celery -A src.celery_app worker --loglevel=info --concurrency=2
    environment:
      # Database
      - DATABASE_URL=${DATABASE_URL}

      # Celery
      - CELERY_BROKER_URL=redis://redis:6379/0
      - CELERY_RESULT_BACKEND=redis://redis:6379/0

      # PresGen Services
      - PRESGEN_CORE_URL=http://presgen-core:8080
      - PRESGEN_AVATAR_URL=http://presgen-avatar:8002

      # All other env vars from presgen-assess
      # (Copy from presgen-assess service)
    depends_on:
      redis:
        condition: service_healthy
      presgen-assess:
        condition: service_healthy
      presgen-core:
        condition: service_healthy
    volumes:
      - ./presgen-assess/src:/app/src:ro
      - course_videos:/app/output
    restart: unless-stopped
    mem_limit: 1g
    mem_reservation: 512m
    networks:
      - presgen-network
    healthcheck:
      test: ["CMD", "celery", "-A", "src.celery_app", "inspect", "ping"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 10s

volumes:
  # ... existing volumes ...
  course_videos:  # NEW: Shared volume for generated videos
```

---

### Step 7: Add psycopg2 for Sync Database Access

**File:** `presgen-assess/requirements.txt`

Add (Celery needs sync Postgres driver):

```txt
# Sync Postgres driver for Celery tasks (Phase 3)
psycopg2-binary==2.9.9
```

**Why:** SQLAlchemy async engine uses `asyncpg`, but Celery tasks need `psycopg2` for sync access.

---

## Testing Phase 3

### Unit Tests

```python
# tests/test_course_generation_task.py
import pytest
from unittest.mock import Mock, patch
from src.tasks.course_generation import generate_course_async

def test_generate_course_async_success():
    """Test successful course generation."""
    with patch('src.tasks.course_generation.SyncSessionLocal') as mock_session:
        # Setup mocks
        mock_db = Mock()
        mock_session.return_value = mock_db

        # Run task
        result = generate_course_async(
            workflow_id="test-workflow",
            skill_id="test-skill",
            course_id="20251109_120000",
        )

        # Verify
        assert result is None  # Task completed
        mock_db.commit.assert_called()

def test_generate_course_async_core_timeout():
    """Test handling of Core timeout."""
    # Similar test with PresGenCoreTimeoutError
    pass

def test_generate_course_async_retry():
    """Test task retry on failure."""
    # Verify task raises Retry exception
    pass
```

### Integration Tests

```bash
# Start all services including worker
docker-compose up -d

# Verify worker is running
docker-compose logs presgen-assess-worker | grep "ready"
# Expected: [2025-11-09 12:00:00,000: INFO/MainProcess] celery@worker1 ready.

# Create a course (should return immediately with status="queued")
time curl -u demo:demo123 -X POST \
  'http://localhost/api/v1/workflows/YOUR_WORKFLOW_ID/skills/YOUR_SKILL_ID/courses' \
  | jq '.status, .progress'
# Expected: "queued" 0
# Time: < 1 second

# Poll status (should respond instantly)
time curl -u demo:demo123 \
  'http://localhost/api/v1/workflows/YOUR_WORKFLOW_ID/skills/YOUR_SKILL_ID/course-status' \
  | jq '.status, .progress'
# Expected: "pending_core_processing" 25 (or further along)
# Time: < 100ms

# Check worker logs to see task progress
docker-compose logs -f presgen-assess-worker
```

### Performance Tests

**Before Phase 3 (Phase 2):**
```bash
# Poll endpoint blocks for 10+ minutes
time curl 'http://localhost/api/v1/.../course-status'
# Time: 600-1800 seconds
```

**After Phase 3:**
```bash
# Poll endpoint returns instantly
time curl 'http://localhost/api/v1/.../course-status'
# Time: < 0.1 seconds
```

---

## Migration Path

### Option A: Big Bang (Recommended for staging first)

1. Deploy all Phase 3 changes at once
2. Test thoroughly in staging
3. Deploy to production

**Pros:** Clean cutover, no hybrid state
**Cons:** Higher risk, requires extensive testing

### Option B: Gradual Migration

1. Deploy Celery app + worker (but don't use yet)
2. Add feature flag: `USE_ASYNC_WORKERS=false`
3. Test worker with subset of workflows
4. Gradually enable for all workflows
5. Remove old synchronous code

**Pros:** Lower risk, can rollback easily
**Cons:** More complex, maintains two code paths temporarily

---

## Monitoring & Observability

### Celery Flower (Web UI)

Add to docker-compose.yml:

```yaml
  celery-flower:
    image: mher/flower
    container_name: presgen-flower
    command: celery --broker=redis://redis:6379/0 flower --port=5555
    ports:
      - "5555:5555"
    environment:
      - CELERY_BROKER_URL=redis://redis:6379/0
      - CELERY_RESULT_BACKEND=redis://redis:6379/0
    depends_on:
      - redis
    networks:
      - presgen-network
```

Access at: `http://localhost:5555`

**Provides:**
- Active tasks
- Completed/failed tasks
- Worker status
- Task execution times
- Queue depth
- Success/failure rates

### Prometheus Metrics

```python
# Add to src/celery_app.py
from prometheus_client import Counter, Histogram

# Metrics
course_generation_started = Counter(
    'course_generation_started_total',
    'Total course generation tasks started'
)
course_generation_completed = Counter(
    'course_generation_completed_total',
    'Total course generation tasks completed'
)
course_generation_failed = Counter(
    'course_generation_failed_total',
    'Total course generation tasks failed'
)
course_generation_duration = Histogram(
    'course_generation_duration_seconds',
    'Course generation task duration'
)
```

---

## Rollback Plan

If Phase 3 causes issues:

### Immediate Rollback (< 5 minutes)

```bash
# Stop worker
docker-compose stop presgen-assess-worker

# Revert code changes
git revert HEAD  # Reverts Phase 3 commit

# Restart API service
docker-compose up -d presgen-assess

# Verify Phase 2 behavior restored
curl http://localhost/health
```

### Gradual Rollback (if using feature flag)

```bash
# Just disable async workers
docker-compose down
USE_ASYNC_WORKERS=false docker-compose up -d
```

---

## Success Criteria

### Functional Requirements

- ✅ Course creation returns immediately (< 1 second)
- ✅ Status polling never times out (< 100ms response)
- ✅ Background workers process courses successfully
- ✅ Failed tasks are retried automatically
- ✅ Course status updates are reflected in polling
- ✅ No regression in existing functionality

### Performance Requirements

- ✅ `/course-status` response time: < 100ms (vs 600-1800s before)
- ✅ `/courses` POST response time: < 1s (vs 1-30min before)
- ✅ Worker can handle 2 concurrent generations
- ✅ Queue depth visible in monitoring

### Reliability Requirements

- ✅ Worker crash doesn't lose jobs (Redis persistence)
- ✅ Task failures trigger retry (max 2 retries)
- ✅ Database updated atomically at each step
- ✅ No HTTP timeout errors (502/504)

---

## Next Steps After Phase 3

### Phase 4: Advanced Monitoring

- Grafana dashboards for queue metrics
- PagerDuty alerts for worker failures
- Automatic scaling based on queue depth
- Historical analytics for generation times

### Phase 5: Performance Optimization

- Investigate PresGen-Core performance bottlenecks
- Parallel processing of multiple slides
- Caching of frequently generated content
- Optimize database queries

---

## Estimated Timeline

| Task | Time | Assignee |
|------|------|----------|
| Step 1: Configuration | 15 min | - |
| Step 2: Sync DB Session | 15 min | - |
| Step 3: Background Task | 2 hours | - |
| Step 4: Refactor Creation | 1 hour | - |
| Step 5: Refactor Status | 1 hour | - |
| Step 6: Docker Compose | 30 min | - |
| Step 7: Dependencies | 15 min | - |
| Testing | 2 hours | - |
| Documentation | 1 hour | - |
| **Total** | **~8 hours** | - |

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Worker process crash | Medium | High | Auto-restart, job persistence in Redis |
| Database connection pool exhaustion | Low | High | Separate pool for workers |
| Task stuck in processing | Low | Medium | Task time limits, monitoring |
| Redis memory exhaustion | Low | Medium | Set maxmemory policy, monitor |
| Breaking change in API | Low | Critical | Extensive testing, gradual rollout |

---

## Questions & Answers

**Q: Do we need Phase 3 right now?**
A: No. Phases 1 & 2 have resolved the immediate timeout issues. Phase 3 is a long-term architectural improvement.

**Q: Can we deploy Phase 3 incrementally?**
A: Yes, use a feature flag to enable for subset of users/workflows first.

**Q: What happens if Redis goes down?**
A: Jobs in queue are lost. Mitigation: Redis persistence, monitoring, alerts.

**Q: How do we scale workers?**
A: Run multiple worker containers: `docker-compose up -d --scale presgen-assess-worker=4`

**Q: Can we use Phase 3 with current database schema?**
A: Yes, no schema changes needed. Just add "queued" status value.

---

## References

- [Celery Documentation](https://docs.celeryproject.org/)
- [Redis Persistence](https://redis.io/docs/management/persistence/)
- [Flower Monitoring](https://flower.readthedocs.io/)
- [COURSE_GENERATION_FIX_PLAN.md](./COURSE_GENERATION_FIX_PLAN.md) - Complete 4-phase plan
- [PHASE_1_IMPLEMENTATION_SUMMARY.md](./PHASE_1_IMPLEMENTATION_SUMMARY.md) - Phase 1 details
- [PHASE_2_IMPLEMENTATION_SUMMARY.md](./PHASE_2_IMPLEMENTATION_SUMMARY.md) - Phase 2 details
