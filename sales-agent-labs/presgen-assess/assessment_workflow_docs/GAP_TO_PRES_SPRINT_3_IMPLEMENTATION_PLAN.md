# Sprint 3: PresGen-Core Integration
## Detailed Implementation Plan

_Last updated: 2025-10-02_

---

## 📋 **Executive Summary**

**Sprint Goal**: Integrate PresGen-Core presentation generation engine to create **individual skill-focused presentations** (one per skill gap, 3-7 minutes each)

**Duration**: Weeks 5-6 (2 weeks)

**Prerequisites**:
- ✅ Sprint 2 Complete - Google Sheets Export operational
- ✅ Gap Analysis data persisted in database
- ✅ Content Outline generation working

**Key Architecture Change**:

- ❌ **OLD**: Single 60-minute presentation covering all skills
- ✅ **NEW**: Multiple short presentations (one per skill gap, 3-7 minutes each)

**Key Deliverables**:
1. Content orchestration service for **per-skill presentation generation**
2. Presentation template selection logic for short-form content
3. Async job queue for **batch presentation generation** (multiple jobs per workflow)
4. Google Drive folder organization with **skill-based naming**
5. Enhanced course recommendations with **1:1 skill-to-presentation mapping**
6. UI updates to **Recommended Courses** section for per-skill generation
7. Sprint 3 TDD manual testing guide

---

## 🎯 **Sprint 3 Objectives**

### 1. PresGen-Core Service Integration
- Integrate existing PresGen-Core presentation generation engine
- Establish service contract between PresGen-Assess and PresGen-Core
- Implement request/response handling with proper error management
- Add correlation ID tracking across services

### 2. Content Orchestration Pipeline (Per-Skill)

- Map **individual skill gaps** to presentation content structure
- Transform single skill content outline into slide content specifications
- Generate **one presentation per skill gap** (not one for all skills)
- Implement batch generation workflow to create all skill presentations
- Each presentation: 3-7 minutes estimated duration

### 3. Presentation Template Management

- Define template selection for **short-form content** (3-7 minute presentations)
- Single consistent template type for all skill-focused presentations
- Template optimized for:
  - Skill introduction (1-2 slides)
  - Gap analysis for this skill (2-3 slides)
  - Learning content (3-5 slides)
  - Summary and next steps (1 slide)
- Total: 7-11 slides per presentation

### 4. Async Job Queue System (Batch Processing)

- Implement background job processing for **batch presentation generation**
- Create one job per skill gap (e.g., 5 skill gaps = 5 parallel jobs)
- Add job status tracking for each skill presentation
- Implement aggregate progress tracking (e.g., "3 of 5 presentations complete")
- Add retry logic for failed individual presentations
- Support concurrent generation of multiple skill presentations

### 5. Google Drive Organization (Per-Skill Structure)

- Create human-readable folder structure:
  - **With user email**: `Assessments/{assessment_title}_{user_email}_{workflow_id}/Presentations/{skill_name}/`
  - **Without user email**: `Assessments/{assessment_title}_{workflow_id}/Presentations/{skill_name}/`
- Each skill gets its own subfolder under Presentations
- File naming: `{skill_name}_presentation_{timestamp}.pptx`
- Example with user email:
  - `Assessments/AWS_Solutions_Architect_john.doe@company.com_abc-123/Presentations/EC2_Instance_Types/`
  - `Assessments/AWS_Solutions_Architect_john.doe@company.com_abc-123/Presentations/S3_Bucket_Policies/`
  - `Assessments/AWS_Solutions_Architect_john.doe@company.com_abc-123/Presentations/IAM_Roles/`
- Example without user email:
  - `Assessments/AWS_Solutions_Architect_abc-123/Presentations/EC2_Instance_Types/`

### 6. Enhanced Course Recommendations (1:1 Skill Mapping)

- **1:1 mapping**: Each recommended course → one skill → one presentation
- Link presentation to its specific course record
- Update UI to show "Generate Presentation" button per course (not one button for all)
- Add presentation URLs to individual course records
- Track generation status per course/skill
- Support regeneration of individual skill presentations

### 7. UI Updates - Recommended Courses Section

- **Add per-course "Generate Presentation" button**
  - Replace single "Generate All" button with individual buttons per course
  - Button states: "Generate", "Generating...", "View Presentation", "Regenerate"
- **Show generation progress per course**
  - Progress indicator (spinner/percentage) during generation
  - Estimated time remaining (3-7 minutes per presentation)
- **Display presentation status badges**
  - "Pending", "Generating", "Completed", "Failed"
- **Add presentation action buttons**
  - "View" - Open Google Slides presentation
  - "Download" - Download PPTX file
  - "Regenerate" - Create new version
- **Batch action support**
  - "Generate All" button to create all skill presentations at once
  - "Download All" to zip and download all presentations

---

## 📦 **Sprint 3 Architecture**

### Service Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                PresGen-Assess (Frontend)                    │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Gap Analysis Dashboard - Recommended Courses        │   │
│  │  ┌────────────────────────────────────────────────┐  │   │
│  │  │ Course 1: EC2 Instance Types                   │  │   │
│  │  │ [Generate Presentation] [View] [Download]      │  │   │
│  │  │ Status: ● Completed | 3:45 min | 8 slides      │  │   │
│  │  └────────────────────────────────────────────────┘  │   │
│  │  ┌────────────────────────────────────────────────┐  │   │
│  │  │ Course 2: S3 Bucket Policies                   │  │   │
│  │  │ [Generating... 65%] [Cancel]                   │  │   │
│  │  │ Status: ● Generating | Est. 1:30 remaining     │  │   │
│  │  └────────────────────────────────────────────────┘  │   │
│  │  ┌────────────────────────────────────────────────┐  │   │
│  │  │ Course 3: IAM Roles                            │  │   │
│  │  │ [Generate Presentation]                        │  │   │
│  │  │ Status: ○ Not Generated                        │  │   │
│  │  └────────────────────────────────────────────────┘  │   │
│  │                                                      │   │
│  │  [Generate All Presentations] [Download All]        │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│              PresGen-Assess Backend API                     │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  POST /workflows/{id}/courses/{course_id}/          │   │
│  │       generate-presentation (Per-Skill) 🎯           │   │
│  │  POST /workflows/{id}/generate-all-presentations    │   │
│  │  GET  /workflows/{id}/presentations                  │   │
│  │  GET  /workflows/{id}/presentations/{pres_id}/status │   │
│  └──────────────────────────────────────────────────────┘   │
│                            ↓                                 │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Content Orchestration Service (Per-Skill) 🎯        │   │
│  │  - Map SINGLE skill gap → Presentation Content       │   │
│  │  - Select short-form template (3-7 min)             │   │
│  │  - Build content spec for ONE skill                  │   │
│  │  - Enqueue ONE job per skill                         │   │
│  └──────────────────────────────────────────────────────┘   │
│                            ↓                                 │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Background Job Queue (Parallel Processing) 🎯       │   │
│  │  - Job 1: EC2 Instance Types     [✅ Complete]      │   │
│  │  - Job 2: S3 Bucket Policies     [⏳ 65%]          │   │
│  │  - Job 3: IAM Roles              [⏸️ Pending]       │   │
│  │  - Parallel execution (max 3 concurrent)             │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                            ↓ (One call per skill)
┌─────────────────────────────────────────────────────────────┐
│                    PresGen-Core Service                     │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  POST /presentations/generate                        │   │
│  │  Input: Single skill content spec                    │   │
│  │  Output: 7-11 slide presentation (3-7 min)           │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│             Google Drive (Human-Readable Folders)           │
│  Assessments/                                               │
│    AWS_Solutions_Architect_john.doe@company.com_abc-123/    │
│      Presentations/                                         │
│        EC2_Instance_Types/                                  │
│          - EC2_Instance_Types_2025-10-02.pptx               │
│        S3_Bucket_Policies/                                  │
│          - S3_Bucket_Policies_2025-10-02.pptx               │
│        IAM_Roles/                                           │
│          - IAM_Roles_2025-10-02.pptx                        │
└─────────────────────────────────────────────────────────────┘
```

---

## 📝 **Database Schema Updates**

### New Table: `generated_presentations`

```sql
-- migrations/sprint_3_presentations.sql

CREATE TABLE IF NOT EXISTS generated_presentations (
    id TEXT PRIMARY KEY,  -- UUID
    workflow_id TEXT NOT NULL REFERENCES workflow_executions(id) ON DELETE CASCADE,

    -- Skill mapping (ONE presentation per skill)
    skill_id TEXT NOT NULL,  -- 🎯 NEW: Links to specific skill gap
    skill_name TEXT NOT NULL,  -- 🎯 NEW: Human-readable skill name
    course_id TEXT REFERENCES recommended_courses(id),  -- 🎯 NEW: 1:1 course mapping

    -- Drive folder naming (human-readable)
    assessment_title TEXT,  -- 🎯 NEW: e.g., "AWS Solutions Architect"
    user_email TEXT,  -- 🎯 NEW: For folder naming (optional)
    drive_folder_path TEXT,  -- 🎯 NEW: Full path for reference

    presentation_title TEXT NOT NULL,
    presentation_url TEXT,  -- Google Slides URL
    download_url TEXT,  -- Direct download URL
    drive_file_id TEXT,  -- Google Drive file ID
    drive_folder_id TEXT,  -- Skill-specific folder ID

    -- Generation metadata
    generation_status TEXT DEFAULT 'pending' CHECK (generation_status IN ('pending', 'generating', 'completed', 'failed', 'cancelled')),
    generation_started_at TEXT,
    generation_completed_at TEXT,
    generation_duration_ms INTEGER,
    estimated_duration_minutes INTEGER,  -- 🎯 NEW: 3-7 minutes

    -- Job tracking
    job_id TEXT UNIQUE,  -- Background job ID
    job_progress INTEGER DEFAULT 0 CHECK (job_progress BETWEEN 0 AND 100),
    job_error_message TEXT,

    -- Template and content (SHORT-FORM)
    template_id TEXT DEFAULT 'short_form_skill',  -- 🎯 NEW: Short-form template
    template_name TEXT DEFAULT 'Skill-Focused Presentation',
    total_slides INTEGER,  -- 🎯 Expected: 7-11 slides
    content_outline_id TEXT REFERENCES content_outlines(id),  -- 🎯 NEW: Links to content outline

    -- Metadata
    file_size_mb REAL,
    thumbnail_url TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,

    -- Indexes
    INDEX idx_presentations_workflow (workflow_id),
    INDEX idx_presentations_skill (skill_id),  -- 🎯 NEW: Query by skill
    INDEX idx_presentations_course (course_id),  -- 🎯 NEW: Query by course
    INDEX idx_presentations_status (generation_status),
    INDEX idx_presentations_job (job_id),
    INDEX idx_presentations_created (created_at DESC),

    -- Constraint: One active presentation per skill per workflow
    UNIQUE(workflow_id, skill_id, generation_status) WHERE generation_status = 'completed'
);

-- Trigger to update updated_at
CREATE TRIGGER IF NOT EXISTS update_presentations_timestamp
AFTER UPDATE ON generated_presentations
BEGIN
    UPDATE generated_presentations SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;
```

### Update Table: `recommended_courses`

```sql
-- Add presentation link to courses
ALTER TABLE recommended_courses ADD COLUMN presentation_id TEXT REFERENCES generated_presentations(id);
ALTER TABLE recommended_courses ADD COLUMN presentation_url TEXT;

CREATE INDEX idx_courses_presentation ON recommended_courses(presentation_id);
```

---

## 🔧 **Implementation Details**

### 1. Service Contract Definitions

```python
# src/schemas/presentation.py
from pydantic import BaseModel, Field, HttpUrl
from typing import List, Dict, Any, Optional
from uuid import UUID
from datetime import datetime
from enum import Enum

class PresentationStatus(str, Enum):
    """Presentation generation status."""
    PENDING = "pending"
    GENERATING = "generating"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class TemplateType(str, Enum):
    """Presentation template types."""
    SINGLE_SKILL = "single_skill"  # 1 skill gap
    MULTI_SKILL = "multi_skill"  # 2-5 skill gaps
    COMPREHENSIVE = "comprehensive"  # 6+ skill gaps
    CUSTOM = "custom"  # User-specified template

class PresentationContentSpec(BaseModel):
    """Content specification for presentation generation (PER-SKILL)."""
    workflow_id: UUID
    skill_id: str  # 🎯 NEW: Single skill this presentation covers
    skill_name: str  # 🎯 NEW: Human-readable skill name

    title: str = Field(..., description="Presentation title")
    subtitle: Optional[str] = Field(None, description="Presentation subtitle")

    # Content structure (SINGLE SKILL)
    skill_gap: Dict[str, Any] = Field(..., description="Single skill gap for this presentation")
    content_outline: Dict[str, Any] = Field(..., description="Content outline for this skill")

    # Template selection (SHORT-FORM)
    template_type: TemplateType = TemplateType.SINGLE_SKILL  # Always single skill
    template_id: Optional[str] = "short_form_skill"

    # Metadata
    exam_name: str
    assessment_title: str  # 🎯 NEW: For Drive folder naming
    learner_name: Optional[str] = None
    user_email: Optional[str] = None  # 🎯 NEW: For Drive folder naming
    assessment_date: datetime
    overall_score: float

class PresentationGenerationRequest(BaseModel):
    """Request to generate presentation."""
    workflow_id: UUID
    template_type: Optional[TemplateType] = None  # Auto-select if None
    custom_title: Optional[str] = None
    include_skill_gap_ids: Optional[List[str]] = None  # If None, include all

class PresentationGenerationResponse(BaseModel):
    """Response after initiating presentation generation."""
    success: bool
    job_id: str
    presentation_id: UUID
    message: str
    estimated_duration_seconds: int
    status_check_url: str

class PresentationJobStatus(BaseModel):
    """Status of presentation generation job."""
    job_id: str
    presentation_id: UUID
    status: PresentationStatus
    progress: int = Field(..., ge=0, le=100)
    current_step: Optional[str] = None
    estimated_time_remaining_seconds: Optional[int] = None
    error_message: Optional[str] = None

class GeneratedPresentation(BaseModel):
    """Complete generated presentation details."""
    id: UUID
    workflow_id: UUID
    presentation_title: str
    presentation_url: Optional[HttpUrl]
    download_url: Optional[HttpUrl]
    drive_file_id: Optional[str]

    generation_status: PresentationStatus
    generation_duration_ms: Optional[int]

    template_name: Optional[str]
    total_slides: Optional[int]
    skill_gaps_covered: List[str]

    file_size_mb: Optional[float]
    thumbnail_url: Optional[HttpUrl]

    created_at: datetime
    updated_at: datetime
```

---

### 2. Content Orchestration Service

```python
# src/service/content_orchestration.py
from typing import List, Dict, Any, Optional
from uuid import UUID, uuid4
import logging
from src.schemas.presentation import (
    PresentationContentSpec,
    TemplateType,
    PresentationGenerationRequest
)
from src.models.gap_analysis import GapAnalysisResults, ContentOutline
from src.models.workflow import WorkflowExecution
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

logger = logging.getLogger(__name__)

class ContentOrchestrationService:
    """Orchestrates content preparation for presentation generation."""

    def __init__(self, db_session: AsyncSession):
        self.db = db_session

    async def prepare_presentation_content(
        self,
        request: PresentationGenerationRequest
    ) -> PresentationContentSpec:
        """
        Prepare content specification for presentation generation.

        Steps:
        1. Fetch gap analysis results
        2. Fetch content outlines
        3. Select appropriate template
        4. Build content specification
        """
        workflow_id = request.workflow_id

        logger.info(f"📋 Preparing presentation content for workflow {workflow_id}")

        # 1. Fetch gap analysis
        gap_analysis = await self._fetch_gap_analysis(workflow_id)
        if not gap_analysis:
            raise ValueError(f"Gap analysis not found for workflow {workflow_id}")

        # 2. Fetch content outlines
        content_outlines = await self._fetch_content_outlines(
            workflow_id,
            request.include_skill_gap_ids
        )

        if not content_outlines:
            raise ValueError(f"No content outlines found for workflow {workflow_id}")

        # 3. Select template
        template_type = request.template_type or self._auto_select_template(
            len(content_outlines)
        )

        # 4. Fetch workflow metadata
        workflow = await self._fetch_workflow(workflow_id)

        # 5. Build content specification
        content_spec = PresentationContentSpec(
            workflow_id=workflow_id,
            title=request.custom_title or self._generate_title(workflow, gap_analysis),
            subtitle=f"Assessment Results - {gap_analysis.created_at.strftime('%B %d, %Y')}",
            skill_gaps=self._format_skill_gaps(gap_analysis),
            content_outlines=self._format_content_outlines(content_outlines),
            template_type=template_type,
            exam_name=workflow.certification_name or "Certification Exam",
            assessment_date=gap_analysis.created_at,
            overall_score=float(gap_analysis.overall_score)
        )

        logger.info(
            f"✅ Content spec prepared | "
            f"gaps={len(content_spec.skill_gaps)} | "
            f"template={template_type} | "
            f"slides_est={self._estimate_slide_count(content_spec)}"
        )

        return content_spec

    async def _fetch_gap_analysis(self, workflow_id: UUID) -> Optional[GapAnalysisResults]:
        """Fetch gap analysis results from database."""
        stmt = select(GapAnalysisResults).where(
            GapAnalysisResults.workflow_id == workflow_id
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def _fetch_content_outlines(
        self,
        workflow_id: UUID,
        skill_ids: Optional[List[str]] = None
    ) -> List[ContentOutline]:
        """Fetch content outlines for specified skills."""
        stmt = select(ContentOutline).where(
            ContentOutline.workflow_id == workflow_id
        )

        if skill_ids:
            stmt = stmt.where(ContentOutline.skill_id.in_(skill_ids))

        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def _fetch_workflow(self, workflow_id: UUID) -> WorkflowExecution:
        """Fetch workflow execution details."""
        stmt = select(WorkflowExecution).where(WorkflowExecution.id == workflow_id)
        result = await self.db.execute(stmt)
        return result.scalar_one()

    def _auto_select_template(self, skill_gap_count: int) -> TemplateType:
        """Auto-select template based on number of skill gaps."""
        if skill_gap_count == 1:
            return TemplateType.SINGLE_SKILL
        elif skill_gap_count <= 5:
            return TemplateType.MULTI_SKILL
        else:
            return TemplateType.COMPREHENSIVE

    def _generate_title(
        self,
        workflow: WorkflowExecution,
        gap_analysis: GapAnalysisResults
    ) -> str:
        """Generate presentation title."""
        cert_name = workflow.certification_name or "Certification"
        score = int(gap_analysis.overall_score)
        return f"{cert_name} - Skill Gap Analysis ({score}% Score)"

    def _format_skill_gaps(self, gap_analysis: GapAnalysisResults) -> List[Dict[str, Any]]:
        """Format skill gaps for presentation."""
        return gap_analysis.skill_gaps  # Already in correct format (JSONB)

    def _format_content_outlines(
        self,
        outlines: List[ContentOutline]
    ) -> List[Dict[str, Any]]:
        """Format content outlines for presentation."""
        return [
            {
                "skill_id": outline.skill_id,
                "skill_name": outline.skill_name,
                "exam_domain": outline.exam_domain,
                "exam_guide_section": outline.exam_guide_section,
                "content_items": outline.content_items,
                "rag_retrieval_score": float(outline.rag_retrieval_score) if outline.rag_retrieval_score else None
            }
            for outline in outlines
        ]

    def _estimate_slide_count(self, content_spec: PresentationContentSpec) -> int:
        """Estimate total slide count."""
        # Title slide + agenda = 2
        # 1 slide per skill gap intro = len(skill_gaps)
        # 2-3 slides per content outline = len(content_outlines) * 2.5
        # Summary slide = 1

        base_slides = 3
        gap_slides = len(content_spec.skill_gaps)
        content_slides = int(len(content_spec.content_outlines) * 2.5)

        return base_slides + gap_slides + content_slides
```

---

### 3. Background Job Queue Implementation

```python
# src/service/background_jobs.py
from typing import Optional
from uuid import UUID, uuid4
import asyncio
import logging
from datetime import datetime
from src.schemas.presentation import (
    PresentationStatus,
    PresentationJobStatus,
    PresentationContentSpec
)
from src.models.presentation import GeneratedPresentation
from src.service.presgen_core_client import PresGenCoreClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

logger = logging.getLogger(__name__)

class PresentationGenerationJob:
    """Background job for presentation generation."""

    def __init__(
        self,
        job_id: str,
        presentation_id: UUID,
        content_spec: PresentationContentSpec,
        db_session: AsyncSession
    ):
        self.job_id = job_id
        self.presentation_id = presentation_id
        self.content_spec = content_spec
        self.db = db_session
        self.presgen_client = PresGenCoreClient()

        self.progress = 0
        self.current_step = "Initializing"
        self.status = PresentationStatus.PENDING

    async def execute(self) -> None:
        """Execute the presentation generation job."""
        try:
            logger.info(f"🎬 Starting presentation generation job {self.job_id}")

            await self._update_status(PresentationStatus.GENERATING, 0, "Starting generation")

            # Step 1: Validate content spec (10%)
            await self._update_progress(10, "Validating content specification")
            await asyncio.sleep(1)  # Simulate work

            # Step 2: Call PresGen-Core API (20-80%)
            await self._update_progress(20, "Generating slides")
            presentation_result = await self.presgen_client.generate_presentation(
                self.content_spec,
                progress_callback=self._presgen_progress_callback
            )

            # Step 3: Save to Drive (80-90%)
            await self._update_progress(80, "Saving to Google Drive")

            # Build human-readable folder path
            folder_path = self._build_drive_folder_path(
                assessment_title=self.content_spec.assessment_title,
                user_email=self.content_spec.user_email,
                workflow_id=self.content_spec.workflow_id,
                skill_name=self.content_spec.skill_name
            )

            drive_result = await self.presgen_client.save_to_drive(
                presentation_result.file_data,
                folder_path=folder_path
            )

            # Step 4: Update database (90-100%)
            await self._update_progress(90, "Finalizing")
            await self._finalize_presentation(presentation_result, drive_result)

            await self._update_status(PresentationStatus.COMPLETED, 100, "Generation complete")

            logger.info(
                f"✅ Presentation generation complete | "
                f"job_id={self.job_id} | "
                f"presentation_id={self.presentation_id}"
            )

        except Exception as e:
            logger.error(f"❌ Presentation generation failed: {e}", exc_info=True)
            await self._update_status(
                PresentationStatus.FAILED,
                self.progress,
                f"Generation failed: {str(e)}"
            )
            raise

    async def _update_status(
        self,
        status: PresentationStatus,
        progress: int,
        current_step: str
    ) -> None:
        """Update job status in database."""
        self.status = status
        self.progress = progress
        self.current_step = current_step

        from sqlalchemy import update
        stmt = update(GeneratedPresentation).where(
            GeneratedPresentation.id == self.presentation_id
        ).values(
            generation_status=status.value,
            job_progress=progress,
            updated_at=datetime.utcnow().isoformat()
        )

        if status == PresentationStatus.GENERATING and progress == 0:
            stmt = stmt.values(generation_started_at=datetime.utcnow().isoformat())
        elif status in [PresentationStatus.COMPLETED, PresentationStatus.FAILED]:
            stmt = stmt.values(generation_completed_at=datetime.utcnow().isoformat())

        await self.db.execute(stmt)
        await self.db.commit()

    async def _update_progress(self, progress: int, step: str) -> None:
        """Update job progress."""
        await self._update_status(self.status, progress, step)

    async def _presgen_progress_callback(self, progress: int, step: str) -> None:
        """Callback for PresGen-Core progress updates."""
        # Map 0-100% from PresGen-Core to 20-80% in our job
        adjusted_progress = 20 + int(progress * 0.6)
        await self._update_progress(adjusted_progress, step)

    async def _finalize_presentation(
        self,
        presentation_result: Any,
        drive_result: Any
    ) -> None:
        """Finalize presentation record in database."""
        from sqlalchemy import update

        duration_ms = (
            datetime.utcnow() - datetime.fromisoformat(
                await self._get_started_at()
            )
        ).total_seconds() * 1000

        stmt = update(GeneratedPresentation).where(
            GeneratedPresentation.id == self.presentation_id
        ).values(
            presentation_url=presentation_result.presentation_url,
            download_url=drive_result.download_url,
            drive_file_id=drive_result.file_id,
            drive_folder_id=drive_result.folder_id,
            total_slides=presentation_result.slide_count,
            file_size_mb=drive_result.file_size_mb,
            thumbnail_url=presentation_result.thumbnail_url,
            generation_duration_ms=int(duration_ms)
        )

        await self.db.execute(stmt)
        await self.db.commit()

    async def _get_started_at(self) -> str:
        """Get generation started timestamp."""
        stmt = select(GeneratedPresentation.generation_started_at).where(
            GeneratedPresentation.id == self.presentation_id
        )
        result = await self.db.execute(stmt)
        return result.scalar_one()

    def _build_drive_folder_path(
        self,
        assessment_title: str,
        user_email: Optional[str],
        workflow_id: UUID,
        skill_name: str
    ) -> str:
        """
        Build human-readable Google Drive folder path.

        Format:
        - With email: Assessments/{assessment_title}_{user_email}_{workflow_id}/Presentations/{skill_name}/
        - Without email: Assessments/{assessment_title}_{workflow_id}/Presentations/{skill_name}/

        Example:
        - Assessments/AWS_Solutions_Architect_john.doe@company.com_abc-123/Presentations/EC2_Instance_Types/
        """
        # Sanitize components for folder naming
        safe_title = assessment_title.replace(" ", "_").replace("/", "-")
        safe_skill = skill_name.replace(" ", "_").replace("/", "-")
        short_workflow_id = str(workflow_id)[:8]  # First 8 chars for brevity

        if user_email:
            # Include user email in folder name
            base_folder = f"{safe_title}_{user_email}_{short_workflow_id}"
        else:
            # Omit user email
            base_folder = f"{safe_title}_{short_workflow_id}"

        return f"Assessments/{base_folder}/Presentations/{safe_skill}/"


class JobQueue:
    """Simple in-memory job queue (replace with Celery/RQ in production)."""

    def __init__(self):
        self.jobs: Dict[str, PresentationGenerationJob] = {}

    async def enqueue(
        self,
        presentation_id: UUID,
        content_spec: PresentationContentSpec,
        db_session: AsyncSession
    ) -> str:
        """Enqueue a new presentation generation job."""
        job_id = str(uuid4())

        job = PresentationGenerationJob(
            job_id=job_id,
            presentation_id=presentation_id,
            content_spec=content_spec,
            db_session=db_session
        )

        self.jobs[job_id] = job

        # Start job in background (use Celery/RQ in production)
        asyncio.create_task(job.execute())

        logger.info(f"📝 Enqueued presentation generation job {job_id}")

        return job_id

    def get_job_status(self, job_id: str) -> Optional[PresentationJobStatus]:
        """Get status of a job."""
        job = self.jobs.get(job_id)
        if not job:
            return None

        return PresentationJobStatus(
            job_id=job.job_id,
            presentation_id=job.presentation_id,
            status=job.status,
            progress=job.progress,
            current_step=job.current_step
        )

# Global job queue instance
job_queue = JobQueue()
```

---

### 4. PresGen-Core Client

```python
# src/service/presgen_core_client.py
import httpx
import logging
from typing import Optional, Callable, Any
from src.schemas.presentation import PresentationContentSpec
from src.common.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

class PresGenCoreClient:
    """Client for PresGen-Core presentation generation service."""

    def __init__(self):
        self.base_url = settings.presgen_core_url
        self.api_key = settings.presgen_core_api_key
        self.timeout = 300.0  # 5 minutes for long-running generation

    async def generate_presentation(
        self,
        content_spec: PresentationContentSpec,
        progress_callback: Optional[Callable[[int, str], None]] = None
    ) -> Any:
        """
        Generate presentation using PresGen-Core.

        Returns presentation result with file_data, presentation_url, etc.
        """
        logger.info(f"🎨 Calling PresGen-Core to generate presentation")

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.base_url}/api/v1/presentations/generate",
                json=content_spec.dict(),
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                }
            )

            response.raise_for_status()
            result = response.json()

            logger.info(
                f"✅ Presentation generated | "
                f"slides={result.get('slide_count')} | "
                f"url={result.get('presentation_url')}"
            )

            return PresentationResult(**result)

    async def save_to_drive(
        self,
        file_data: bytes,
        folder_path: str
    ) -> Any:
        """Save presentation to Google Drive."""
        logger.info(f"💾 Saving presentation to Drive: {folder_path}")

        # Implementation depends on PresGen-Core API
        # This is a placeholder

        return DriveResult(
            file_id="mock_file_id",
            folder_id="mock_folder_id",
            download_url="https://drive.google.com/file/d/mock_file_id",
            file_size_mb=2.5
        )


class PresentationResult:
    """Result from PresGen-Core presentation generation."""
    def __init__(self, **kwargs):
        self.presentation_url = kwargs.get("presentation_url")
        self.file_data = kwargs.get("file_data")
        self.slide_count = kwargs.get("slide_count")
        self.thumbnail_url = kwargs.get("thumbnail_url")


class DriveResult:
    """Result from Google Drive save operation."""
    def __init__(self, **kwargs):
        self.file_id = kwargs.get("file_id")
        self.folder_id = kwargs.get("folder_id")
        self.download_url = kwargs.get("download_url")
        self.file_size_mb = kwargs.get("file_size_mb")
```

---

## 🔌 **API Endpoints**

### 1. Generate Presentation

```python
# src/service/api/v1/endpoints/presentations.py
from fastapi import APIRouter, HTTPException, Depends, status
from uuid import UUID, uuid4
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from src.service.database import get_db_session
from src.schemas.presentation import (
    PresentationGenerationRequest,
    PresentationGenerationResponse,
    PresentationJobStatus,
    GeneratedPresentation,
    PresentationStatus
)
from src.models.presentation import GeneratedPresentation as GeneratedPresentationModel
from src.service.content_orchestration import ContentOrchestrationService
from src.service.background_jobs import job_queue
from src.common.enhanced_logging_v2 import StructuredLogger

router = APIRouter(tags=["Presentations"])
logger = StructuredLogger(__name__)

@router.post(
    "/workflows/{workflow_id}/gap-analysis/generate-presentation",
    response_model=PresentationGenerationResponse,
    status_code=status.HTTP_202_ACCEPTED
)
async def generate_presentation(
    workflow_id: UUID,
    request: PresentationGenerationRequest,
    db: AsyncSession = Depends(get_db_session)
):
    """
    Generate presentation from gap analysis results.

    This is an async operation that returns immediately with a job_id.
    Use the status endpoint to check progress.
    """
    try:
        logger.log_api_request(
            endpoint=f"/workflows/{workflow_id}/gap-analysis/generate-presentation",
            method="POST",
            workflow_id=str(workflow_id)
        )

        # 1. Prepare content specification
        orchestrator = ContentOrchestrationService(db)
        content_spec = await orchestrator.prepare_presentation_content(request)

        # 2. Create presentation record
        presentation_id = uuid4()
        presentation = GeneratedPresentationModel(
            id=str(presentation_id),
            workflow_id=str(workflow_id),
            presentation_title=content_spec.title,
            generation_status=PresentationStatus.PENDING.value,
            template_name=content_spec.template_type.value,
            skill_gaps_covered=",".join([gap["skill_id"] for gap in content_spec.skill_gaps]),
            created_at=datetime.utcnow().isoformat()
        )

        db.add(presentation)
        await db.commit()

        # 3. Enqueue background job
        job_id = await job_queue.enqueue(
            presentation_id=presentation_id,
            content_spec=content_spec,
            db_session=db
        )

        # 4. Update presentation with job_id
        presentation.job_id = job_id
        await db.commit()

        logger.log_api_response(
            endpoint=f"/workflows/{workflow_id}/gap-analysis/generate-presentation",
            status_code=202,
            duration_ms=0,  # TODO: Add timing
            job_id=job_id,
            presentation_id=str(presentation_id)
        )

        return PresentationGenerationResponse(
            success=True,
            job_id=job_id,
            presentation_id=presentation_id,
            message="Presentation generation started",
            estimated_duration_seconds=120,  # 2 minutes estimate
            status_check_url=f"/api/v1/workflows/{workflow_id}/presentations/{presentation_id}/status"
        )

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.log_error(
            error_type=type(e).__name__,
            error_message=str(e),
            workflow_id=str(workflow_id)
        )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to initiate presentation generation: {str(e)}"
        )


@router.get(
    "/workflows/{workflow_id}/presentations/{presentation_id}/status",
    response_model=PresentationJobStatus
)
async def get_presentation_status(
    workflow_id: UUID,
    presentation_id: UUID,
    db: AsyncSession = Depends(get_db_session)
):
    """Get status of presentation generation job."""
    from sqlalchemy import select

    stmt = select(GeneratedPresentationModel).where(
        GeneratedPresentationModel.id == str(presentation_id),
        GeneratedPresentationModel.workflow_id == str(workflow_id)
    )
    result = await db.execute(stmt)
    presentation = result.scalar_one_or_none()

    if not presentation:
        raise HTTPException(status_code=404, detail="Presentation not found")

    # Get job status from queue if still in progress
    if presentation.job_id and presentation.generation_status in ["pending", "generating"]:
        job_status = job_queue.get_job_status(presentation.job_id)
        if job_status:
            return job_status

    # Return status from database
    return PresentationJobStatus(
        job_id=presentation.job_id or "",
        presentation_id=UUID(presentation.id),
        status=PresentationStatus(presentation.generation_status),
        progress=presentation.job_progress or 100,
        current_step="Complete" if presentation.generation_status == "completed" else None,
        error_message=presentation.job_error_message
    )


@router.get(
    "/workflows/{workflow_id}/presentations",
    response_model=List[GeneratedPresentation]
)
async def list_presentations(
    workflow_id: UUID,
    db: AsyncSession = Depends(get_db_session)
):
    """List all presentations for a workflow."""
    from sqlalchemy import select

    stmt = select(GeneratedPresentationModel).where(
        GeneratedPresentationModel.workflow_id == str(workflow_id)
    ).order_by(GeneratedPresentationModel.created_at.desc())

    result = await db.execute(stmt)
    presentations = result.scalars().all()

    return [
        GeneratedPresentation(
            id=UUID(p.id),
            workflow_id=UUID(p.workflow_id),
            presentation_title=p.presentation_title,
            presentation_url=p.presentation_url,
            download_url=p.download_url,
            drive_file_id=p.drive_file_id,
            generation_status=PresentationStatus(p.generation_status),
            generation_duration_ms=p.generation_duration_ms,
            template_name=p.template_name,
            total_slides=p.total_slides,
            skill_gaps_covered=p.skill_gaps_covered.split(",") if p.skill_gaps_covered else [],
            file_size_mb=p.file_size_mb,
            thumbnail_url=p.thumbnail_url,
            created_at=datetime.fromisoformat(p.created_at),
            updated_at=datetime.fromisoformat(p.updated_at)
        )
        for p in presentations
    ]
```

---

## 🧪 **Sprint 3 Manual TDD Test Cases**

Will be documented in: `GAP_TO_PRES_SPRINT_3_TDD_MANUAL_TESTING.md`

### Test Suites:
1. **Content Orchestration** (5 tests)
2. **Template Selection** (4 tests)
3. **Job Queue Management** (6 tests)
4. **PresGen-Core Integration** (8 tests)
5. **Database Persistence** (5 tests)
6. **API Endpoint Testing** (10 tests)
7. **Error Handling** (6 tests)
8. **Drive Organization** (4 tests)

**Total**: 48 test cases

---

## 📊 **Sprint 3 Acceptance Criteria**

- [ ] Content orchestration service implemented and tested
- [ ] Template selection logic working for all template types
- [ ] Background job queue operational with status tracking
- [ ] PresGen-Core client integration complete
- [ ] Database schema migrated (generated_presentations table)
- [ ] All API endpoints functional and documented
- [ ] Drive folder organization implemented
- [ ] Sprint 3 TDD manual testing guide complete
- [ ] All 48 test cases passing
- [ ] Code reviewed and merged

---

## 🚨 **Sprint 3 Risks & Mitigations**

| Risk | Impact | Mitigation |
|------|--------|------------|
| PresGen-Core API changes | HIGH | Version contract, comprehensive error handling |
| Long generation times | MEDIUM | Async job queue, progress updates, timeout handling |
| Drive API rate limits | MEDIUM | Implement retry logic, exponential backoff |
| Job queue memory limits | MEDIUM | Implement persistent queue (Redis/RabbitMQ) in production |
| Template selection errors | LOW | Fallback to default template, comprehensive logging |

---

## 📈 **Success Metrics (Per-Skill Generation)**

### Development Metrics

- **Code Coverage**: Target 85%+
- **API Response Time**: < 200ms for job submission
- **Generation Time**: < 420 seconds per skill presentation (3-7 minutes)
- **Batch Generation Time**: < 10 minutes for 5 skill presentations (parallel)
- **Error Rate**: < 2% for successful generation

### System Metrics

- **Job Queue Throughput**: 3-5 concurrent skill presentations
- **Database Write Performance**: < 50ms per update
- **Drive Upload Speed**: < 30 seconds per presentation
- **Status Check Performance**: < 100ms per request
- **Per-Skill Presentation Size**: 7-11 slides, 2-4 MB PPTX file

---

## 🎯 **Next Steps After Sprint 3**

**Sprint 4**: PresGen-Avatar Integration
- Avatar-narrated video course generation
- Video player UI component
- Course download functionality
- Timer tracker for generation progress

---

## 🎯 **Key Architectural Changes Summary**

### Old Architecture (Comprehensive Presentation)

- **Approach**: One 60-minute presentation covering all skills
- **UI**: Single "Generate Presentation" button for entire workflow
- **Generation**: Sequential, all-in-one job
- **Storage**: Single presentation file per workflow
- **User Experience**: Long wait time (60+ minutes), single large file

### New Architecture (Per-Skill Micro-Presentations) ✅

- **Approach**: Multiple 3-7 minute presentations (one per skill gap)
- **UI**: Per-course "Generate Presentation" button + "Generate All" batch option
- **Generation**: Parallel job queue (3-5 concurrent skill presentations)
- **Storage**: Skill-specific folders with dedicated presentation files
- **User Experience**:
  - Shorter wait times (3-7 minutes per skill)
  - Granular control (generate only needed skills)
  - Progress tracking per skill
  - Bite-sized content perfect for video narration (Sprint 4)

### Benefits of Per-Skill Approach

1. **Faster Time-to-Value**: Users can start viewing presentations within 3-7 minutes
2. **Parallel Processing**: 5 skills = 10 minutes total (vs 60 minutes sequential)
3. **Granular Control**: Regenerate individual skills without affecting others
4. **Better UX**: Progress indicators per skill, not one monolithic progress bar
5. **Video-Ready**: Short presentations ideal for avatar narration in Sprint 4
6. **Scalable**: Easier to manage 10 small files than 1 huge file

---

**Sprint 3 Duration**: 2 weeks (Weeks 5-6)
**Sprint 3 Team**: 1 Senior Developer + 1 Backend Developer + 1 Frontend Developer + 1 QA Engineer
**Sprint 3 Review**: End of Week 6

---

*Document Created*: 2025-10-02
*Last Updated*: 2025-10-02 - Updated for per-skill generation architecture
*Sprint 3 Status*: READY TO START
*Dependencies*: Sprint 2 Complete ✅

