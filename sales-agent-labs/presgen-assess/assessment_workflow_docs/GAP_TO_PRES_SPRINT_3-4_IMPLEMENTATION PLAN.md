Detailed Implementation Plans: Options 1, 2, 3, 5
Option 1: Production PresGen-Core Integration 🎨
Overview
Switch from mock mode to real Google Slides generation using the PresGen-Core service running on port 8001.
Prerequisites
PresGen-Core service running on http://localhost:8001
Google Cloud credentials configured
OAuth token for Google Slides API
40-slide template support enabled
Implementation Steps
Phase 1: Environment Configuration (15 mins)
Files: .env, src/common/config.py
Verify PresGen-Core is running
curl http://localhost:8001/health
# Expected: {"status": "healthy"}
Update .env configuration
# Ensure these are set:
PRESGEN_CORE_URL=http://localhost:8001
PRESGEN_CORE_MAX_SLIDES=40
GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json
OAUTH_TOKEN_PATH=/path/to/token.json
Verify Google credentials
# Check service account file exists
ls -la /Users/yitzchak/Documents/learn/presentation_project/sales-agent-labs/presgen-service-account2.json

# Check OAuth token exists
ls -la /Users/yitzchak/Documents/learn/presentation_project/sales-agent-labs/token.json
Phase 2: Disable Mock Mode (5 mins)
File: src/service/presgen_core_client.py
Locate mock flag
# Find this line (around line 50-60):
self.use_mock = True  # Mock mode for Sprint 3 testing
Change to production mode
self.use_mock = False  # Production mode - use real PresGen-Core API
Add environment-based toggle (recommended)
# Better approach - control via environment variable:
from src.common.config import settings

self.use_mock = settings.debug  # Mock in debug mode, production otherwise
Phase 3: Update API Client Methods (30 mins)
File: src/service/presgen_core_client.py
Review generate_presentation() method
Ensure proper API endpoint URL construction
Verify request payload format matches PresGen-Core API
Check timeout settings (should be 600 seconds = 10 mins)
Update progress callback handling
async def generate_presentation(
    self,
    content_spec: PresentationContentSpec,
    progress_callback: Optional[Callable] = None
):
    if self.use_mock:
        return await self._mock_generate_presentation(content_spec, progress_callback)
    
    # Real API call
    url = f"{self.base_url}/api/v1/presentations/generate"
    
    payload = {
        "title": content_spec.title,
        "skill_name": content_spec.skill_name,
        "skill_description": content_spec.skill_description,
        "learning_objectives": content_spec.learning_objectives,
        "content_items": content_spec.content_items,
        "assessment_context": {
            "overall_score": content_spec.overall_score,
            "skill_score": content_spec.skill_score
        },
        "template_config": {
            "max_slides": 11,  # Short-form per-skill
            "template_id": "short_form_skill"
        }
    }
    
    # Make async HTTP request with progress tracking
    async with aiohttp.ClientSession() as session:
        async with session.post(
            url,
            json=payload,
            timeout=aiohttp.ClientTimeout(total=600)
        ) as response:
            if response.status != 200:
                raise Exception(f"PresGen-Core API error: {response.status}")
            
            result = await response.json()
            return self._parse_presgen_response(result)
Update save_to_drive() method
async def save_to_drive(
    self,
    file_data: bytes,
    folder_path: str
):
    if self.use_mock:
        return await self._mock_save_to_drive(file_data, folder_path)
    
    # Real Drive API integration
    url = f"{self.base_url}/api/v1/drive/upload"
    
    # Send presentation data to PresGen-Core for Drive upload
    async with aiohttp.ClientSession() as session:
        form = aiohttp.FormData()
        form.add_field('file', file_data, filename='presentation.pptx')
        form.add_field('folder_path', folder_path)
        
        async with session.post(url, data=form) as response:
            if response.status != 200:
                raise Exception(f"Drive upload failed: {response.status}")
            
            result = await response.json()
            return DriveUploadResult(
                file_id=result['file_id'],
                folder_id=result['folder_id'],
                download_url=result['download_url'],
                file_size_mb=result['file_size_mb']
            )
Add proper error handling
class PresGenCoreAPIError(Exception):
    """PresGen-Core API error"""
    pass

class PresGenCoreTimeoutError(Exception):
    """PresGen-Core request timeout"""
    pass

# Use in methods:
try:
    result = await self.generate_presentation(content_spec)
except asyncio.TimeoutError:
    raise PresGenCoreTimeoutError("Presentation generation timed out after 10 minutes")
except aiohttp.ClientError as e:
    raise PresGenCoreAPIError(f"API connection failed: {e}")
Phase 4: Update Timeouts (10 mins)
Files: .env, src/service/background_jobs.py
Adjust timeout settings
# In .env:
PRESENTATION_GENERATION_TIMEOUT_SECONDS=600  # 10 minutes per presentation
Update background job timeout handling
# In background_jobs.py execute() method:
try:
    # Step 2: Call PresGen-Core API (20-80%)
    await self._update_progress(20, "Generating slides")
    
    # Add timeout wrapper
    presentation_result = await asyncio.wait_for(
        self.presgen_client.generate_presentation(
            self.content_spec,
            progress_callback=self._presgen_progress_callback
        ),
        timeout=600  # 10 minutes
    )
except asyncio.TimeoutError:
    logger.error(f"❌ Presentation generation timed out after 10 minutes")
    raise Exception("Presentation generation exceeded maximum time limit")
Phase 5: Testing Strategy (60 mins)
Test 1: Single Presentation Generation
# Use a simple skill to test
curl -X POST "http://localhost:8000/api/v1/workflows/8e46398dc2924439a04531dfeb49d7ef/courses/220f8b53c7b242a88eeb5f7ae08aff84/generate-presentation" \
  -H "Content-Type: application/json" \
  -d '{
    "workflow_id": "8e46398dc2924439a04531dfeb49d7ef",
    "course_id": "220f8b53c7b242a88eeb5f7ae08aff84",
    "custom_title": "AWS Networking Fundamentals - Production Test"
  }'

# Monitor progress
watch -n 5 'sqlite3 test_database.db "SELECT skill_name, generation_status, job_progress FROM generated_presentations ORDER BY created_at DESC LIMIT 1;"'
Test 2: Verify Google Slides Creation
# After completion, check the presentation URL
sqlite3 test_database.db "SELECT presentation_url, drive_file_id FROM generated_presentations WHERE generation_status = 'completed' ORDER BY created_at DESC LIMIT 1;"

# Open in browser to verify it's a real Google Slides document
Test 3: Measure Generation Time
# Check actual duration
sqlite3 test_database.db "SELECT skill_name, generation_duration_ms / 1000.0 as duration_seconds FROM generated_presentations WHERE generation_status = 'completed' ORDER BY created_at DESC LIMIT 1;"

# Expected: 180-420 seconds (3-7 minutes)
Test 4: Drive Folder Organization
# Verify folder structure in Google Drive
# Navigate to: Google Drive > Assessments > [assessment_title]_[workflow_id] > Presentations
# Confirm folder exists and presentation is inside
Test 5: Error Handling
# Test with invalid data to verify error handling
curl -X POST "http://localhost:8000/api/v1/workflows/8e46398dc2924439a04531dfeb49d7ef/courses/220f8b53c7b242a88eeb5f7ae08aff84/generate-presentation" \
  -H "Content-Type: application/json" \
  -d '{
    "workflow_id": "8e46398dc2924439a04531dfeb49d7ef",
    "course_id": "220f8b53c7b242a88eeb5f7ae08aff84",
    "custom_title": ""
  }'

# Verify proper error message returned
Phase 6: Monitoring & Logging (15 mins)
Add enhanced logging
# In presgen_core_client.py:
logger.info(f"🎨 Calling PresGen-Core API | url={url}")
logger.info(f"📊 Presentation request | skill={content_spec.skill_name} | slides=7-11")

start_time = time.time()
result = await self._call_api(payload)
duration = time.time() - start_time

logger.info(f"✅ PresGen-Core completed | duration={duration:.1f}s | slides={result.slide_count}")
Monitor server logs
# Watch for errors during generation
tail -f logs/presgen_assess.log | grep -E "(ERROR|PresGen|generation)"
Phase 7: Rollback Plan (5 mins)
If production mode fails:
# Quick rollback - set mock mode back
self.use_mock = True  # Revert to mock mode

# Or via environment
DEBUG=true  # If using settings.debug approach
Success Criteria
✅ Real Google Slides presentations created
✅ Presentations accessible via URLs in database
✅ Drive folder structure matches design
✅ Generation time: 3-7 minutes per presentation
✅ No timeout errors for normal presentations
✅ Error handling works for API failures
✅ All existing mock-mode tests still pass
Estimated Time
Total: 2-3 hours (including testing and troubleshooting)
Dependencies
PresGen-Core service must be running and healthy
Google Cloud credentials valid and authorized
Network connectivity to Google APIs
Sufficient Google Drive storage quota
Risks & Mitigations
Risk	Impact	Mitigation
PresGen-Core API down	High	Check health endpoint first; keep mock mode as fallback
Google API quota exceeded	High	Implement rate limiting; monitor quota usage
Timeout on large presentations	Medium	Increase timeout to 10 mins; add retry logic
Invalid OAuth token	High	Add token refresh logic; verify credentials before generation
Network issues	Medium	Add retry with exponential backoff
Option 2: Avatar Generation Integration 🎥
Overview
Add AI avatar video generation to presentations using PresGen-Avatar service on port 8002. Each presentation gets an accompanying video with an AI presenter.
Prerequisites
PresGen-Avatar service running on http://localhost:8002
Option 1 (Production PresGen-Core) completed
Extended timeout support (avatar generation: 10-15 minutes)
Video storage in Google Drive
Architecture Changes
Current Flow:
Assessment → Gap Analysis → Content Outline → Presentation Generation
New Flow:
Assessment → Gap Analysis → Content Outline → Presentation Generation → Avatar Video Generation
Implementation Steps
Phase 1: Database Schema Updates (30 mins)
File: alembic/versions/XXX_add_avatar_generation.py
Create migration
cd /Users/yitzchak/Documents/learn/presentation_project/sales-agent-labs/presgen-assess
alembic revision -m "add_avatar_generation_support"
Add avatar fields to generated_presentations
def upgrade():
    op.add_column('generated_presentations', sa.Column('avatar_video_url', sa.Text(), nullable=True))
    op.add_column('generated_presentations', sa.Column('avatar_video_file_id', sa.String(255), nullable=True))
    op.add_column('generated_presentations', sa.Column('avatar_generation_status', sa.String(50), default='not_started', nullable=False))
    op.add_column('generated_presentations', sa.Column('avatar_generation_started_at', sa.DateTime(), nullable=True))
    op.add_column('generated_presentations', sa.Column('avatar_generation_completed_at', sa.DateTime(), nullable=True))
    op.add_column('generated_presentations', sa.Column('avatar_generation_duration_ms', sa.Integer(), nullable=True))
    op.add_column('generated_presentations', sa.Column('avatar_job_id', sa.String(36), nullable=True))
    op.add_column('generated_presentations', sa.Column('avatar_job_progress', sa.Integer(), default=0, nullable=False))
    op.add_column('generated_presentations', sa.Column('avatar_error_message', sa.Text(), nullable=True))
    op.add_column('generated_presentations', sa.Column('video_duration_seconds', sa.Integer(), nullable=True))
    op.add_column('generated_presentations', sa.Column('video_file_size_mb', sa.Float(), nullable=True))
    
    # Add constraint for avatar status
    op.create_check_constraint(
        'check_avatar_generation_status',
        'generated_presentations',
        "avatar_generation_status IN ('not_started', 'pending', 'generating', 'completed', 'failed', 'skipped')"
    )
    
    # Add index for avatar job tracking
    op.create_index('idx_presentations_avatar_status', 'generated_presentations', ['avatar_generation_status'])

def downgrade():
    op.drop_index('idx_presentations_avatar_status')
    op.drop_constraint('check_avatar_generation_status', 'generated_presentations')
    op.drop_column('generated_presentations', 'video_file_size_mb')
    op.drop_column('generated_presentations', 'video_duration_seconds')
    op.drop_column('generated_presentations', 'avatar_error_message')
    op.drop_column('generated_presentations', 'avatar_job_progress')
    op.drop_column('generated_presentations', 'avatar_job_id')
    op.drop_column('generated_presentations', 'avatar_generation_duration_ms')
    op.drop_column('generated_presentations', 'avatar_generation_completed_at')
    op.drop_column('generated_presentations', 'avatar_generation_started_at')
    op.drop_column('generated_presentations', 'avatar_generation_status')
    op.drop_column('generated_presentations', 'avatar_video_file_id')
    op.drop_column('generated_presentations', 'avatar_video_url')
Run migration
alembic upgrade head
Update model
# In src/models/presentation.py:
class GeneratedPresentation(Base):
    # ... existing fields ...
    
    # Avatar generation fields
    avatar_video_url = Column(Text, nullable=True)
    avatar_video_file_id = Column(String(255), nullable=True)
    avatar_generation_status = Column(String(50), default='not_started', nullable=False)
    avatar_generation_started_at = Column(DateTime, nullable=True)
    avatar_generation_completed_at = Column(DateTime, nullable=True)
    avatar_generation_duration_ms = Column(Integer, nullable=True)
    avatar_job_id = Column(String(36), nullable=True)
    avatar_job_progress = Column(Integer, default=0, nullable=False)
    avatar_error_message = Column(Text, nullable=True)
    video_duration_seconds = Column(Integer, nullable=True)
    video_file_size_mb = Column(Float, nullable=True)
Phase 2: PresGen-Avatar Client (90 mins)
File: src/service/presgen_avatar_client.py (NEW)
Create client class
"""PresGen-Avatar API Client for AI avatar video generation."""

import logging
import asyncio
from typing import Optional, Callable
from dataclasses import dataclass

import aiohttp

from src.common.config import settings

logger = logging.getLogger(__name__)


@dataclass
class AvatarGenerationResult:
    """Result from avatar generation."""
    video_url: str
    video_file_id: str
    video_duration_seconds: int
    thumbnail_url: str
    file_size_mb: float


@dataclass
class AvatarContentSpec:
    """Content specification for avatar video generation."""
    presentation_id: str
    presentation_url: str
    presentation_title: str
    skill_name: str
    slide_count: int
    script_content: Optional[str] = None  # Optional pre-generated script


class PresGenAvatarClient:
    """
    Client for PresGen-Avatar service.
    
    Generates AI avatar videos from presentations.
    """
    
    def __init__(self):
        self.base_url = settings.presgen_avatar_url
        self.timeout = settings.avatar_generation_timeout_seconds
        self.use_mock = settings.debug  # Mock in debug mode
        
    async def generate_avatar_video(
        self,
        content_spec: AvatarContentSpec,
        progress_callback: Optional[Callable] = None
    ) -> AvatarGenerationResult:
        """
        Generate AI avatar video for a presentation.
        
        Args:
            content_spec: Avatar content specification
            progress_callback: Optional callback for progress updates (0-100%)
        
        Returns:
            AvatarGenerationResult with video URLs and metadata
        """
        if self.use_mock:
            return await self._mock_generate_avatar(content_spec, progress_callback)
        
        logger.info(
            f"🎥 Generating avatar video | "
            f"presentation={content_spec.presentation_id} | "
            f"slides={content_spec.slide_count}"
        )
        
        url = f"{self.base_url}/api/v1/avatars/generate"
        
        payload = {
            "presentation_id": content_spec.presentation_id,
            "presentation_url": content_spec.presentation_url,
            "title": content_spec.presentation_title,
            "skill_name": content_spec.skill_name,
            "slide_count": content_spec.slide_count,
            "script_content": content_spec.script_content,
            "config": {
                "avatar_type": "professional",
                "voice_type": "neutral",
                "video_quality": "hd",
                "include_subtitles": True
            }
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=self.timeout)
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        raise Exception(f"PresGen-Avatar API error: {response.status} - {error_text}")
                    
                    result = await response.json()
                    
                    # Poll for completion if async
                    if result.get('job_id'):
                        return await self._poll_avatar_job(
                            result['job_id'],
                            session,
                            progress_callback
                        )
                    
                    return AvatarGenerationResult(
                        video_url=result['video_url'],
                        video_file_id=result['video_file_id'],
                        video_duration_seconds=result['video_duration_seconds'],
                        thumbnail_url=result['thumbnail_url'],
                        file_size_mb=result['file_size_mb']
                    )
        
        except asyncio.TimeoutError:
            logger.error(f"❌ Avatar generation timed out after {self.timeout}s")
            raise
        except Exception as e:
            logger.error(f"❌ Avatar generation failed: {e}")
            raise
    
    async def _poll_avatar_job(
        self,
        job_id: str,
        session: aiohttp.ClientSession,
        progress_callback: Optional[Callable] = None
    ) -> AvatarGenerationResult:
        """Poll avatar generation job until complete."""
        url = f"{self.base_url}/api/v1/avatars/jobs/{job_id}"
        
        while True:
            await asyncio.sleep(10)  # Poll every 10 seconds
            
            async with session.get(url) as response:
                if response.status != 200:
                    raise Exception(f"Job status check failed: {response.status}")
                
                result = await response.json()
                status = result['status']
                progress = result.get('progress', 0)
                
                if progress_callback:
                    await progress_callback(progress, result.get('current_step', ''))
                
                if status == 'completed':
                    return AvatarGenerationResult(
                        video_url=result['video_url'],
                        video_file_id=result['video_file_id'],
                        video_duration_seconds=result['video_duration_seconds'],
                        thumbnail_url=result['thumbnail_url'],
                        file_size_mb=result['file_size_mb']
                    )
                elif status == 'failed':
                    raise Exception(f"Avatar generation failed: {result.get('error_message')}")
    
    async def _mock_generate_avatar(
        self,
        content_spec: AvatarContentSpec,
        progress_callback: Optional[Callable] = None
    ) -> AvatarGenerationResult:
        """Mock avatar generation for testing."""
        logger.info(f"🎭 Mock avatar generation | presentation={content_spec.presentation_id}")
        
        # Simulate progress
        steps = [
            (20, "Analyzing presentation content"),
            (40, "Generating video script"),
            (60, "Creating avatar video"),
            (80, "Adding voiceover"),
            (90, "Rendering final video"),
            (100, "Complete")
        ]
        
        for progress, step in steps:
            if progress_callback:
                await progress_callback(progress, step)
            await asyncio.sleep(0.2)  # Simulate work
        
        # Return mock result
        return AvatarGenerationResult(
            video_url=f"https://drive.google.com/file/d/mock-avatar-{content_spec.presentation_id[:8]}/view",
            video_file_id=f"mock-avatar-{content_spec.presentation_id[:8]}",
            video_duration_seconds=content_spec.slide_count * 45,  # ~45s per slide
            thumbnail_url=f"https://drive.google.com/thumbnail/mock-avatar-{content_spec.presentation_id[:8]}",
            file_size_mb=content_spec.slide_count * 5.5  # ~5.5MB per slide
        )
Phase 3: Avatar Background Jobs (60 mins)
File: src/service/background_jobs.py
Add AvatarGenerationJob class
class AvatarGenerationJob:
    """
    Background job for generating avatar video.
    
    Runs after presentation generation completes.
    """
    
    def __init__(
        self,
        job_id: str,
        presentation_id: UUID,
        presentation_url: str,
        presentation_title: str,
        skill_name: str,
        slide_count: int
    ):
        self.job_id = job_id
        self.presentation_id = presentation_id
        self.avatar_client = PresGenAvatarClient()
        
        self.content_spec = AvatarContentSpec(
            presentation_id=str(presentation_id),
            presentation_url=presentation_url,
            presentation_title=presentation_title,
            skill_name=skill_name,
            slide_count=slide_count
        )
        
        self.progress = 0
        self.current_step = "Initializing"
        self.status = PresentationStatus.PENDING
    
    async def execute(self) -> None:
        """Execute avatar video generation."""
        async with AsyncSessionLocal() as session:
            self.db = session
            
            try:
                logger.info(f"🎥 Starting avatar generation job {self.job_id}")
                
                await self._update_status(PresentationStatus.GENERATING, 0, "Starting avatar generation")
                
                # Generate avatar video
                avatar_result = await self.avatar_client.generate_avatar_video(
                    self.content_spec,
                    progress_callback=self._avatar_progress_callback
                )
                
                # Update database
                await self._finalize_avatar(avatar_result)
                
                await self._update_status(PresentationStatus.COMPLETED, 100, "Avatar generation complete")
                
                logger.info(
                    f"✅ Avatar generation complete | "
                    f"job_id={self.job_id} | "
                    f"duration={avatar_result.video_duration_seconds}s"
                )
            
            except Exception as e:
                logger.error(f"❌ Avatar generation failed: {e}", exc_info=True)
                try:
                    await self._update_status(
                        PresentationStatus.FAILED,
                        self.progress,
                        f"Avatar generation failed: {str(e)}",
                        error_message=str(e)
                    )
                except Exception as update_error:
                    logger.error(f"❌ Failed to update error status: {update_error}")
                raise
            finally:
                self.db = None
                logger.debug(f"🔒 Database session closed for avatar job {self.job_id}")
    
    async def _update_status(
        self,
        status: PresentationStatus,
        progress: int,
        current_step: str,
        error_message: Optional[str] = None
    ) -> None:
        """Update avatar job status in database."""
        self.status = status
        self.progress = progress
        self.current_step = current_step
        
        update_values = {
            "avatar_generation_status": status.value,
            "avatar_job_progress": progress,
            "updated_at": datetime.utcnow()
        }
        
        if status == PresentationStatus.GENERATING and progress == 0:
            update_values["avatar_generation_started_at"] = datetime.utcnow()
        elif status in [PresentationStatus.COMPLETED, PresentationStatus.FAILED]:
            update_values["avatar_generation_completed_at"] = datetime.utcnow()
        
        if error_message:
            update_values["avatar_error_message"] = error_message
        
        stmt = update(GeneratedPresentation).where(
            GeneratedPresentation.id == str(self.presentation_id)
        ).values(**update_values)
        
        await self.db.execute(stmt)
        await self.db.commit()
    
    async def _avatar_progress_callback(self, progress: int, step: str) -> None:
        """Callback for avatar progress updates."""
        await self._update_status(self.status, progress, step)
    
    async def _finalize_avatar(self, avatar_result: AvatarGenerationResult) -> None:
        """Finalize avatar record in database."""
        
        # Calculate duration
        stmt = select(GeneratedPresentation.avatar_generation_started_at).where(
            GeneratedPresentation.id == str(self.presentation_id)
        )
        result = await self.db.execute(stmt)
        started_at_str = result.scalar_one()
        
        if started_at_str:
            started_at = datetime.fromisoformat(started_at_str) if isinstance(started_at_str, str) else started_at_str
            duration_ms = int((datetime.utcnow() - started_at).total_seconds() * 1000)
        else:
            duration_ms = 0
        
        update_stmt = update(GeneratedPresentation).where(
            GeneratedPresentation.id == str(self.presentation_id)
        ).values(
            avatar_video_url=avatar_result.video_url,
            avatar_video_file_id=avatar_result.video_file_id,
            video_duration_seconds=avatar_result.video_duration_seconds,
            video_file_size_mb=avatar_result.file_size_mb,
            avatar_generation_duration_ms=duration_ms
        )
        
        await self.db.execute(update_stmt)
        await self.db.commit()
Update PresentationGenerationJob to trigger avatar generation
# In PresentationGenerationJob.execute(), after presentation completes:

# Step 4: Update database (90-100%)
await self._update_progress(90, "Finalizing")
await self._finalize_presentation(presentation_result, drive_result, folder_path)

await self._update_status(PresentationStatus.COMPLETED, 100, "Generation complete")

# NEW: Check if avatar generation is enabled
if settings.enable_avatar_generation:
    logger.info(f"🎬 Triggering avatar generation for {self.presentation_id}")
    
    # Enqueue avatar generation job
    avatar_job_id = await job_queue.enqueue_avatar(
        presentation_id=self.presentation_id,
        presentation_url=presentation_result.presentation_url,
        presentation_title=self.content_spec.title,
        skill_name=self.content_spec.skill_name,
        slide_count=presentation_result.slide_count
    )
    
    # Update presentation with avatar job_id
    update_stmt = update(GeneratedPresentation).where(
        GeneratedPresentation.id == str(self.presentation_id)
    ).values(
        avatar_job_id=avatar_job_id,
        avatar_generation_status='pending'
    )
    await self.db.execute(update_stmt)
    await self.db.commit()
Add enqueue_avatar() to JobQueue
# In JobQueue class:

async def enqueue_avatar(
    self,
    presentation_id: UUID,
    presentation_url: str,
    presentation_title: str,
    skill_name: str,
    slide_count: int
) -> str:
    """Enqueue avatar generation job."""
    job_id = str(uuid4())
    
    job = AvatarGenerationJob(
        job_id=job_id,
        presentation_id=presentation_id,
        presentation_url=presentation_url,
        presentation_title=presentation_title,
        skill_name=skill_name,
        slide_count=slide_count
    )
    
    self.avatar_jobs[job_id] = job
    
    # Start job in background
    asyncio.create_task(job.execute())
    
    logger.info(
        f"🎥 Enqueued avatar generation job {job_id} | "
        f"skill={skill_name}"
    )
    
    return job_id
Phase 4: API Endpoints (30 mins)
File: src/service/api/v1/endpoints/presentations.py
Add avatar status endpoint
@router.get(
    "/workflows/{workflow_id}/presentations/{presentation_id}/avatar-status",
    response_model=AvatarJobStatus,
    summary="Get avatar generation status"
)
async def get_avatar_status(
    workflow_id: str,
    presentation_id: str,
    db: AsyncSession = Depends(get_db)
) -> AvatarJobStatus:
    """Get avatar generation status for a presentation."""
    
    presentation_id_normalized = presentation_id.replace('-', '')
    
    stmt = select(GeneratedPresentation).where(
        GeneratedPresentation.id == presentation_id_normalized
    )
    result = await db.execute(stmt)
    presentation = result.scalar_one_or_none()
    
    if not presentation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Presentation {presentation_id} not found"
        )
    
    return AvatarJobStatus(
        job_id=presentation.avatar_job_id,
        presentation_id=presentation.id,
        status=presentation.avatar_generation_status,
        progress=presentation.avatar_job_progress,
        video_url=presentation.avatar_video_url,
        video_duration_seconds=presentation.video_duration_seconds,
        error_message=presentation.avatar_error_message
    )
Update presentation response schema
# In src/schemas/presentation.py:

class GeneratedPresentation(BaseModel):
    # ... existing fields ...
    
    # Avatar fields
    avatar_video_url: Optional[str] = None
    avatar_video_file_id: Optional[str] = None
    avatar_generation_status: str = "not_started"
    avatar_job_id: Optional[str] = None
    avatar_job_progress: int = 0
    video_duration_seconds: Optional[int] = None
    video_file_size_mb: Optional[float] = None
Phase 5: Configuration (15 mins)
Files: .env, src/common/config.py
Add avatar settings to .env
# Avatar Generation
ENABLE_AVATAR_GENERATION=true
PRESGEN_AVATAR_URL=http://localhost:8002
PRESGEN_AVATAR_MAX_SLIDES=40
AVATAR_GENERATION_TIMEOUT_SECONDS=900  # 15 minutes
Update config.py
# In Settings class:

# Avatar Generation
enable_avatar_generation: bool = Field(default=False, alias="ENABLE_AVATAR_GENERATION")
presgen_avatar_url: str = Field(default="http://localhost:8002", alias="PRESGEN_AVATAR_URL")
presgen_avatar_max_slides: int = Field(default=40, alias="PRESGEN_AVATAR_MAX_SLIDES")
avatar_generation_timeout_seconds: int = Field(
    default=900, alias="AVATAR_GENERATION_TIMEOUT_SECONDS"
)
Phase 6: Testing Strategy (90 mins)
Test 1: Avatar Generation Workflow
# 1. Generate presentation
curl -X POST "http://localhost:8000/api/v1/workflows/8e46398dc2924439a04531dfeb49d7ef/courses/f060300480de4308831e35cc0a89e0b8/generate-presentation" \
  -H "Content-Type: application/json" \
  -d '{
    "workflow_id": "8e46398dc2924439a04531dfeb49d7ef",
    "course_id": "f060300480de4308831e35cc0a89e0b8"
  }'

# 2. Monitor presentation completion
watch -n 5 'sqlite3 test_database.db "SELECT generation_status, job_progress, avatar_generation_status, avatar_job_progress FROM generated_presentations ORDER BY created_at DESC LIMIT 1;"'

# Expected sequence:
# - generation_status: pending → generating → completed
# - avatar_generation_status: pending → generating → completed
Test 2: Verify Avatar Video
# Check avatar video fields
sqlite3 test_database.db "SELECT skill_name, avatar_video_url, video_duration_seconds, video_file_size_mb FROM generated_presentations WHERE avatar_generation_status = 'completed' ORDER BY created_at DESC LIMIT 1;"

# Open video URL to verify
Test 3: Check Generation Times
# Measure total time (presentation + avatar)
sqlite3 test_database.db "
SELECT 
    skill_name,
    generation_duration_ms / 1000.0 as pres_seconds,
    avatar_generation_duration_ms / 1000.0 as avatar_seconds,
    (generation_duration_ms + avatar_generation_duration_ms) / 1000.0 as total_seconds
FROM generated_presentations 
WHERE avatar_generation_status = 'completed' 
ORDER BY created_at DESC LIMIT 1;
"

# Expected: 5-10 mins presentation + 10-15 mins avatar = 15-25 mins total
Test 4: Avatar-Only Generation
# Test generating avatar for existing presentation
curl -X POST "http://localhost:8000/api/v1/presentations/{presentation_id}/generate-avatar" \
  -H "Content-Type: application/json"

# Monitor progress
curl "http://localhost:8000/api/v1/workflows/{workflow_id}/presentations/{presentation_id}/avatar-status"
Test 5: Error Handling
# Test with invalid presentation URL
# Verify avatar_generation_status = 'failed'
# Verify avatar_error_message populated
Success Criteria
✅ Avatar videos generated successfully
✅ Videos accessible via URLs in database
✅ Avatar generation runs after presentation completes
✅ Progress tracking works (0-100%)
✅ Generation time: 10-15 minutes per avatar
✅ Video duration: ~45 seconds per slide
✅ Error handling works for avatar failures
✅ Presentations work without avatars if disabled
Estimated Time
Total: 5-6 hours (including testing)
Dependencies
Option 1 (Production PresGen-Core) must be completed first
PresGen-Avatar service running on port 8002
Video storage quota in Google Drive
Extended timeout support for long-running jobs
Risks & Mitigations
Risk	Impact	Mitigation
Avatar generation timeout	High	Increase timeout to 15 mins; add checkpoint/resume
Large video file sizes	Medium	Implement compression; monitor Drive quota
PresGen-Avatar API issues	High	Make avatar generation optional; allow retry
Sequential processing slow	Medium	Consider parallel processing for batch jobs
Option 3: Fix API Endpoints 🔧
Overview
Fix UUID format inconsistencies in status and list endpoints that prevent them from returning correct data. Currently, endpoints return 404/empty results due to hyphen handling issues.
Root Cause Analysis
Problem: SQLite stores UUIDs as strings without hyphens (8e46398dc2924439a04531dfeb49d7ef), but:
API URLs accept both formats
FastAPI UUID parsing adds hyphens automatically
ORM queries fail when comparing UUID objects to string columns
Example:
# URL: /presentations/8e46398d-c292-4439-a045-31dfeb49d7ef/status
# FastAPI parses as UUID object
# SQLAlchemy tries: WHERE id = UUID('8e46398d-c292-4439-a045-31dfeb49d7ef')
# But SQLite has: id = '8e46398dc2924439a04531dfeb49d7ef' (string)
# Result: No match found
Implementation Steps
Phase 1: Status Endpoint Fix (15 mins)
File: src/service/api/v1/endpoints/presentations.py
Locate status endpoint (around line 300-350)
@router.get(
    "/workflows/{workflow_id}/presentations/{presentation_id}/status",
    response_model=PresentationJobStatus,
    summary="Get presentation generation status"
)
async def get_presentation_status(
    workflow_id: UUID,
    presentation_id: UUID,
    db: AsyncSession = Depends(get_db)
) -> PresentationJobStatus:
Change parameter types and normalize
@router.get(
    "/workflows/{workflow_id}/presentations/{presentation_id}/status",
    response_model=PresentationJobStatus,
    summary="Get presentation generation status"
)
async def get_presentation_status(
    workflow_id: str,  # Changed from UUID
    presentation_id: str,  # Changed from UUID
    db: AsyncSession = Depends(get_db)
) -> PresentationJobStatus:
    """
    Get presentation generation status.
    
    Returns progress (0-100%), current step, and completion status.
    """
    try:
        # Normalize IDs (remove hyphens for SQLite UUID comparison)
        presentation_id_normalized = presentation_id.replace('-', '')
        workflow_id_normalized = workflow_id.replace('-', '')
        
        logger.debug(
            f"📊 Status check | "
            f"workflow={workflow_id_normalized} | "
            f"presentation={presentation_id_normalized}"
        )
        
        # Query using raw SQL to avoid UUID type issues
        stmt = text("""
            SELECT 
                id, job_id, generation_status, job_progress,
                job_error_message, created_at, updated_at
            FROM generated_presentations 
            WHERE id = :presentation_id
            AND workflow_id = :workflow_id
        """)
        
        result = await db.execute(stmt, {
            "presentation_id": presentation_id_normalized,
            "workflow_id": workflow_id_normalized
        })
        row = result.fetchone()
        
        if not row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Presentation {presentation_id} not found"
            )
        
        # Map row to response
        return PresentationJobStatus(
            job_id=row[1],
            presentation_id=row[0],
            status=row[2],
            progress=row[3],
            current_step=f"Progress: {row[3]}%",
            error_message=row[4]
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Status check failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve status: {str(e)}"
        )
Phase 2: List Endpoint Fix (20 mins)
File: src/service/api/v1/endpoints/presentations.py
Locate list endpoint (around line 350-400)
@router.get(
    "/workflows/{workflow_id}/presentations",
    response_model=PresentationListResponse,
    summary="List all presentations for workflow"
)
async def list_presentations(
    workflow_id: UUID,
    db: AsyncSession = Depends(get_db)
) -> PresentationListResponse:
Fix query and normalization
@router.get(
    "/workflows/{workflow_id}/presentations",
    response_model=PresentationListResponse,
    summary="List all presentations for workflow"
)
async def list_presentations(
    workflow_id: str,  # Changed from UUID
    db: AsyncSession = Depends(get_db)
) -> PresentationListResponse:
    """
    List all presentations for a workflow.
    
    Returns presentations with counts by status.
    """
    try:
        # Normalize workflow_id
        workflow_id_normalized = workflow_id.replace('-', '')
        
        logger.info(f"📋 List presentations | workflow={workflow_id_normalized}")
        
        # Query using raw SQL
        stmt = text("""
            SELECT * FROM generated_presentations 
            WHERE workflow_id = :workflow_id
            ORDER BY created_at DESC
        """)
        
        result = await db.execute(stmt, {"workflow_id": workflow_id_normalized})
        rows = result.fetchall()
        
        if not rows:
            logger.info(f"  No presentations found for workflow {workflow_id_normalized}")
            return PresentationListResponse(
                workflow_id=workflow_id,
                presentations=[],
                total_count=0,
                completed_count=0,
                pending_count=0,
                generating_count=0,
                failed_count=0
            )
        
        # Convert rows to presentation objects
        presentations = []
        completed_count = 0
        pending_count = 0
        generating_count = 0
        failed_count = 0
        
        for row in rows:
            # Map row columns to GeneratedPresentationSchema
            pres = GeneratedPresentationSchema(
                id=row[0],  # id
                workflow_id=row[2],  # workflow_id
                skill_id=row[3],  # skill_id
                skill_name=row[4],  # skill_name
                course_id=row[5],  # course_id
                assessment_title=row[6],  # assessment_title
                user_email=row[7],  # user_email
                drive_folder_path=row[8],  # drive_folder_path
                presentation_title=row[9],  # presentation_title
                presentation_url=row[10],  # presentation_url
                download_url=row[11],  # download_url
                drive_file_id=row[12],  # drive_file_id
                drive_folder_id=row[13],  # drive_folder_id
                generation_status=row[14],  # generation_status
                generation_started_at=row[15],  # generation_started_at
                generation_completed_at=row[16],  # generation_completed_at
                generation_duration_ms=row[17],  # generation_duration_ms
                estimated_duration_minutes=row[18],  # estimated_duration_minutes
                job_id=row[19],  # job_id
                job_progress=row[20],  # job_progress
                job_error_message=row[21],  # job_error_message
                template_id=row[22],  # template_id
                template_name=row[23],  # template_name
                total_slides=row[24],  # total_slides
                content_outline_id=row[25],  # content_outline_id
                file_size_mb=row[26],  # file_size_mb
                thumbnail_url=row[27],  # thumbnail_url
                created_at=row[28],  # created_at
                updated_at=row[29]  # updated_at
            )
            
            presentations.append(pres)
            
            # Count by status
            if row[14] == 'completed':
                completed_count += 1
            elif row[14] == 'pending':
                pending_count += 1
            elif row[14] == 'generating':
                generating_count += 1
            elif row[14] == 'failed':
                failed_count += 1
        
        logger.info(
            f"  Found {len(presentations)} presentations | "
            f"completed={completed_count} | "
            f"pending={pending_count} | "
            f"generating={generating_count} | "
            f"failed={failed_count}"
        )
        
        return PresentationListResponse(
            workflow_id=workflow_id,
            presentations=presentations,
            total_count=len(presentations),
            completed_count=completed_count,
            pending_count=pending_count,
            generating_count=generating_count,
            failed_count=failed_count
        )
    
    except Exception as e:
        logger.error(f"❌ List presentations failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list presentations: {str(e)}"
        )
Phase 3: Single Presentation GET Endpoint (15 mins)
File: src/service/api/v1/endpoints/presentations.py
Add new endpoint to get single presentation details
@router.get(
    "/workflows/{workflow_id}/presentations/{presentation_id}",
    response_model=GeneratedPresentationSchema,
    summary="Get presentation details"
)
async def get_presentation(
    workflow_id: str,
    presentation_id: str,
    db: AsyncSession = Depends(get_db)
) -> GeneratedPresentationSchema:
    """
    Get detailed information about a specific presentation.
    
    Returns all presentation fields including URLs, status, and metadata.
    """
    try:
        # Normalize IDs
        presentation_id_normalized = presentation_id.replace('-', '')
        workflow_id_normalized = workflow_id.replace('-', '')
        
        logger.debug(
            f"📄 Get presentation | "
            f"presentation={presentation_id_normalized}"
        )
        
        # Query using raw SQL
        stmt = text("""
            SELECT * FROM generated_presentations 
            WHERE id = :presentation_id
            AND workflow_id = :workflow_id
        """)
        
        result = await db.execute(stmt, {
            "presentation_id": presentation_id_normalized,
            "workflow_id": workflow_id_normalized
        })
        row = result.fetchone()
        
        if not row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Presentation {presentation_id} not found"
            )
        
        # Map row to response schema (same as list endpoint)
        return GeneratedPresentationSchema(
            id=row[0],
            workflow_id=row[2],
            skill_id=row[3],
            skill_name=row[4],
            course_id=row[5],
            assessment_title=row[6],
            user_email=row[7],
            drive_folder_path=row[8],
            presentation_title=row[9],
            presentation_url=row[10],
            download_url=row[11],
            drive_file_id=row[12],
            drive_folder_id=row[13],
            generation_status=row[14],
            generation_started_at=row[15],
            generation_completed_at=row[16],
            generation_duration_ms=row[17],
            estimated_duration_minutes=row[18],
            job_id=row[19],
            job_progress=row[20],
            job_error_message=row[21],
            template_id=row[22],
            template_name=row[23],
            total_slides=row[24],
            content_outline_id=row[25],
            file_size_mb=row[26],
            thumbnail_url=row[27],
            created_at=row[28],
            updated_at=row[29]
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Get presentation failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve presentation: {str(e)}"
        )
Phase 4: Add Helper Function (10 mins)
File: src/service/api/v1/endpoints/presentations.py
Add UUID normalization helper at top of file
def normalize_uuid(uuid_str: str) -> str:
    """
    Normalize UUID string by removing hyphens.
    
    SQLite stores UUIDs as strings without hyphens.
    This function ensures consistent format for queries.
    
    Args:
        uuid_str: UUID string with or without hyphens
    
    Returns:
        UUID string without hyphens
    """
    return uuid_str.replace('-', '')
Use helper throughout file
# Replace all instances of:
presentation_id.replace('-', '')
workflow_id.replace('-', '')
course_id.replace('-', '')

# With:
normalize_uuid(presentation_id)
normalize_uuid(workflow_id)
normalize_uuid(course_id)
Phase 5: Testing Strategy (30 mins)
Test 1: Status Endpoint
# Get a completed presentation ID
PRES_ID=$(sqlite3 test_database.db "SELECT id FROM generated_presentations WHERE generation_status = 'completed' LIMIT 1;")

# Test status endpoint (without hyphens)
curl "http://localhost:8000/api/v1/workflows/8e46398dc2924439a04531dfeb49d7ef/presentations/${PRES_ID}/status"

# Test with hyphens (add them manually)
PRES_ID_HYPHENS=$(echo $PRES_ID | sed 's/^\(........\)\(....\)\(....\)\(....\)\(............\)$/\1-\2-\3-\4-\5/')
curl "http://localhost:8000/api/v1/workflows/8e46398d-c292-4439-a045-31dfeb49d7ef/presentations/${PRES_ID_HYPHENS}/status"

# Both should return valid status
Test 2: List Endpoint
# Test without hyphens
curl "http://localhost:8000/api/v1/workflows/8e46398dc2924439a04531dfeb49d7ef/presentations" | python3 -m json.tool

# Test with hyphens
curl "http://localhost:8000/api/v1/workflows/8e46398d-c292-4439-a045-31dfeb49d7ef/presentations" | python3 -m json.tool

# Both should return presentation list with counts
Test 3: Get Single Presentation
# Get presentation details
curl "http://localhost:8000/api/v1/workflows/8e46398d-c292-4439-a045-31dfeb49d7ef/presentations/${PRES_ID_HYPHENS}" | python3 -m json.tool

# Verify all fields populated
Test 4: Verify Sprint 3 Test Cases
# Re-run Sprint 3 test cases 1, 2, 7 from manual testing guide
# All should now pass completely
Test 5: API Documentation
# Open Swagger UI
open http://localhost:8000/docs

# Test endpoints through UI
# Verify UUID format flexibility
Phase 6: Update API Documentation (10 mins)
File: src/service/api/v1/endpoints/presentations.py
Add docstring notes about UUID handling
"""
Presentation Generation API Endpoints

UUID Handling:
- All UUID parameters accept both formats (with or without hyphens)
- Examples: 
  - 8e46398dc2924439a04531dfeb49d7ef (no hyphens)
  - 8e46398d-c292-4439-a045-31dfeb49d7ef (with hyphens)
- Internally normalized to no-hyphen format for SQLite compatibility
"""
Update endpoint descriptions
@router.get(
    "/workflows/{workflow_id}/presentations/{presentation_id}/status",
    response_model=PresentationJobStatus,
    summary="Get presentation generation status",
    description="""
    Get real-time status of presentation generation.
    
    **UUID Format**: Accepts both hyphenated and non-hyphenated UUID formats.
    
    **Returns**:
    - job_id: Background job identifier
    - status: pending | generating | completed | failed
    - progress: 0-100%
    - current_step: Human-readable progress description
    - error_message: Error details if failed
    """
)
Success Criteria
✅ Status endpoint returns correct data for all presentations
✅ List endpoint returns all presentations with accurate counts
✅ Both UUID formats (with/without hyphens) work correctly
✅ All Sprint 3 test cases pass completely
✅ API documentation updated and accurate
✅ No 404 errors for valid presentation IDs
✅ Error handling works for invalid IDs
Estimated Time
Total: 1.5-2 hours (including testing)
Benefits
Immediate Value: Sprint 3 fully functional
User Experience: Endpoints work as expected
Testing: Can validate all Sprint 3 functionality
Foundation: Clean APIs for Sprint 4
Documentation: Clear UUID handling for frontend
Rollback Plan
If fixes cause issues:
# Revert changes
git checkout src/service/api/v1/endpoints/presentations.py

# Restart server
# Previous behavior restored
Option 5: End-to-End Workflow Testing 🔄
Overview
Test the complete flow from assessment creation through presentation generation to validate the entire system works as an integrated workflow.
Prerequisites
Sprint 3 completed and working
Option 3 (API endpoint fixes) completed
Clean test environment (or ability to create new workflows)
Workflow Stages
Stage 1: Assessment Creation
    ↓
Stage 2: Gap Analysis Execution
    ↓
Stage 3: Course Recommendations
    ↓
Stage 4: Content Outline Generation
    ↓
Stage 5: Presentation Generation (Sprint 3)
    ↓
Stage 6: Result Verification
Implementation Steps
Phase 1: Test Data Preparation (30 mins)
Create test assessment specification
{
  "assessment_title": "AWS Solutions Architect Associate - E2E Test",
  "user_email": "test@example.com",
  "assessment_type": "gap_analysis",
  "domain": "AWS Cloud Computing",
  "difficulty_level": "intermediate",
  "questions": [
    {
      "question_id": "q1",
      "question_text": "What is Amazon EC2?",
      "domain": "Compute",
      "subdomain": "EC2 Fundamentals",
      "user_answer": "A virtual server in the cloud",
      "correct_answer": "A scalable compute capacity service",
      "is_correct": true,
      "time_spent_seconds": 45
    },
    {
      "question_id": "q2",
      "question_text": "What is Amazon S3 used for?",
      "domain": "Storage",
      "subdomain": "Object Storage",
      "user_answer": "Database storage",
      "correct_answer": "Object storage service",
      "is_correct": false,
      "time_spent_seconds": 30
    },
    {
      "question_id": "q3",
      "question_text": "What is Amazon VPC?",
      "domain": "Networking",
      "subdomain": "VPC Fundamentals",
      "user_answer": "Virtual Private Cloud for network isolation",
      "correct_answer": "Isolated cloud network",
      "is_correct": true,
      "time_spent_seconds": 60
    },
    {
      "question_id": "q4",
      "question_text": "What does IAM stand for?",
      "domain": "Security",
      "subdomain": "Access Management",
      "user_answer": "Don't know",
      "correct_answer": "Identity and Access Management",
      "is_correct": false,
      "time_spent_seconds": 15
    },
    {
      "question_id": "q5",
      "question_text": "What is Amazon RDS?",
      "domain": "Database",
      "subdomain": "Relational Databases",
      "user_answer": "Relational Database Service",
      "correct_answer": "Managed relational database service",
      "is_correct": true,
      "time_spent_seconds": 50
    }
  ]
}
Save test data
# Create test data file
cat > /tmp/e2e_test_assessment.json << 'EOF'
{
  "assessment_title": "AWS Solutions Architect Associate - E2E Test",
  "user_email": "test@example.com",
  ...
}
EOF
Phase 2: Stage 1 - Assessment Creation (15 mins)
Objective: Create new assessment and verify workflow initialization
Create assessment via API
# Assuming you have an assessment creation endpoint
curl -X POST "http://localhost:8000/api/v1/assessments" \
  -H "Content-Type: application/json" \
  -d @/tmp/e2e_test_assessment.json \
  > /tmp/e2e_assessment_response.json

# Extract workflow_id
WORKFLOW_ID=$(cat /tmp/e2e_assessment_response.json | python3 -c "import json, sys; print(json.load(sys.stdin)['workflow_id'])")

echo "Created workflow: $WORKFLOW_ID"
Verify database state
# Check workflow_executions table
sqlite3 test_database.db "SELECT id, status, created_at FROM workflow_executions WHERE id = '$WORKFLOW_ID';"

# Expected: workflow exists with 'pending' or 'initialized' status
Validation checklist
# ✅ Workflow record created
# ✅ Status is 'pending' or 'initialized'
# ✅ assessment_data JSON populated with questions
# ✅ Timestamps set correctly
Phase 3: Stage 2 - Gap Analysis Execution (30 mins)
Objective: Analyze assessment responses and identify skill gaps
Trigger gap analysis
# Execute gap analysis for workflow
curl -X POST "http://localhost:8000/api/v1/workflows/$WORKFLOW_ID/execute-gap-analysis" \
  -H "Content-Type: application/json" \
  > /tmp/e2e_gap_analysis_response.json
Monitor execution
# Poll workflow status
for i in {1..10}; do
  echo "=== Check $i ==="
  curl -s "http://localhost:8000/api/v1/workflows/$WORKFLOW_ID/status" | python3 -m json.tool
  sleep 3
done
Verify gap analysis results
# Check gap_analysis table
sqlite3 test_database.db "SELECT skill_id, skill_name, score_percentage, gap_severity FROM gap_analysis WHERE workflow_id = '$WORKFLOW_ID';"

# Expected output (based on test data):
# compute|EC2 Fundamentals|100.0|none
# storage|Object Storage|0.0|critical
# networking|VPC Fundamentals|100.0|none
# security|Access Management|0.0|critical
# database|Relational Databases|100.0|none
Validation checklist
# ✅ Gap analysis records created (one per skill/domain)
# ✅ Scores calculated correctly (100% for correct, 0% for incorrect)
# ✅ Gap severity assigned (none/minor/moderate/critical)
# ✅ Workflow status updated to 'gap_analysis_complete'
Phase 4: Stage 3 - Course Recommendations (30 mins)
Objective: Generate personalized course recommendations for identified gaps
Trigger course recommendation
# Generate recommendations
curl -X POST "http://localhost:8000/api/v1/workflows/$WORKFLOW_ID/recommend-courses" \
  -H "Content-Type: application/json" \
  > /tmp/e2e_courses_response.json
Verify recommended courses
# Check recommended_courses table
sqlite3 test_database.db "SELECT skill_id, skill_name, course_title, difficulty_level, estimated_duration_minutes FROM recommended_courses WHERE workflow_id = '$WORKFLOW_ID';"

# Expected: Courses recommended for gaps (Storage, Security)
# Should have 2-5 courses total
Check course details
# Get detailed course info
sqlite3 test_database.db "SELECT id, skill_name, learning_objectives FROM recommended_courses WHERE workflow_id = '$WORKFLOW_ID' LIMIT 2;"

# Verify learning objectives are relevant to gaps
Validation checklist
# ✅ Courses recommended for critical/high gaps
# ✅ Course titles relevant to skill gaps
# ✅ Difficulty appropriate (intermediate level)
# ✅ Learning objectives specific to gaps
# ✅ Estimated duration reasonable (30-60 mins per course)
Phase 5: Stage 4 - Content Outline Generation (45 mins)
Objective: Generate detailed content outlines for each recommended course
Trigger content outline generation
# Generate outlines for all courses
curl -X POST "http://localhost:8000/api/v1/workflows/$WORKFLOW_ID/generate-content-outlines" \
  -H "Content-Type: application/json" \
  > /tmp/e2e_outlines_response.json
Monitor progress
# Check outline generation status
watch -n 5 'sqlite3 test_database.db "SELECT skill_name, generation_status FROM content_outlines WHERE workflow_id = '\'$WORKFLOW_ID\'' ORDER BY created_at DESC;"'
Verify content outlines
# Get outline summaries
sqlite3 test_database.db "
SELECT 
    skill_name, 
    total_sections,
    estimated_duration_minutes,
    generation_status
FROM content_outlines 
WHERE workflow_id = '$WORKFLOW_ID';
"

# Expected: One outline per course, 5-7 sections each
Inspect outline details
# Get first outline's full structure
OUTLINE_ID=$(sqlite3 test_database.db "SELECT id FROM content_outlines WHERE workflow_id = '$WORKFLOW_ID' LIMIT 1;")

sqlite3 test_database.db "SELECT outline_json FROM content_outlines WHERE id = '$OUTLINE_ID';" | python3 -m json.tool | head -50

# Verify:
# ✅ Sections have titles and descriptions
# ✅ Topics are specific and relevant
# ✅ Learning objectives clear
# ✅ Examples/exercises included
Validation checklist
# ✅ Content outlines generated for all courses
# ✅ Each outline has 5-7 sections
# ✅ Sections logically ordered (basics → advanced)
# ✅ Topics relevant to skill gaps
# ✅ Duration estimates reasonable
# ✅ outline_json well-structured
Phase 6: Stage 5 - Presentation Generation (60 mins)
Objective: Generate presentations for all courses using Sprint 3 functionality
Get course IDs
# List all courses for workflow
sqlite3 test_database.db "SELECT id, skill_name FROM recommended_courses WHERE workflow_id = '$WORKFLOW_ID';"

# Save IDs to array
COURSE_IDS=($(sqlite3 test_database.db "SELECT id FROM recommended_courses WHERE workflow_id = '$WORKFLOW_ID';"))
echo "Found ${#COURSE_IDS[@]} courses"
Option A: Batch generation (recommended)
# Generate all presentations at once
curl -X POST "http://localhost:8000/api/v1/workflows/$WORKFLOW_ID/generate-all-presentations" \
  -H "Content-Type: application/json" \
  -d "{
    \"workflow_id\": \"$WORKFLOW_ID\",
    \"max_concurrent\": 3
  }" \
  > /tmp/e2e_batch_generation_response.json

# Extract job IDs
cat /tmp/e2e_batch_generation_response.json | python3 -c "
import json, sys
data = json.load(sys.stdin)
for job in data['jobs']:
    print(f\"Job: {job['job_id']} - {job['skill_name']}\")
"
Option B: Individual generation
# Generate presentations one by one
for course_id in "${COURSE_IDS[@]}"; do
  echo "Generating presentation for course: $course_id"
  
  curl -X POST "http://localhost:8000/api/v1/workflows/$WORKFLOW_ID/courses/$course_id/generate-presentation" \
    -H "Content-Type: application/json" \
    -d "{
      \"workflow_id\": \"$WORKFLOW_ID\",
      \"course_id\": \"$course_id\"
    }"
  
  echo ""
  sleep 2
done
Monitor generation progress
# Real-time monitoring
watch -n 5 '
echo "=== Presentation Generation Progress ==="
sqlite3 test_database.db "
SELECT 
    skill_name,
    generation_status,
    job_progress,
    total_slides
FROM generated_presentations 
WHERE workflow_id = '\''$WORKFLOW_ID'\''
ORDER BY created_at DESC;
"
'
Wait for completion
# Poll until all complete
while true; do
  COMPLETED=$(sqlite3 test_database.db "SELECT COUNT(*) FROM generated_presentations WHERE workflow_id = '$WORKFLOW_ID' AND generation_status = 'completed';")
  TOTAL=$(sqlite3 test_database.db "SELECT COUNT(*) FROM generated_presentations WHERE workflow_id = '$WORKFLOW_ID';")
  
  echo "Progress: $COMPLETED / $TOTAL presentations completed"
  
  if [ "$COMPLETED" -eq "$TOTAL" ]; then
    echo "✅ All presentations complete!"
    break
  fi
  
  sleep 10
done
Validation checklist
# ✅ Presentations generated for all courses
# ✅ All statuses = 'completed'
# ✅ Job progress = 100%
# ✅ No failed presentations
# ✅ Presentation URLs populated
# ✅ Drive folder paths correct
# ✅ Slide counts reasonable (7-11 per presentation)
Phase 7: Stage 6 - Result Verification (45 mins)
Objective: Verify end-to-end workflow results and data consistency
Summary statistics
# Generate workflow summary
sqlite3 test_database.db "
SELECT 
    'Assessment Questions' as metric,
    COUNT(*) as count
FROM json_each((SELECT assessment_data FROM workflow_executions WHERE id = '$WORKFLOW_ID'), '\$.questions')
UNION ALL
SELECT 
    'Skill Gaps Identified',
    COUNT(*)
FROM gap_analysis 
WHERE workflow_id = '$WORKFLOW_ID'
UNION ALL
SELECT 
    'Courses Recommended',
    COUNT(*)
FROM recommended_courses
WHERE workflow_id = '$WORKFLOW_ID'
UNION ALL
SELECT 
    'Content Outlines Generated',
    COUNT(*)
FROM content_outlines
WHERE workflow_id = '$WORKFLOW_ID'
UNION ALL
SELECT 
    'Presentations Generated',
    COUNT(*)
FROM generated_presentations
WHERE workflow_id = '$WORKFLOW_ID' AND generation_status = 'completed';
"
Data consistency checks
# Verify referential integrity

# Check 1: Every gap has a recommended course
sqlite3 test_database.db "
SELECT 
    ga.skill_id,
    ga.skill_name,
    COUNT(rc.id) as course_count
FROM gap_analysis ga
LEFT JOIN recommended_courses rc ON ga.skill_id = rc.skill_id AND ga.workflow_id = rc.workflow_id
WHERE ga.workflow_id = '$WORKFLOW_ID'
GROUP BY ga.skill_id, ga.skill_name;
"
# Expected: Each gap should have 1+ courses

# Check 2: Every course has a content outline
sqlite3 test_database.db "
SELECT 
    rc.skill_name,
    COUNT(co.id) as outline_count
FROM recommended_courses rc
LEFT JOIN content_outlines co ON rc.id = co.course_id
WHERE rc.workflow_id = '$WORKFLOW_ID'
GROUP BY rc.skill_name;
"
# Expected: Each course should have 1 outline

# Check 3: Every course has a presentation
sqlite3 test_database.db "
SELECT 
    rc.skill_name,
    COUNT(gp.id) as presentation_count
FROM recommended_courses rc
LEFT JOIN generated_presentations gp ON rc.id = gp.course_id
WHERE rc.workflow_id = '$WORKFLOW_ID'
GROUP BY rc.skill_name;
"
# Expected: Each course should have 1 presentation
Quality checks
# Check presentation quality
sqlite3 test_database.db "
SELECT 
    skill_name,
    total_slides,
    generation_duration_ms / 1000.0 as duration_seconds,
    CASE 
        WHEN presentation_url IS NULL THEN '❌ Missing URL'
        WHEN drive_folder_path IS NULL THEN '❌ Missing folder path'
        WHEN total_slides < 7 OR total_slides > 11 THEN '⚠️  Slide count out of range'
        ELSE '✅ OK'
    END as quality_check
FROM generated_presentations
WHERE workflow_id = '$WORKFLOW_ID'
AND generation_status = 'completed';
"
Generate test report
# Create comprehensive test report
cat > /tmp/e2e_test_report.md << EOF
# End-to-End Workflow Test Report

**Workflow ID**: $WORKFLOW_ID
**Test Date**: $(date '+%Y-%m-%d %H:%M:%S')
**Environment**: Development (Mock Mode: $(grep 'use_mock' src/service/presgen_core_client.py | grep -q 'True' && echo 'Yes' || echo 'No'))

## Stage Results

### Stage 1: Assessment Creation ✅
- Questions: $(sqlite3 test_database.db "SELECT COUNT(*) FROM json_each((SELECT assessment_data FROM workflow_executions WHERE id = '$WORKFLOW_ID'), '\$.questions');")
- Domains covered: Compute, Storage, Networking, Security, Database

### Stage 2: Gap Analysis ✅
- Skills analyzed: $(sqlite3 test_database.db "SELECT COUNT(*) FROM gap_analysis WHERE workflow_id = '$WORKFLOW_ID';")
- Critical gaps: $(sqlite3 test_database.db "SELECT COUNT(*) FROM gap_analysis WHERE workflow_id = '$WORKFLOW_ID' AND gap_severity = 'critical';")
- Average score: $(sqlite3 test_database.db "SELECT ROUND(AVG(score_percentage), 1) FROM gap_analysis WHERE workflow_id = '$WORKFLOW_ID';")%

### Stage 3: Course Recommendations ✅
- Courses recommended: $(sqlite3 test_database.db "SELECT COUNT(*) FROM recommended_courses WHERE workflow_id = '$WORKFLOW_ID';")
- Total learning time: $(sqlite3 test_database.db "SELECT SUM(estimated_duration_minutes) FROM recommended_courses WHERE workflow_id = '$WORKFLOW_ID';") minutes

### Stage 4: Content Outlines ✅
- Outlines generated: $(sqlite3 test_database.db "SELECT COUNT(*) FROM content_outlines WHERE workflow_id = '$WORKFLOW_ID' AND generation_status = 'completed';")
- Total sections: $(sqlite3 test_database.db "SELECT SUM(total_sections) FROM content_outlines WHERE workflow_id = '$WORKFLOW_ID';")

### Stage 5: Presentation Generation ✅
- Presentations completed: $(sqlite3 test_database.db "SELECT COUNT(*) FROM generated_presentations WHERE workflow_id = '$WORKFLOW_ID' AND generation_status = 'completed';")
- Total slides generated: $(sqlite3 test_database.db "SELECT SUM(total_slides) FROM generated_presentations WHERE workflow_id = '$WORKFLOW_ID' AND generation_status = 'completed';")
- Average generation time: $(sqlite3 test_database.db "SELECT ROUND(AVG(generation_duration_ms) / 1000.0, 1) FROM generated_presentations WHERE workflow_id = '$WORKFLOW_ID' AND generation_status = 'completed';") seconds

## Data Consistency ✅
- All gaps have courses: $(sqlite3 test_database.db "SELECT CASE WHEN COUNT(*) = 0 THEN '✅ Yes' ELSE '❌ No' END FROM gap_analysis ga LEFT JOIN recommended_courses rc ON ga.skill_id = rc.skill_id AND ga.workflow_id = rc.workflow_id WHERE ga.workflow_id = '$WORKFLOW_ID' AND rc.id IS NULL;")
- All courses have outlines: $(sqlite3 test_database.db "SELECT CASE WHEN COUNT(*) = 0 THEN '✅ Yes' ELSE '❌ No' END FROM recommended_courses rc LEFT JOIN content_outlines co ON rc.id = co.course_id WHERE rc.workflow_id = '$WORKFLOW_ID' AND co.id IS NULL;")
- All courses have presentations: $(sqlite3 test_database.db "SELECT CASE WHEN COUNT(*) = 0 THEN '✅ Yes' ELSE '❌ No' END FROM recommended_courses rc LEFT JOIN generated_presentations gp ON rc.id = gp.course_id WHERE rc.workflow_id = '$WORKFLOW_ID' AND gp.id IS NULL;")

## Quality Checks
$(sqlite3 test_database.db "SELECT '- ' || skill_name || ': ' || total_slides || ' slides, ' || ROUND(generation_duration_ms/1000.0, 1) || 's' FROM generated_presentations WHERE workflow_id = '$WORKFLOW_ID' AND generation_status = 'completed';")

## Test Verdict
**Status**: $(sqlite3 test_database.db "SELECT CASE WHEN (SELECT COUNT(*) FROM generated_presentations WHERE workflow_id = '$WORKFLOW_ID' AND generation_status = 'failed') = 0 THEN '✅ PASS' ELSE '❌ FAIL' END;")

EOF

# Display report
cat /tmp/e2e_test_report.md
Export results
# Export workflow data for review
sqlite3 test_database.db << EOF
.mode markdown
.output /tmp/e2e_workflow_data.md

SELECT '# Workflow: $WORKFLOW_ID' as title;
SELECT '';
SELECT '## Gap Analysis Results';
SELECT skill_name, score_percentage, gap_severity FROM gap_analysis WHERE workflow_id = '$WORKFLOW_ID';

SELECT '';
SELECT '## Recommended Courses';
SELECT skill_name, course_title, difficulty_level FROM recommended_courses WHERE workflow_id = '$WORKFLOW_ID';

SELECT '';
SELECT '## Generated Presentations';
SELECT skill_name, presentation_title, total_slides, generation_status FROM generated_presentations WHERE workflow_id = '$WORKFLOW_ID';

.output stdout
EOF

cat /tmp/e2e_workflow_data.md
Phase 8: Regression Testing (30 mins)
Objective: Ensure new workflow doesn't break existing functionality
Test existing workflows
# List all workflows
sqlite3 test_database.db "SELECT id, status, created_at FROM workflow_executions ORDER BY created_at DESC LIMIT 5;"

# For each existing workflow, check:
# - Data still accessible
# - Presentations still loadable
# - No corruption
Test parallel workflows
# Create second test workflow while first is running
# Verify both complete successfully
# Check for resource contention issues
Test error scenarios
# Test with invalid data
curl -X POST "http://localhost:8000/api/v1/workflows/invalid-id/execute-gap-analysis"
# Expected: 404 or 400 error, not 500

# Test with missing required fields
curl -X POST "http://localhost:8000/api/v1/assessments" \
  -H "Content-Type: application/json" \
  -d '{"incomplete": "data"}'
# Expected: 422 validation error
Phase 9: Performance Baseline (30 mins)
Objective: Establish performance baselines for the complete workflow
Measure end-to-end time
START_TIME=$(date +%s)

# Run complete workflow (steps 1-6)
# ...

END_TIME=$(date +%s)
TOTAL_TIME=$((END_TIME - START_TIME))

echo "Total workflow time: $TOTAL_TIME seconds"
echo "Total workflow time: $((TOTAL_TIME / 60)) minutes"
Stage timing breakdown
# Query timestamps from database
sqlite3 test_database.db "
WITH workflow_times AS (
  SELECT 
    'Assessment Creation' as stage,
    created_at as start_time,
    created_at as end_time
  FROM workflow_executions
  WHERE id = '$WORKFLOW_ID'
  
  UNION ALL
  
  SELECT 
    'Gap Analysis',
    MIN(created_at),
    MAX(created_at)
  FROM gap_analysis
  WHERE workflow_id = '$WORKFLOW_ID'
  
  UNION ALL
  
  SELECT 
    'Course Recommendations',
    MIN(created_at),
    MAX(created_at)
  FROM recommended_courses
  WHERE workflow_id = '$WORKFLOW_ID'
  
  UNION ALL
  
  SELECT 
    'Content Outlines',
    MIN(generation_started_at),
    MAX(generation_completed_at)
  FROM content_outlines
  WHERE workflow_id = '$WORKFLOW_ID'
  
  UNION ALL
  
  SELECT 
    'Presentation Generation',
    MIN(generation_started_at),
    MAX(generation_completed_at)
  FROM generated_presentations
  WHERE workflow_id = '$WORKFLOW_ID'
)
SELECT 
  stage,
  start_time,
  end_time,
  CAST((julianday(end_time) - julianday(start_time)) * 86400 AS INTEGER) as duration_seconds
FROM workflow_times
ORDER BY start_time;
"
Resource utilization
# Database size
du -h test_database.db

# Table sizes
sqlite3 test_database.db "
SELECT 
    name as table_name,
    CAST(SUM(pgsize) / 1024.0 AS INTEGER) as size_kb
FROM dbstat
WHERE name IN (
    'workflow_executions',
    'gap_analysis',
    'recommended_courses',
    'content_outlines',
    'generated_presentations'
)
GROUP BY name
ORDER BY size_kb DESC;
"
Performance report
cat > /tmp/e2e_performance_report.md << EOF
# E2E Workflow Performance Report

**Workflow ID**: $WORKFLOW_ID
**Total Time**: $TOTAL_TIME seconds ($((TOTAL_TIME / 60)) minutes)
**Mode**: Mock (production will be slower)

## Stage Timings
[Paste timing breakdown from query above]

## Performance Baselines (Mock Mode)
- Assessment Creation: < 1 second
- Gap Analysis: 1-3 seconds
- Course Recommendations: 2-5 seconds
- Content Outlines: 5-10 seconds
- Presentation Generation: 1-2 seconds per presentation

## Production Estimates
- Assessment Creation: < 1 second
- Gap Analysis: 5-10 seconds
- Course Recommendations: 10-20 seconds
- Content Outlines: 30-60 seconds
- Presentation Generation: 3-7 minutes per presentation

**Total Production Estimate**: 15-30 minutes for 5 presentations

## Database Growth
- Total DB size: $(du -h test_database.db | cut -f1)
- Workflow data: ~500KB per workflow
- Presentation data: ~50KB per presentation

EOF

cat /tmp/e2e_performance_report.md
Success Criteria
✅ Complete workflow executes without errors
✅ All stages complete in expected order
✅ Data consistency maintained across all tables
✅ All presentations generated successfully
✅ No orphaned or missing data
✅ Performance within acceptable ranges
✅ Error handling works at each stage
✅ Workflow can be repeated with different data
Estimated Time
Total: 4-5 hours (including all phases and documentation)
Benefits
Confidence: Validates entire system works end-to-end
Documentation: Creates test report for stakeholders
Baselines: Establishes performance benchmarks
Regression: Ensures new features don't break existing functionality
Production Readiness: Proves system ready for real users
Deliverables
Test Report (/tmp/e2e_test_report.md)
Stage results
Data consistency checks
Quality metrics
Pass/fail verdict
Performance Report (/tmp/e2e_performance_report.md)
Timing breakdown
Resource utilization
Production estimates
Workflow Data Export (/tmp/e2e_workflow_data.md)
Gap analysis results
Recommended courses
Generated presentations
Test Script (reusable automation)
Bash script to run E2E test
Can be integrated into CI/CD
Next Steps After E2E Testing
If all tests pass:
Move to Option 1 (Production PresGen-Core)
Run E2E test again with real presentation generation
Validate with stakeholders
Plan production deployment
If tests fail:
Identify failure point
Debug specific stage
Fix issues
Re-run E2E test
Update documentation
Summary Comparison
Option	Time	Complexity	Value	Dependencies	Production Ready
1: Production PresGen-Core	2-3h	Medium	High	PresGen-Core running	Yes - enables real presentations
2: Avatar Integration	5-6h	High	High	Option 1 complete	Yes - adds video capability
3: Fix API Endpoints	1.5-2h	Low	Medium	None	Yes - completes Sprint 3
5: E2E Testing	4-5h	Medium	High	Option 3 helpful	Yes - validates entire system
Recommended Sequence
Option 3 (Fix API Endpoints) - Quick win, completes Sprint 3
Option 5 (E2E Testing) - Validates everything works
Option 1 (Production PresGen-Core) - Real presentations
Option 5 again (E2E with production) - Validate with real generation
Option 2 (Avatar Integration) - Enhanced capability
Total Time: ~14-17 hours spread across multiple days This sequence ensures:
Early validation (E2E with mock)
Incremental progress (fix → test → production → test → enhance)
Reduced risk (test before production changes)
Clear milestones (each option is a deliverable)
