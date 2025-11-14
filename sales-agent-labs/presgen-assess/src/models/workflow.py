"""Workflow state models for async workflow support."""

from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional
from uuid import UUID, uuid4

from sqlalchemy import Column, String, DateTime, JSON, Text, Integer, Boolean
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from pydantic import BaseModel, Field, validator

from src.models.base import Base


class WorkflowStatus(str, Enum):
    """Workflow status enumeration with async support."""
    INITIATED = "initiated"
    ASSESSMENT_GENERATED = "assessment_generated"
    DEPLOYED_TO_GOOGLE = "deployed_to_google"
    AWAITING_COMPLETION = "awaiting_completion"  # Async break point
    SHEET_URL_PROVIDED = "sheet_url_provided"
    RESULTS_ANALYZED = "results_analyzed"
    TRAINING_PLAN_GENERATED = "training_plan_generated"
    COURSE_OUTLINES_GENERATED = "course_outlines_generated"
    PRESENTATIONS_GENERATED = "presentations_generated"
    AVATAR_VIDEOS_GENERATED = "avatar_videos_generated"
    COMPLETED = "completed"
    ERROR = "error"


class WorkflowExecution(Base):
    """Database model for workflow state tracking."""

    __tablename__ = "workflow_executions"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(String(255), nullable=False)
    certification_profile_id = Column(PGUUID(as_uuid=True), nullable=False)
    current_step = Column(String(50), nullable=False)
    execution_status = Column(String(50), nullable=False, default=WorkflowStatus.INITIATED)

    # Google Workspace resources
    google_form_id = Column(String(255))
    google_sheet_id = Column(String(255))
    google_drive_folder_id = Column(String(255))

    # Async workflow support
    paused_at = Column(DateTime(timezone=True))
    resumed_at = Column(DateTime(timezone=True))
    sheet_url_input = Column(Text)
    resume_token = Column(PGUUID(as_uuid=True), default=uuid4)

    # Slide count tracking (40-slide support)
    requested_slide_count = Column(Integer, default=20)
    generated_slide_count = Column(Integer)

    # Workflow data
    assessment_data = Column(JSON)
    gap_analysis_results = Column(JSON)
    training_plan = Column(JSON)
    generated_content_urls = Column(JSON)
    collected_responses = Column(JSON, default=list)

    # Schema compatibility fields
    workflow_type = Column(String(100), default="assessment_generation")
    parameters = Column(JSON, default=dict)
    progress = Column(Integer, default=0)
    assessment_id = Column(PGUUID(as_uuid=True))
    presentation_url = Column(Text)
    status = Column(String(50))  # Alias for execution_status

    # Metadata
    step_execution_log = Column(JSON, default=list)
    error_log = Column(JSON, default=list)
    performance_metrics = Column(JSON, default=dict)
    error_message = Column(Text)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    estimated_completion_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))

    # Relationships
    generated_courses = relationship(
        "GeneratedCourse",
        back_populates="workflow",
        cascade="all, delete-orphan"
    )


class PresentationGeneration(Base):
    """Track presentation generation with slide counts."""

    __tablename__ = "presentation_generations"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    workflow_execution_id = Column(PGUUID(as_uuid=True), nullable=False)
    course_title = Column(String(255), nullable=False)
    requested_slides = Column(Integer, nullable=False)
    generated_slides = Column(Integer)
    generation_duration_seconds = Column(Integer)
    presgen_core_url = Column(Text)
    avatar_video_url = Column(Text)
    rag_sources_used = Column(JSON)
    generation_status = Column(String(50), default='pending')
    error_message = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True))

    __table_args__ = (
        {"schema": None}
    )


# Pydantic models for API validation

class AssessmentRequest(BaseModel):
    """Request model for assessment workflow initiation."""
    certification_id: UUID
    user_id: str = Field(..., min_length=1, max_length=255)
    custom_requirements: Optional[str] = Field(None, max_length=1000)
    slide_count: int = Field(default=20, ge=1, le=40)

    @validator('slide_count')
    def validate_slide_count(cls, v):
        """Validate slide count is within 1-40 range."""
        if not 1 <= v <= 40:
            raise ValueError('Slide count must be between 1 and 40')
        return v


class WorkflowResumeRequest(BaseModel):
    """Request model for resuming async workflow."""
    workflow_id: UUID
    sheet_url: str = Field(..., min_length=1)
    user_id: str = Field(..., min_length=1, max_length=255)

    @validator('sheet_url')
    def validate_google_sheets_url(cls, v):
        """Validate Google Sheets URL format."""
        import re
        pattern = r'^https://docs\.google\.com/spreadsheets/d/[a-zA-Z0-9-_]+'
        if not re.match(pattern, v):
            raise ValueError('Invalid Google Sheets URL format')
        return v


class WorkflowStatusResponse(BaseModel):
    """Response model for workflow status."""
    workflow_id: UUID
    user_id: str
    certification_profile_id: UUID
    current_step: str
    execution_status: WorkflowStatus
    google_form_url: Optional[str] = None
    google_sheet_url: Optional[str] = None
    google_drive_folder_url: Optional[str] = None
    requested_slide_count: int
    generated_slide_count: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    paused_at: Optional[datetime] = None
    resumed_at: Optional[datetime] = None
    estimated_completion_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class PresentationRequest(BaseModel):
    """Request model for presentation generation with 40-slide support."""
    title: str = Field(..., min_length=1, max_length=200)
    course_outline: Dict
    slide_count: int = Field(default=20, ge=1, le=40)
    learning_objectives: List[str]
    difficulty_level: str = Field(..., pattern="^(beginner|intermediate|advanced)$")
    rag_context_required: bool = Field(default=True)

    @validator('slide_count')
    def validate_slide_count(cls, v):
        """Validate slide count is within 1-40 range."""
        if not 1 <= v <= 40:
            raise ValueError('Slide count must be between 1 and 40')
        return v

    @validator('course_outline')
    def validate_course_outline_for_slides(cls, v, values):
        """Ensure enough content sections for requested slides."""
        slide_count = values.get('slide_count', 20)
        sections = v.get('sections', [])

        # Rough estimate: need at least 1 section per 3 slides
        min_sections = max(1, slide_count // 3)
        if len(sections) < min_sections:
            raise ValueError(
                f'Insufficient content sections for {slide_count} slides. '
                f'Need at least {min_sections} content sections.'
            )
        return v


class WorkflowStepLog(BaseModel):
    """Model for individual workflow step execution log."""
    step_name: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    duration_seconds: Optional[int] = None
    success: bool = True
    error_message: Optional[str] = None
    metadata: Optional[Dict] = None
