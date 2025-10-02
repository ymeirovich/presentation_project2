"""
Presentation Generation Schemas for Sprint 3

Per-skill presentation generation schemas supporting:
- One presentation per skill gap (3-7 minutes each)
- Human-readable Drive folder organization
- Background job processing with progress tracking
- 1:1 course-to-presentation mapping
"""
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
    """Presentation template types (Sprint 3: all use single_skill)."""
    SINGLE_SKILL = "single_skill"  # 1 skill gap (3-7 minutes)
    MULTI_SKILL = "multi_skill"  # FUTURE: 2-5 skill gaps
    COMPREHENSIVE = "comprehensive"  # FUTURE: 6+ skill gaps
    CUSTOM = "custom"  # User-specified template


class PresentationContentSpec(BaseModel):
    """
    Content specification for presentation generation (PER-SKILL).

    Each spec generates ONE presentation for ONE skill gap.
    """
    workflow_id: UUID
    skill_id: str = Field(..., description="Single skill this presentation covers")
    skill_name: str = Field(..., description="Human-readable skill name")

    title: str = Field(..., description="Presentation title")
    subtitle: Optional[str] = Field(None, description="Presentation subtitle")

    # Content structure (SINGLE SKILL)
    skill_gap: Dict[str, Any] = Field(..., description="Single skill gap for this presentation")
    content_outline: Dict[str, Any] = Field(..., description="Content outline for this skill")

    # Template selection (SHORT-FORM)
    template_type: TemplateType = TemplateType.SINGLE_SKILL  # Always single skill in Sprint 3
    template_id: Optional[str] = "short_form_skill"

    # Metadata
    exam_name: str
    assessment_title: str = Field(..., description="For Drive folder naming")
    learner_name: Optional[str] = None
    user_email: Optional[str] = Field(None, description="For Drive folder naming (optional)")
    assessment_date: datetime
    overall_score: float

    class Config:
        json_schema_extra = {
            "example": {
                "workflow_id": "123e4567-e89b-12d3-a456-426614174000",
                "skill_id": "ec2_instance_types",
                "skill_name": "EC2 Instance Types",
                "title": "AWS Solutions Architect - EC2 Instance Types",
                "subtitle": "Skill Gap Analysis - October 2, 2025",
                "skill_gap": {
                    "skill_id": "ec2_instance_types",
                    "skill_name": "EC2 Instance Types",
                    "severity": 8,
                    "confidence_delta": -3.5
                },
                "content_outline": {
                    "skill_id": "ec2_instance_types",
                    "content_items": [
                        {"topic": "T2 vs T3 instances", "source": "AWS Docs", "page": 42}
                    ]
                },
                "exam_name": "AWS Solutions Architect Associate",
                "assessment_title": "AWS Solutions Architect",
                "user_email": "john.doe@company.com",
                "assessment_date": "2025-10-02T10:30:00Z",
                "overall_score": 75.5
            }
        }


class PresentationGenerationRequest(BaseModel):
    """
    Request to generate presentation for a single skill/course.

    Sprint 3: Generate one presentation per course/skill.
    """
    workflow_id: UUID
    course_id: UUID = Field(..., description="Course ID to generate presentation for")
    custom_title: Optional[str] = Field(None, description="Override default title")

    class Config:
        json_schema_extra = {
            "example": {
                "workflow_id": "123e4567-e89b-12d3-a456-426614174000",
                "course_id": "456e7890-e89b-12d3-a456-426614174111",
                "custom_title": "EC2 Deep Dive"
            }
        }


class BatchPresentationGenerationRequest(BaseModel):
    """
    Request to generate presentations for all courses in a workflow.

    Creates multiple parallel jobs (one per skill).
    """
    workflow_id: UUID
    max_concurrent: int = Field(3, ge=1, le=5, description="Max concurrent presentations to generate")

    class Config:
        json_schema_extra = {
            "example": {
                "workflow_id": "123e4567-e89b-12d3-a456-426614174000",
                "max_concurrent": 3
            }
        }


class PresentationGenerationResponse(BaseModel):
    """Response after initiating presentation generation."""
    success: bool
    job_id: str
    presentation_id: UUID
    message: str
    estimated_duration_seconds: int = Field(..., description="Estimated 180-420 seconds (3-7 min)")
    status_check_url: str

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "job_id": "job_789abc",
                "presentation_id": "789e0123-e89b-12d3-a456-426614174222",
                "message": "Presentation generation started for EC2 Instance Types",
                "estimated_duration_seconds": 300,
                "status_check_url": "/api/v1/workflows/123e4567-e89b-12d3-a456-426614174000/presentations/789e0123-e89b-12d3-a456-426614174222/status"
            }
        }


class BatchPresentationGenerationResponse(BaseModel):
    """Response after initiating batch presentation generation."""
    success: bool
    jobs: List[Dict[str, Any]] = Field(..., description="List of started jobs")
    message: str
    total_presentations: int
    estimated_total_duration_seconds: int

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "jobs": [
                    {"job_id": "job_1", "presentation_id": "uuid_1", "skill_name": "EC2 Instance Types"},
                    {"job_id": "job_2", "presentation_id": "uuid_2", "skill_name": "S3 Bucket Policies"}
                ],
                "message": "Started generation for 5 skill presentations",
                "total_presentations": 5,
                "estimated_total_duration_seconds": 600
            }
        }


class PresentationJobStatus(BaseModel):
    """Status of presentation generation job."""
    job_id: str
    presentation_id: UUID
    status: PresentationStatus
    progress: int = Field(..., ge=0, le=100, description="Percentage complete")
    current_step: Optional[str] = Field(None, description="e.g., 'Generating slides'")
    estimated_time_remaining_seconds: Optional[int] = None
    error_message: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "job_id": "job_789abc",
                "presentation_id": "789e0123-e89b-12d3-a456-426614174222",
                "status": "generating",
                "progress": 65,
                "current_step": "Generating slides",
                "estimated_time_remaining_seconds": 105
            }
        }


class GeneratedPresentation(BaseModel):
    """Complete generated presentation details."""
    id: UUID
    workflow_id: UUID

    # Skill mapping
    skill_id: str
    skill_name: str
    course_id: Optional[UUID]

    # Drive folder info
    assessment_title: Optional[str]
    user_email: Optional[str]
    drive_folder_path: Optional[str]

    # Presentation details
    presentation_title: str
    presentation_url: Optional[HttpUrl]
    download_url: Optional[HttpUrl]
    drive_file_id: Optional[str]

    # Generation metadata
    generation_status: PresentationStatus
    generation_started_at: Optional[datetime]
    generation_completed_at: Optional[datetime]
    generation_duration_ms: Optional[int]
    estimated_duration_minutes: Optional[int]

    # Job tracking
    job_id: Optional[str]
    job_progress: int
    job_error_message: Optional[str]

    # Template and content
    template_name: Optional[str]
    total_slides: Optional[int]

    # Metadata
    file_size_mb: Optional[float]
    thumbnail_url: Optional[HttpUrl]
    created_at: datetime
    updated_at: datetime

    class Config:
        json_schema_extra = {
            "example": {
                "id": "789e0123-e89b-12d3-a456-426614174222",
                "workflow_id": "123e4567-e89b-12d3-a456-426614174000",
                "skill_id": "ec2_instance_types",
                "skill_name": "EC2 Instance Types",
                "course_id": "456e7890-e89b-12d3-a456-426614174111",
                "assessment_title": "AWS Solutions Architect",
                "user_email": "john.doe@company.com",
                "drive_folder_path": "Assessments/AWS_Solutions_Architect_john.doe@company.com_123e4567/Presentations/EC2_Instance_Types/",
                "presentation_title": "EC2 Instance Types - Skill Gap Analysis",
                "presentation_url": "https://docs.google.com/presentation/d/abc123",
                "download_url": "https://drive.google.com/file/d/xyz789/export",
                "drive_file_id": "xyz789",
                "generation_status": "completed",
                "generation_duration_ms": 285000,
                "estimated_duration_minutes": 5,
                "job_id": "job_789abc",
                "job_progress": 100,
                "template_name": "Skill-Focused Presentation",
                "total_slides": 9,
                "file_size_mb": 2.3,
                "created_at": "2025-10-02T10:30:00Z",
                "updated_at": "2025-10-02T10:35:00Z"
            }
        }


class PresentationListResponse(BaseModel):
    """List of presentations for a workflow."""
    workflow_id: UUID
    presentations: List[GeneratedPresentation]
    total_count: int
    completed_count: int
    pending_count: int
    generating_count: int
    failed_count: int

    class Config:
        json_schema_extra = {
            "example": {
                "workflow_id": "123e4567-e89b-12d3-a456-426614174000",
                "presentations": [],
                "total_count": 5,
                "completed_count": 3,
                "pending_count": 1,
                "generating_count": 1,
                "failed_count": 0
            }
        }
