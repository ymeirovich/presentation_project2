# Sprint 4: Individual Skill Course Generation - Implementation Plan

**Created**: 2025-10-05
**Sprint**: Sprint 4 - PresGen-Avatar Integration
**Status**: Active Development

## 📋 Executive Summary

### Objective
Implement **per-skill course generation** with PresGen-Avatar video narration, enabling users to generate individual courses for specific skill gaps directly from the Recommended Courses tab.

### Key Deliverables
1. ✅ Database schema for `generated_courses` table
2. ✅ PresGen-Avatar HTTP client with async polling
3. ✅ Course generation API endpoints (POST, GET status)
4. ✅ Enhanced logging to `course_generation.log`
5. ✅ Frontend "Generate Course" button integration
6. ✅ End-to-end workflow: Click → Core → Avatar → Video Display

### Architecture Overview
```
User Interface (Recommended Courses Tab)
    ↓ [Click "Generate Course"]
PresGen-Assess API (port 8000)
    ↓ [Create presentation]
PresGen-Core (port 8080)
    ↓ [Generate video]
PresGen-Avatar (port 8002)
    ↓ [Return video URL]
Display Video in UI
```

---

## 🎯 Sprint Goals

### Primary Goals
1. **Per-Skill Generation**: Enable course generation for individual skills (not batch)
2. **Custom Prompt Override**: Use certification profile's `presentation_prompt` field
3. **PresGen-Avatar Integration**: Presentation-only mode with OpenAI voice
4. **Progress Tracking**: Real-time status updates (0-100%)
5. **Enhanced Logging**: Dedicated log file for course generation events

### Success Criteria
- ✅ User can click "Generate Course" on any skill in Recommended Courses tab
- ✅ Backend orchestrates PresGen-Core → PresGen-Avatar pipeline
- ✅ Custom prompts from certification profiles are used
- ✅ Video URL is returned and playable in UI
- ✅ All events logged to `course_generation.log`
- ✅ Progress updates displayed in real-time

---

## 📊 Phase Breakdown

### Phase 1: Database Schema (Week 1, Day 1)

**Status**: ✅ Completed (migration `ce9ec16057c4_add_generated_courses_table_sprint4.py` applied, SQLAlchemy model in `src/models/generated_course.py`)

#### Task 1.1: Create Migration
**File**: `alembic/versions/008_add_generated_courses_table_sprint4.py`

**Schema**:
```python
def upgrade():
    op.create_table(
        'generated_courses',
        sa.Column('id', sa.String(32), primary_key=True),
        sa.Column('workflow_id', sa.String(32), sa.ForeignKey('workflow_executions.id')),
        sa.Column('skill_id', sa.String(255), nullable=False),
        sa.Column('skill_name', sa.String(500), nullable=False),
        sa.Column('course_title', sa.String(500)),

        # Integration
        sa.Column('presgen_core_job_id', sa.String(255)),
        sa.Column('presgen_avatar_job_id', sa.String(255)),
        sa.Column('presentation_url', sa.String(1000)),
        sa.Column('video_url', sa.String(1000)),

        # Status
        sa.Column('progress', sa.Integer(), default=0),
        sa.Column('status', sa.String(50), default='pending'),
        sa.Column('error_message', sa.Text()),

        # Timestamps
        sa.Column('created_at', sa.DateTime(), server_default='CURRENT_TIMESTAMP'),
        sa.Column('updated_at', sa.DateTime(), server_default='CURRENT_TIMESTAMP'),
        sa.Column('completed_at', sa.DateTime())
    )

    op.create_index('ix_generated_courses_workflow_id', 'generated_courses', ['workflow_id'])
    op.create_index('ix_generated_courses_skill_id', 'generated_courses', ['skill_id'])
    op.create_index('ix_generated_courses_status', 'generated_courses', ['status'])
```

**Testing**:
```bash
alembic revision -m "add_generated_courses_table_sprint4"
alembic upgrade head
sqlite3 test_database.db "SELECT sql FROM sqlite_master WHERE name='generated_courses';"
```

#### Task 1.2: Create SQLAlchemy Model
**File**: `src/models/generated_course.py`

```python
from sqlalchemy import Column, String, Integer, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from src.service.database import Base

class GeneratedCourse(Base):
    __tablename__ = "generated_courses"

    id = Column(String(32), primary_key=True)
    workflow_id = Column(String(32), ForeignKey("workflow_executions.id"), nullable=False)
    skill_id = Column(String(255), nullable=False)
    skill_name = Column(String(500), nullable=False)
    course_title = Column(String(500))

    # Integration
    presgen_core_job_id = Column(String(255))
    presgen_avatar_job_id = Column(String(255))
    presentation_url = Column(String(1000))
    video_url = Column(String(1000))

    # Status
    progress = Column(Integer, default=0)
    status = Column(String(50), default='pending')
    error_message = Column(Text)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at = Column(DateTime)

    # Relationships
    workflow = relationship("WorkflowExecution", back_populates="generated_courses")
```

---

### Phase 2: PresGen-Avatar Client (Week 1, Day 2)

**Status**: 🚧 In Progress (client package committed, wiring HTTP requests + polling in this phase)

**Goal Summary**
- Build an async HTTP client that mirrors production PresGen-Avatar behaviour while supporting local mock mode.
- Formalize request/response schemas (Pydantic) with `voice_config`, progress, and status fields consumed by API layer.
- Expose helpers for generate → poll workflows so `workflows.generate_skill_course` can orchestrate avatar narration without bespoke code.

#### Task 2.1: Create Client Structure
**Directory**: `src/integrations/presgen_avatar/`

**Files**:
- `__init__.py` - Package initialization
- `client.py` - HTTP client implementation
- `schemas.py` - Pydantic request/response models

#### Task 2.2: Implement HTTP Client
**File**: `src/integrations/presgen_avatar/client.py`

**Key Methods**:
```python
class PresGenAvatarClient:
    async def generate_video(
        self,
        presentation_url: str,
        mode: str = "presentation-only",
        quality: str = "fast",
        voice_provider: str = "openai",
        voice_id: str = "alloy"
    ) -> AvatarGenerationResponse

    async def get_status(self, job_id: str) -> AvatarGenerationResponse

    async def poll_until_complete(
        self,
        job_id: str,
        max_wait_seconds: int = 900,
        poll_interval_seconds: int = 10
    ) -> AvatarGenerationResponse
```

**Configuration**:
- Base URL: `http://localhost:8002` (from `.env`)
- Timeout: 30 seconds per request
- Max polling: 15 minutes (900s)
- Poll interval: 10 seconds

#### Task 2.3: Define Schemas
**File**: `src/integrations/presgen_avatar/schemas.py`

```python
from pydantic import BaseModel
from typing import Optional, Dict, Any

class AvatarGenerationRequest(BaseModel):
    presentation_url: str
    mode: str = "presentation-only"
    quality: str = "fast"
    voice_config: Dict[str, Any]

class AvatarGenerationResponse(BaseModel):
    job_id: str
    status: str
    video_url: Optional[str] = None
    progress: int = 0
    estimated_completion_seconds: Optional[int] = None
```

---

### Phase 3: Enhanced Logging (Week 1, Day 2)

**Status**: ✅ Complete (central logger shipped with rotation + Phase 3 TDD executed)

#### Task 3.1: Configure Course Generation Logger
**File**: `src/services/course_generation_service.py`

**Setup**:
```python
import logging
from logging.handlers import RotatingFileHandler

# Create logs directory
os.makedirs("logs", exist_ok=True)

# Configure logger
course_gen_logger = logging.getLogger("course_generation")
course_gen_logger.setLevel(logging.INFO)

# File handler with rotation
file_handler = RotatingFileHandler(
    "logs/course_generation.log",
    maxBytes=10*1024*1024,  # 10MB
    backupCount=5
)
formatter = logging.Formatter(
    '%(asctime)s | %(levelname)-8s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
file_handler.setFormatter(formatter)
course_gen_logger.addHandler(file_handler)
course_gen_logger.propagate = False
```

#### Task 3.2: Define Logging Events
**Events to Log**:
1. `COURSE_GENERATION_STARTED` - Initial request received
2. `SKILL_FOUND` - Skill details retrieved
3. `CUSTOM_PROMPT_LOADED` - Certification profile prompt loaded
4. `COURSE_RECORD_CREATED` - Database record created
5. `PRESGEN_CORE_STARTED` - Presentation generation initiated
6. `PRESGEN_CORE_COMPLETED` - Presentation URL received
7. `PRESGEN_AVATAR_STARTED` - Video generation initiated
8. `PRESGEN_AVATAR_PROGRESS` - Progress updates (every 10%)
9. `PRESGEN_AVATAR_COMPLETED` - Video URL received
10. `COURSE_GENERATION_COMPLETED` - Final success
11. `COURSE_GENERATION_FAILED` - Error occurred

**Log Format**:
```
2025-10-05 10:45:23 | INFO | EVENT_NAME | key1=value1 | key2=value2
```

---

### Phase 4: API Endpoints (Week 1, Day 3-4)

**Status**: ✅ Complete (POST/GET endpoints validated via Phase 4 TDD)

#### Task 4.1: Generate Course Endpoint
**File**: `src/service/api/v1/endpoints/workflows.py`

**Endpoint**:
```python
@router.post(
    "/{workflow_id}/skills/{skill_id}/generate-course",
    response_model=CourseGenerationResponse
)
async def generate_skill_course(
    workflow_id: str,
    skill_id: str,
    db: AsyncSession = Depends(get_db)
)
```

**Flow**:
1. Fetch workflow and validate
2. Fetch skill from `recommended_courses` table
3. Get certification profile's `presentation_prompt`
4. Create `GeneratedCourse` record (status=pending)
5. Call PresGen-Core with custom prompt
6. Update record (status=generating_presentation, progress=50)
7. Call PresGen-Avatar with presentation URL
8. Poll for completion with progress updates
9. Update record (status=completed, progress=100)
10. Return course details with video URL

**Response**:
```json
{
  "course_id": "abc123",
  "workflow_id": "workflow-456",
  "skill_id": "python_basics",
  "skill_name": "Python Fundamentals",
  "course_title": "Mastering Python Fundamentals",
  "presentation_url": "https://drive.google.com/...",
  "video_url": "https://storage.googleapis.com/...",
  "status": "completed",
  "progress": 100,
  "created_at": "2025-10-05T10:45:00Z",
  "completed_at": "2025-10-05T10:46:30Z"
}
```

#### Task 4.2: Course Status Endpoint
**Endpoint**:
```python
@router.get(
    "/{workflow_id}/courses/{course_id}/status",
    response_model=CourseStatusResponse
)
async def get_course_status(
    workflow_id: str,
    course_id: str,
    db: AsyncSession = Depends(get_db)
)
```

**Response**:
```json
{
  "course_id": "abc123",
  "status": "generating_video",
  "progress": 75,
  "presentation_url": "https://drive.google.com/...",
  "video_url": null,
  "error_message": null
}
```

#### Task 4.3: List Courses Endpoint
**Endpoint**:
```python
@router.get(
    "/{workflow_id}/courses",
    response_model=List[CourseGenerationResponse]
)
async def list_workflow_courses(
    workflow_id: str,
    db: AsyncSession = Depends(get_db)
)
```

---

### Phase 5: Frontend Integration (Week 1, Day 5)

**Status**: ✅ Complete (UI controls, polling, and playback validated via Phase 5 TDD)

#### Task 5.1: Add Generate Course Button
**File**: `presgen-ui/src/components/assess/RecommendedCoursesTab.tsx`

**UI Component**:
```tsx
{skill.courses.map(course => (
  <div key={course.skill_id} className="border rounded-lg p-4">
    <h3>{course.skill_name}</h3>
    <p>Severity: {course.severity}</p>

    <Button
      onClick={() => handleGenerateCourse(course.skill_id)}
      disabled={generatingCourseId === course.skill_id}
    >
      {generatingCourseId === course.skill_id ? (
        <>
          <Loader2 className="animate-spin mr-2" />
          Generating... {progress}%
        </>
      ) : (
        <>
          <PlayCircle className="mr-2" />
          Generate Course
        </>
      )}
    </Button>

    {courseVideos[course.skill_id] && (
      <VideoPlayer url={courseVideos[course.skill_id]} />
    )}
  </div>
))}
```

#### Task 5.2: Implement Generation Handler
```typescript
const handleGenerateCourse = async (skillId: string) => {
  setGeneratingCourseId(skillId);
  setProgress(0);

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
        setCourseVideos(prev => ({
          ...prev,
          [skillId]: status.video_url
        }));
        setGeneratingCourseId(null);
        toast.success('Course generated!');
      } else if (status.status === 'failed') {
        clearInterval(pollInterval);
        setGeneratingCourseId(null);
        toast.error(status.error_message || 'Generation failed');
      }
    }, 2000);

  } catch (error) {
    toast.error('Failed to generate course');
    setGeneratingCourseId(null);
  }
};
```

#### Task 5.3: Add Video Player Component
```tsx
const VideoPlayer = ({ url }: { url: string }) => (
  <div className="mt-4">
    <video controls className="w-full rounded-lg">
      <source src={url} type="video/mp4" />
      Your browser does not support video playback.
    </video>
  </div>
);
```

---

### Phase 6: PresGen-Core Custom Prompt Integration (Week 2, Day 1)

**Status**: ✅ Complete (prompt overrides flowing to PresGen-Core; Phase 6 TDD validated)

#### Task 6.1: Modify PresGenCoreClient
**File**: `src/integrations/presgen_core/client.py`

**Add custom prompt support**:
```python
async def generate_presentation(
    self,
    skill: str,
    domain: str,
    custom_prompt: Optional[str] = None,
    target_duration_minutes: int = 10
) -> PresentationGenerationResponse:
    """
    Generate presentation with optional custom prompt override

    Args:
        skill: Skill name
        domain: Domain/subdomain
        custom_prompt: Custom prompt from certification profile (overrides default)
        target_duration_minutes: Target presentation length
    """
    payload = {
        "skill": skill,
        "domain": domain,
        "target_duration_minutes": target_duration_minutes,
        "prompt": custom_prompt or self._get_default_prompt()
    }

    response = await self.client.post(
        f"{self.base_url}/api/v1/presentations/generate",
        json=payload
    )
    return PresentationGenerationResponse(**response.json())
```

#### Task 6.2: Fetch Custom Prompt from Certification Profile
**In course generation endpoint**:
```python
# Get certification profile's custom prompt
result = await db.execute(
    select(CertificationProfile).where(
        CertificationProfile.id == workflow.certification_profile_id
    )
)
cert_profile = result.scalar_one_or_none()
custom_prompt = cert_profile.presentation_prompt if cert_profile else None

log_course_event("CUSTOM_PROMPT_LOADED", has_custom_prompt=bool(custom_prompt))

# Use custom prompt in PresGen-Core call
presgen_result = await presgen_core.generate_presentation(
    skill=skill_course.skill_name,
    domain=skill_course.domain,
    custom_prompt=custom_prompt,
    target_duration_minutes=10
)
```

---

### Phase 7: Error Handling & Resilience (Week 2, Day 2)

**Status**: ✅ Complete (retry/backoff + circuit breakers implemented; Phase 7 TDD validated)

#### Task 7.1: Add Retry Logic
```python
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=10)
)
async def generate_presentation_with_retry(client, **kwargs):
    return await client.generate_presentation(**kwargs)
```

#### Task 7.2: Implement Circuit Breaker
```python
from circuitbreaker import circuit

@circuit(failure_threshold=5, recovery_timeout=60)
async def call_presgen_avatar(client, **kwargs):
    return await client.generate_video(**kwargs)
```

#### Task 7.3: Add Error Recovery
```python
try:
    avatar_result = await call_presgen_avatar(avatar_client, ...)
except Exception as e:
    course.status = "failed"
    course.error_message = str(e)
    await db.commit()
    log_course_event("COURSE_GENERATION_FAILED", error=str(e))
    raise
```

---

### Phase 8: Local MP4 Output & Downloads (Week 2, Day 3)

**Status**: 🚧 In Progress (timestamp job IDs, local avatar storage, and UI download link implementation underway)

#### Task 8.1: Timestamped Job Identifiers
```python
from datetime import datetime

timestamp_id = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
course_id = timestamp_id
```

#### Task 8.2: Persist Avatar Outputs Locally
```python
from datetime import datetime

timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
safe_skill = skill_id.lower().replace(" ", "-")

output_dir = settings.avatar_output_dir / workflow_id_str / "jobs" / avatar_result.job_id
output_dir.mkdir(parents=True, exist_ok=True)
mp4_path = output_dir / f"avatar-{safe_skill}-{timestamp}.mp4"

async with httpx.AsyncClient(timeout=None) as client:
    async with client.stream("GET", final_status.video_url) as stream:
        stream.raise_for_status()
        with mp4_path.open("wb") as fh:
            async for chunk in stream.aiter_bytes():
                fh.write(chunk)

course.local_video_path = str(mp4_path)
course.video_url = f"/api/v1/workflows/{workflow_id_str}/courses/{course_id}/video"
```

#### Task 8.3: Download Endpoint & UI Link
```python
# backend
return FileResponse(Path(course.local_video_path), media_type="video/mp4")

# frontend (React)
<Button asChild variant="ghost" size="sm">
  <a href={`/api/presgen-assess/workflows/${workflowId}/courses/${courseIds[course.skill_id]}/video`}>
    Download Video
  </a>
</Button>
```

#### Task 8.4: Phase 8 TDD
- See `Oct5_Avatar_SPRINT_4_PHASE8_TDD_MANUAL_TESTING.md` for manual verification steps covering timestamp IDs, local storage, and UI download link.

---

## 🧪 Testing Strategy

### Unit Tests
- PresGen-Avatar client methods
- Course generation service logic
- Custom prompt extraction

### Integration Tests
- End-to-end course generation flow
- Database operations
- API endpoint responses

### Manual TDD Tests
- Follow `SPRINT_4_TDD_MANUAL_TESTING.md`
- Test each phase independently
- Verify logging at each step

---

## 📈 Success Metrics

### Performance Targets
- Course generation: < 2 minutes (including video)
- API response time: < 500ms (initial request)
- Progress updates: Every 10 seconds
- Log file size: Auto-rotate at 10MB

### Quality Metrics
- Test coverage: > 80%
- Error rate: < 5%
- Custom prompt usage: 100% when available
- Video playback success: > 95%

---

## 🚀 Deployment Plan

### Development (Week 2, Day 3)
1. ✅ All unit tests passing
2. ✅ Integration tests passing
3. ✅ Manual TDD complete
4. ✅ Logging verified

### Staging (Week 2, Day 4)
1. Deploy to staging environment
2. Run smoke tests
3. Performance testing
4. User acceptance testing

### Production (Week 2, Day 5)
1. Feature flag enabled
2. Monitor logs and metrics
3. Gradual rollout (10% → 50% → 100%)
4. Rollback plan ready

---

## 📝 Documentation Updates

### Files to Update
1. ✅ `SPRINT_4_TDD_MANUAL_TESTING.md` - Testing guide
2. ✅ `SPRINT_4_IMPLEMENTATION_PLAN.md` - This document
3. ⏳ `ASSESSMENT_WORKFLOW_PROJECT_STATUS.md` - Status update
4. ⏳ API documentation (OpenAPI/Swagger)
5. ⏳ User guide updates

---

## 🔗 Dependencies

### External Services
- ✅ PresGen-Core (port 8080) - Presentation generation
- ❓ PresGen-Avatar (port 8002) - Video narration [Need uvicorn command]
- ✅ Google Drive - File storage

### Internal Dependencies
- ✅ Database: `generated_courses` table
- ✅ Models: `GeneratedCourse`, `RecommendedCourse`
- ✅ Logging: `course_generation.log`

---

## 📅 Timeline

| Phase | Duration | Status |
|-------|----------|--------|
| Phase 1: Database Schema | 1 day | ⏳ Ready to start |
| Phase 2: PresGen-Avatar Client | 1 day | ⏳ Ready to start |
| Phase 3: Enhanced Logging | 0.5 day | ⏳ Ready to start |
| Phase 4: API Endpoints | 2 days | ⏳ Ready to start |
| Phase 5: Frontend Integration | 1 day | ⏳ Ready to start |
| Phase 6: Custom Prompt | 1 day | ⏳ Ready to start |
| Phase 7: Error Handling | 1 day | ⏳ Ready to start |
| Testing & QA | 2 days | ⏳ Pending |
| **Total** | **10 days** | **Sprint 4** |

---

**Document Status**: Active Development
**Last Updated**: 2025-10-05
**Next Review**: After Phase 1 completion
**Owner**: Development Team
