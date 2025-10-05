# Sprint 4: Individual Skill Course Generation - TDD Manual Testing Guide

**Created**: 2025-10-05
**Sprint**: Sprint 4 - PresGen-Avatar Integration for Per-Skill Course Generation
**Status**: Implementation & Testing

## 📋 Table of Contents
- [Overview](#overview)
- [Prerequisites](#prerequisites)
- [Test Environment Setup](#test-environment-setup)
- [Phase 1: Database Schema & Migration](#phase-1-database-schema--migration)
- [Phase 2: PresGen-Avatar Client Setup](#phase-2-presgen-avatar-client-setup)
- [Phase 3: Course Generation API Endpoints](#phase-3-course-generation-api-endpoints)
- [Phase 4: Frontend Integration](#phase-4-frontend-integration)
- [Phase 5: End-to-End Workflow Testing](#phase-5-end-to-end-workflow-testing)

---

## Overview

### Sprint 4 Objectives
This sprint implements **individual skill course generation** with PresGen-Avatar integration:

1. **User clicks "Generate Course"** on a single skill in Recommended Courses tab
2. **Backend generates course outline** from individual skill gap
3. **PresGen-Core creates presentation** using certification profile's custom prompt
4. **PresGen-Avatar narrates video** in presentation-only mode with OpenAI voice
5. **Frontend displays video** with embedded player

### Architecture Flow
```
User Click → PresGen-Assess API → PresGen-Core (presentation) → PresGen-Avatar (video) → Display
                ↓
         Course Generation Log
```

### Key Features
- ✅ Per-skill course generation (not batch)
- ✅ Custom prompt override from certification profile
- ✅ Presentation-only mode (fast quality)
- ✅ OpenAI voice avatar
- ✅ Progress tracking (0-100%)
- ✅ Enhanced logging to `course_generation.log`

---

## Prerequisites

### 1. Required Services Running
```bash
# PresGen-Assess (port 8000)
cd /Users/yitzchak/Documents/learn/presentation_project/sales-agent-labs/presgen-assess
./venv/bin/uvicorn src.service.app:app --reload --port 8000

# PresGen-Core (port 8080)
cd /Users/yitzchak/Documents/learn/presentation_project/sales-agent-labs
./venv/bin/uvicorn src.service.http:app --reload --port 8080

# PresGen-Avatar (port 8002) - TO BE CONFIRMED
# [User to provide the correct uvicorn command]
```

### 2. Environment Variables
Verify `.env` file contains:
```bash
PRESGEN_CORE_URL=http://localhost:8080
PRESGEN_AVATAR_URL=http://localhost:8002
PRESGEN_USE_MOCK=False
```

### 3. Test Workflow
Create a test workflow with skill gaps:
```bash
# Use existing workflow or create new assessment
# Ensure workflow has completed gap analysis with skill_gaps populated
```

---

## Phase 1: Database Schema & Migration

### Test Case 1.1: Create Database Migration

**Objective**: Create `generated_courses` table for storing course generation metadata

**Steps**:
1. Create migration file:
```bash
cd /Users/yitzchak/Documents/learn/presentation_project/sales-agent-labs/presgen-assess
alembic revision -m "add_generated_courses_table_sprint4"
--
(.venv) yitzchak@MacBookPro presgen-assess % alembic revision -m "add_generated_courses_table_sprint4"
  Generating /Users/yitzchak/Documents/learn/presentation_project/sales-agent-
  labs/presgen-
  assess/alembic/versions/ecb6d5c3a67d_add_generated_courses_table_sprint4.py ...  done
```

2. Verify migration file created in `alembic/versions/`
--
DONE

**Expected Result**:
- Migration file created with timestamp prefix
- File name: `008_add_generated_courses_table_sprint4.py`

**✅ STOP HERE - Confirm migration file exists before proceeding**

---

### Test Case 1.2: Define Table Schema

**Objective**: Implement table schema with proper columns and indexes

**Migration Schema**:
```python
def upgrade():
    op.create_table(
        'generated_courses',
        sa.Column('id', sa.String(32), primary_key=True),
        sa.Column('workflow_id', sa.String(32), sa.ForeignKey('workflow_executions.id'), nullable=False),
        sa.Column('skill_id', sa.String(255), nullable=False),
        sa.Column('skill_name', sa.String(500), nullable=False),
        sa.Column('course_title', sa.String(500), nullable=True),

        # PresGen Integration
        sa.Column('presgen_core_job_id', sa.String(255), nullable=True),
        sa.Column('presgen_avatar_job_id', sa.String(255), nullable=True),
        sa.Column('presentation_url', sa.String(1000), nullable=True),
        sa.Column('video_url', sa.String(1000), nullable=True),

        # Progress & Status
        sa.Column('progress', sa.Integer(), default=0),
        sa.Column('status', sa.String(50), default='pending'),  # pending, generating, completed, failed
        sa.Column('error_message', sa.Text(), nullable=True),

        # Timestamps
        sa.Column('created_at', sa.DateTime(), server_default='CURRENT_TIMESTAMP'),
        sa.Column('updated_at', sa.DateTime(), server_default='CURRENT_TIMESTAMP'),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
    )

    # Indexes
    op.create_index('ix_generated_courses_workflow_id', 'generated_courses', ['workflow_id'])
    op.create_index('ix_generated_courses_skill_id', 'generated_courses', ['skill_id'])
    op.create_index('ix_generated_courses_status', 'generated_courses', ['status'])
```

**Steps**:
1. Edit migration file with schema above
2. Run migration:
```bash
alembic upgrade head
```

**Expected Result**:
```
INFO  [alembic.runtime.migration] Running upgrade 007 -> 008, add_generated_courses_table_sprint4
```

**Validation**:
```bash
sqlite3 test_database.db "SELECT sql FROM sqlite_master WHERE name='generated_courses';"
```

**✅ STOP HERE - Confirm table created successfully**

---

## Phase 2: PresGen-Avatar Client Setup

### Test Case 2.1: Create PresGen-Avatar Client Structure

**Objective**: Create client for PresGen-Avatar API integration

**Steps**:
1. Create directory structure:
```bash
mkdir -p src/integration/presgen_avatar
touch src/integration/presgen_avatar/__init__.py
touch src/integration/presgen_avatar/client.py
touch src/integration/presgen_avatar/schemas.py
```

2. Verify files created:
```bash
ls -la src/integration/presgen_avatar/
```

**Expected Result**:
```
__init__.py
client.py
schemas.py
```

**✅ STOP HERE - Confirm directory structure created**

---

### Test Case 2.2: Implement Avatar Client

**Objective**: Create HTTP client for PresGen-Avatar API

**File**: `src/integrations/presgen_avatar/client.py`

**Implementation**:
```python
import httpx
import asyncio
from typing import Optional, Dict, Any
from pydantic import BaseModel
import logging
from datetime import datetime

logger = logging.getLogger("presgen_avatar_client")

class AvatarGenerationRequest(BaseModel):
    """Request to PresGen-Avatar for video generation"""
    presentation_url: str
    mode: str = "presentation-only"
    quality: str = "fast"
    voice_config: Dict[str, Any] = {
        "provider": "openai",
        "voice_id": "alloy"
    }

class AvatarGenerationResponse(BaseModel):
    """Response from PresGen-Avatar"""
    job_id: str
    status: str
    video_url: Optional[str] = None
    progress: int = 0
    estimated_completion_seconds: Optional[int] = None

class PresGenAvatarClient:
    """Client for PresGen-Avatar API"""

    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip('/')
        self.client = httpx.AsyncClient(timeout=30.0)
        logger.info(f"🎬 PresGenAvatarClient initialized | base_url={self.base_url}")

    async def generate_video(
        self,
        presentation_url: str,
        mode: str = "presentation-only",
        quality: str = "fast",
        voice_provider: str = "openai",
        voice_id: str = "alloy"
    ) -> AvatarGenerationResponse:
        """
        Submit presentation for avatar video generation

        Args:
            presentation_url: URL to the presentation file
            mode: Generation mode (presentation-only, custom-script, etc.)
            quality: Quality setting (fast, standard, high)
            voice_provider: Voice provider (openai, elevenlabs, etc.)
            voice_id: Voice ID for the provider

        Returns:
            AvatarGenerationResponse with job_id and initial status
        """
        request = AvatarGenerationRequest(
            presentation_url=presentation_url,
            mode=mode,
            quality=quality,
            voice_config={
                "provider": voice_provider,
                "voice_id": voice_id
            }
        )

        logger.info(
            f"🎬 Submitting avatar generation request | "
            f"presentation_url={presentation_url} | mode={mode} | quality={quality}"
        )

        response = await self.client.post(
            f"{self.base_url}/api/v1/avatar/generate",
            json=request.dict()
        )
        response.raise_for_status()

        result = AvatarGenerationResponse(**response.json())
        logger.info(f"✅ Avatar generation submitted | job_id={result.job_id} | status={result.status}")

        return result

    async def get_status(self, job_id: str) -> AvatarGenerationResponse:
        """
        Get status of avatar generation job

        Args:
            job_id: Job identifier

        Returns:
            AvatarGenerationResponse with current status and progress
        """
        logger.info(f"📊 Checking avatar job status | job_id={job_id}")

        response = await self.client.get(
            f"{self.base_url}/api/v1/avatar/status/{job_id}"
        )
        response.raise_for_status()

        result = AvatarGenerationResponse(**response.json())
        logger.info(
            f"📊 Avatar job status | job_id={job_id} | status={result.status} | "
            f"progress={result.progress}%"
        )

        return result

    async def poll_until_complete(
        self,
        job_id: str,
        max_wait_seconds: int = 900,
        poll_interval_seconds: int = 10
    ) -> AvatarGenerationResponse:
        """
        Poll job status until completion or timeout

        Args:
            job_id: Job identifier
            max_wait_seconds: Maximum time to wait (default 15 minutes)
            poll_interval_seconds: Time between status checks

        Returns:
            Final AvatarGenerationResponse
        """
        start_time = datetime.now()
        logger.info(
            f"⏳ Starting avatar job polling | job_id={job_id} | "
            f"max_wait={max_wait_seconds}s | interval={poll_interval_seconds}s"
        )

        while True:
            elapsed = (datetime.now() - start_time).total_seconds()
            if elapsed > max_wait_seconds:
                raise TimeoutError(f"Avatar generation timed out after {max_wait_seconds}s")

            status = await self.get_status(job_id)

            if status.status == "completed":
                logger.info(f"✅ Avatar generation completed | job_id={job_id} | video_url={status.video_url}")
                return status
            elif status.status == "failed":
                raise RuntimeError(f"Avatar generation failed | job_id={job_id}")

            logger.info(f"⏳ Still generating... | progress={status.progress}% | elapsed={elapsed:.0f}s")
            await asyncio.sleep(poll_interval_seconds)

    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()
```

**Steps**:
1. Copy implementation to `src/integrations/presgen_avatar/client.py`
2. Verify import works:
```bash
./venv/bin/python -c "from src.integration.presgen_avatar.client import PresGenAvatarClient; print('✅ Import successful')"
```

**Expected Result**:
```
✅ Import successful
--
DONE
```

**✅ STOP HERE - Confirm client implementation works**

---

### Test Case 2.3: Configure Logging

**Objective**: Set up dedicated course generation logging

**File**: `src/services/course_generation_service.py` (create new)

**Implementation**:
```python
import logging
from logging.handlers import RotatingFileHandler
import os

# Create logs directory if it doesn't exist
os.makedirs("logs", exist_ok=True)

# Configure course generation logger
course_gen_logger = logging.getLogger("course_generation")
course_gen_logger.setLevel(logging.INFO)

# File handler with rotation (10MB max, keep 5 backups)
file_handler = RotatingFileHandler(
    "logs/course_generation.log",
    maxBytes=10*1024*1024,  # 10MB
    backupCount=5
)
file_handler.setLevel(logging.INFO)

# Format: timestamp | level | message
formatter = logging.Formatter(
    '%(asctime)s | %(levelname)-8s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
file_handler.setFormatter(formatter)

course_gen_logger.addHandler(file_handler)

# Prevent propagation to root logger
course_gen_logger.propagate = False

def log_course_event(event: str, **kwargs):
    """Log course generation event with context"""
    context = " | ".join([f"{k}={v}" for k, v in kwargs.items()])
    course_gen_logger.info(f"{event} | {context}")
```

**Steps**:
1. Create the service file
2. Test logging:
```bash
./venv/bin/python -c "
from src.services.course_generation_service import log_course_event
log_course_event('TEST', workflow_id='test-123', skill='Python')
print('✅ Logging configured')
"
--
✅ Logging configured
```

3. Verify log file created:
```bash
cat logs/course_generation.log
--

(.venv) yitzchak@MacBookPro presgen-assess % cat logs/course_generation.log
2025-10-05 11:59:03 | INFO     | TEST | workflow_id=test-123 | skill=Python
```

**Expected Result**:
```
2025-10-05 10:45:23 | INFO     | TEST | workflow_id=test-123 | skill=Python
```

**✅ STOP HERE - Confirm logging is working**

---

## Phase 3: Course Generation API Endpoints

### Test Case 3.1: Create API Endpoint for Single Course Generation

**Objective**: Implement endpoint to generate course for individual skill

**File**: `src/service/api/v1/endpoints/workflows.py`

**Add this endpoint**:
```python
@router.post(
    "/{workflow_id}/skills/{skill_id}/generate-course",
    response_model=CourseGenerationResponse,
    summary="Generate course for individual skill",
    description="Generate avatar-narrated course for a specific skill gap"
)
async def generate_skill_course(
    workflow_id: str,
    skill_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Generate course for individual skill with PresGen-Avatar integration

    Flow:
    1. Fetch skill gap details from recommended_courses
    2. Get certification profile's presentation_prompt
    3. Call PresGen-Core with custom prompt
    4. Call PresGen-Avatar for video narration
    5. Return course metadata with video URL
    """
    from src.services.course_generation_service import log_course_event
    from src.integrations.presgen_avatar.client import PresGenAvatarClient
    from src.integrations.presgen_core.client import PresGenCoreClient

    log_course_event("COURSE_GENERATION_STARTED", workflow_id=workflow_id, skill_id=skill_id)

    # 1. Fetch workflow and skill details
    result = await db.execute(
        select(WorkflowExecution).where(WorkflowExecution.id == workflow_id)
    )
    workflow = result.scalar_one_or_none()
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")

    # 2. Fetch skill gap from recommended_courses
    result = await db.execute(
        select(RecommendedCourse).where(
            and_(
                RecommendedCourse.workflow_id == workflow_id,
                RecommendedCourse.skill_id == skill_id
            )
        )
    )
    skill_course = result.scalar_one_or_none()
    if not skill_course:
        raise HTTPException(status_code=404, detail="Skill not found in recommended courses")

    log_course_event("SKILL_FOUND", skill_name=skill_course.skill_name, severity=skill_course.severity)

    # 3. Get certification profile's custom prompt
    result = await db.execute(
        select(CertificationProfile).where(
            CertificationProfile.id == workflow.certification_profile_id
        )
    )
    cert_profile = result.scalar_one_or_none()
    custom_prompt = cert_profile.presentation_prompt if cert_profile else None

    log_course_event("CUSTOM_PROMPT_LOADED", has_custom_prompt=bool(custom_prompt))

    # 4. Create course record
    course_id = str(uuid.uuid4().hex)
    course = GeneratedCourse(
        id=course_id,
        workflow_id=workflow_id,
        skill_id=skill_id,
        skill_name=skill_course.skill_name,
        course_title=f"Mastering {skill_course.skill_name}",
        status="pending",
        progress=0
    )
    db.add(course)
    await db.commit()

    log_course_event("COURSE_RECORD_CREATED", course_id=course_id)

    # 5. Call PresGen-Core for presentation
    presgen_core = PresGenCoreClient(base_url=os.getenv("PRESGEN_CORE_URL"))

    presentation_spec = {
        "skill": skill_course.skill_name,
        "domain": skill_course.domain,
        "target_duration_minutes": 10,
        "custom_prompt": custom_prompt
    }

    course.status = "generating_presentation"
    course.progress = 25
    await db.commit()

    log_course_event("PRESGEN_CORE_STARTED", course_id=course_id)

    # TODO: Implement actual PresGen-Core call
    # presgen_result = await presgen_core.generate_presentation(presentation_spec)

    # Mock response for testing
    presentation_url = f"https://drive.google.com/presentations/{course_id}"
    course.presentation_url = presentation_url
    course.progress = 50
    await db.commit()

    log_course_event("PRESGEN_CORE_COMPLETED", presentation_url=presentation_url)

    # 6. Call PresGen-Avatar for narration
    avatar_client = PresGenAvatarClient(base_url=os.getenv("PRESGEN_AVATAR_URL"))

    course.status = "generating_video"
    course.progress = 60
    await db.commit()

    log_course_event("PRESGEN_AVATAR_STARTED", presentation_url=presentation_url)

    # TODO: Implement actual PresGen-Avatar call
    # avatar_result = await avatar_client.generate_video(
    #     presentation_url=presentation_url,
    #     mode="presentation-only",
    #     quality="fast",
    #     voice_provider="openai",
    #     voice_id="alloy"
    # )

    # Mock response for testing
    video_url = f"https://storage.googleapis.com/videos/{course_id}.mp4"
    course.video_url = video_url
    course.status = "completed"
    course.progress = 100
    course.completed_at = datetime.utcnow()
    await db.commit()

    log_course_event("COURSE_GENERATION_COMPLETED", video_url=video_url, duration_seconds=45)

    return CourseGenerationResponse(
        course_id=course.id,
        workflow_id=workflow_id,
        skill_id=skill_id,
        skill_name=skill_course.skill_name,
        course_title=course.course_title,
        presentation_url=course.presentation_url,
        video_url=course.video_url,
        status=course.status,
        progress=course.progress,
        created_at=course.created_at,
        completed_at=course.completed_at
    )
```

**Steps**:
1. Add endpoint to workflows.py
2. Restart PresGen-Assess server
3. Test endpoint with curl:
```bash
curl -X POST "http://localhost:8000/api/v1/workflows/{workflow_id}/skills/{skill_id}/generate-course" -H "Content-Type: application/json"
```
--
(.venv) yitzchak@MacBookPro presgen-assess % curl -X POST \
  "http://localhost:8000/api/v1/workflows/52014fe9-6b77-4e91-b770-ff20b24d7ff7/skills/modeling/generate-course"

{"course_id":"d1fdcffee5cf4e6cb88a02b8b53986d1","workflow_id":"52014fe9-6b77-4e91-b770-ff20b24d7ff7","skill_id":"modeling","skill_name":"Modeling","course_title":"Mastering Modeling","presentation_url":"https://drive.google.com/presentation/d/core_8be278bff49e40e5a4313c1f14624bdb/edit","video_url":"https://storage.googleapis.com/videos/d1fdcffee5cf4e6cb88a02b8b53986d1.mp4","status":"completed","progress":100,"created_at":"2025-10-05T12:12:56.191691","updated_at":null,"completed_at":"2025-10-05T12:12:56.199200"}%                 
**Expected Result**:
```json
{
  "course_id": "abc123...",
  "status": "completed",
  "progress": 100,
  "video_url": "https://storage.googleapis.com/videos/abc123.mp4"
}
```

**✅ STOP HERE - Test endpoint and verify response**

---

### Test Case 3.2: Add Course Status Endpoint

**Objective**: Check real-time progress of course generation

**Add endpoint**:
```python
@router.get(
    "/{workflow_id}/courses/{course_id}/status",
    response_model=CourseStatusResponse,
    summary="Get course generation status"
)
async def get_course_status(
    workflow_id: str,
    course_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get real-time status of course generation"""
    result = await db.execute(
        select(GeneratedCourse).where(
            and_(
                GeneratedCourse.workflow_id == workflow_id,
                GeneratedCourse.id == course_id
            )
        )
    )
    course = result.scalar_one_or_none()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    return CourseStatusResponse(
        course_id=course.id,
        status=course.status,
        progress=course.progress,
        presentation_url=course.presentation_url,
        video_url=course.video_url,
        error_message=course.error_message
    )
```

**Test**:
```bash
curl "http://localhost:8000/api/v1/workflows/{workflow_id}/courses/{course_id}/status"
```

--
(.venv) yitzchak@MacBookPro presgen-assess % curl "http://localhost:8000/api/v1/workflows/52014fe9-6b77-4e91-b770-ff20b24d7ff7/courses/9c478b6789df4216ab9015bfa555bb51/status"

{"course_id":"9c478b6789df4216ab9015bfa555bb51","status":"completed","progress":100,"presentation_url":"https://drive.google.com/presentation/d/core_ae98d8486a084b039ff820290ff793ad/edit","video_url":"https://storage.googleapis.com/videos/9c478b6789df4216ab9015bfa555bb51.mp4","error_message":null}%                

**Expected Result**:
```json
{
  "course_id": "abc123",
  "status": "completed",
  "progress": 100,
  "video_url": "..."
}
```

**✅ STOP HERE - Verify status endpoint works**

---

## Phase 4: Frontend Integration

### Test Case 4.1: Add "Generate Course" Button

**Objective**: Add UI button to trigger course generation

**File**: `presgen-ui/src/components/assess/RecommendedCoursesTab.tsx` (or similar)

**Add button for each skill**:
```typescript
<Button
  onClick={() => handleGenerateCourse(skill.skill_id)}
  disabled={generatingCourseId === skill.skill_id}
>
  {generatingCourseId === skill.skill_id ? (
    <>
      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
      Generating... {progress}%
    </>
  ) : (
    <>
      <PlayCircle className="mr-2 h-4 w-4" />
      Generate Course
    </>
  )}
</Button>
```

**Handler**:
```typescript
const handleGenerateCourse = async (skillId: string) => {
  setGeneratingCourseId(skillId);

  try {
    const response = await fetch(
      `/api/presgen-assess/workflows/${workflowId}/skills/${skillId}/generate-course`,
      { method: 'POST' }
    );

    const result = await response.json();

    // Poll for status
    const pollInterval = setInterval(async () => {
      const statusRes = await fetch(
        `/api/presgen-assess/workflows/${workflowId}/courses/${result.course_id}/status`
      );
      const status = await statusRes.json();

      setProgress(status.progress);

      if (status.status === 'completed') {
        clearInterval(pollInterval);
        setGeneratingCourseId(null);
        setVideoUrl(status.video_url);
        toast.success('Course generated successfully!');
      }
    }, 2000);

  } catch (error) {
    toast.error('Failed to generate course');
    setGeneratingCourseId(null);
  }
};
```

**✅ STOP HERE - Verify button appears in UI**

---

## Phase 5: End-to-End Workflow Testing

### Test Case 5.1: Complete Workflow Test

**Objective**: Test entire flow from button click to video display

**Steps**:
1. Create new assessment workflow
2. Complete gap analysis
3. Navigate to Recommended Courses tab
4. Click "Generate Course" on a skill
5. Monitor logs: `tail -f logs/course_generation.log`
6. Verify video URL returned
7. Test video playback in UI

**Expected Log Output**:
```
2025-10-05 10:45:23 | INFO | COURSE_GENERATION_STARTED | workflow_id=xxx | skill_id=yyy
2025-10-05 10:45:24 | INFO | SKILL_FOUND | skill_name=Python | severity=high
2025-10-05 10:45:24 | INFO | CUSTOM_PROMPT_LOADED | has_custom_prompt=True
2025-10-05 10:45:25 | INFO | COURSE_RECORD_CREATED | course_id=zzz
2025-10-05 10:45:26 | INFO | PRESGEN_CORE_STARTED | course_id=zzz
2025-10-05 10:45:40 | INFO | PRESGEN_CORE_COMPLETED | presentation_url=...
2025-10-05 10:45:41 | INFO | PRESGEN_AVATAR_STARTED | presentation_url=...
2025-10-05 10:46:15 | INFO | COURSE_GENERATION_COMPLETED | video_url=... | duration_seconds=45
```

**✅ SUCCESS CRITERIA**:
- ✅ Button click triggers generation
- ✅ Progress updates in UI (0% → 100%)
- ✅ Logs show all phases
- ✅ Video URL returned
- ✅ Video plays in UI

---

## Troubleshooting

### Issue: PresGen-Avatar not responding
**Solution**: Verify PresGen-Avatar server is running on port 8002
```bash
curl http://localhost:8002/health
```

### Issue: Custom prompt not being used
**Solution**: Check certification profile has presentation_prompt set
```sql
SELECT presentation_prompt FROM certification_profiles WHERE id = 'xxx';
```

### Issue: Logs not appearing
**Solution**: Verify logs directory exists and has write permissions
```bash
ls -la logs/
chmod 755 logs/
```

---

## Next Steps

After all tests pass:
1. ✅ Switch to production PresGen-Avatar integration
2. ✅ Add error handling and retries
3. ✅ Implement batch course generation
4. ✅ Add video thumbnail generation
5. ✅ Deploy to staging environment

---

**Document Status**: Ready for Testing
**Last Updated**: 2025-10-05
**Next Review**: After Phase 3 completion
