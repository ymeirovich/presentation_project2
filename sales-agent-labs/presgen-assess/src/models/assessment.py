"""Assessment data models with validation."""

from datetime import datetime
from typing import Dict, List, Optional
from uuid import UUID, uuid4

from sqlalchemy import Column, String, DateTime, JSON, Text, Integer, Float, Boolean
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.sql import func
from pydantic import BaseModel, Field, validator

from src.models.base import Base


class AssessmentResult(Base):
    """Database model for assessment results."""

    __tablename__ = "assessment_results"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    workflow_execution_id = Column(PGUUID(as_uuid=True), nullable=False)
    student_identifier = Column(String(255), nullable=False)

    # Raw results
    responses = Column(JSON, nullable=False)  # Question ID -> Response mapping
    completion_time_seconds = Column(Integer)
    submission_timestamp = Column(DateTime(timezone=True), nullable=False)

    # Calculated metrics
    total_score = Column(Float)
    domain_scores = Column(JSON)  # Domain -> Score mapping
    bloom_level_scores = Column(JSON)  # Cognitive level -> Score mapping
    confidence_indicators = Column(JSON)

    created_at = Column(DateTime(timezone=True), server_default=func.now())


class LearningContent(Base):
    """Track generated learning content."""

    __tablename__ = "learning_content"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    workflow_execution_id = Column(PGUUID(as_uuid=True), nullable=False)
    content_type = Column(String(50), nullable=False)  # presentation, avatar_video, outline
    topic = Column(String(255), nullable=False)
    target_gaps = Column(JSON)  # References to gap IDs

    # Content URLs and metadata
    presgen_core_url = Column(Text)
    presgen_avatar_url = Column(Text)
    google_drive_url = Column(Text)
    public_access_url = Column(Text)

    generation_status = Column(String(50), default='pending')
    generation_started_at = Column(DateTime(timezone=True))
    generation_completed_at = Column(DateTime(timezone=True))
    generation_error_log = Column(JSON)

    created_at = Column(DateTime(timezone=True), server_default=func.now())


# Pydantic models for API validation

class QuestionOption(BaseModel):
    """Individual question option."""
    id: str
    text: str
    is_correct: bool = False


class AssessmentQuestion(BaseModel):
    """Assessment question model."""
    id: str
    question_text: str
    question_type: str = Field(..., pattern="^(multiple_choice|true_false|scenario)$")
    domain: str
    subdomain: Optional[str] = None
    bloom_level: str = Field(..., pattern="^(remember|understand|apply|analyze|evaluate|create)$")
    difficulty: float = Field(ge=0.0, le=1.0)
    options: List[QuestionOption]
    explanation: str
    rag_sources: List[str] = Field(default_factory=list)
    time_limit_seconds: Optional[int] = Field(None, ge=30, le=600)

    @validator('options')
    def validate_options(cls, v, values):
        """Validate question options."""
        question_type = values.get('question_type')

        if question_type == 'multiple_choice':
            if len(v) < 2 or len(v) > 6:
                raise ValueError('Multiple choice questions must have 2-6 options')
            correct_count = sum(1 for opt in v if opt.is_correct)
            if correct_count != 1:
                raise ValueError('Multiple choice questions must have exactly 1 correct answer')

        elif question_type == 'true_false':
            if len(v) != 2:
                raise ValueError('True/false questions must have exactly 2 options')
            correct_count = sum(1 for opt in v if opt.is_correct)
            if correct_count != 1:
                raise ValueError('True/false questions must have exactly 1 correct answer')

        return v


class Assessment(BaseModel):
    """Complete assessment model."""
    id: UUID = Field(default_factory=uuid4)
    certification_profile_id: UUID
    title: str = Field(..., min_length=1, max_length=200)
    description: str = Field(..., max_length=1000)
    questions: List[AssessmentQuestion]
    estimated_duration_minutes: int = Field(ge=10, le=180)
    passing_score_percentage: float = Field(default=70.0, ge=0.0, le=100.0)
    rag_context_used: Dict = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.now)

    @validator('questions')
    def validate_questions(cls, v):
        """Validate assessment questions."""
        if len(v) < 5:
            raise ValueError('Assessment must have at least 5 questions')
        if len(v) > 50:
            raise ValueError('Assessment cannot have more than 50 questions')

        # Check domain coverage
        domains = {q.domain for q in v}
        if len(domains) < 2:
            raise ValueError('Assessment must cover at least 2 domains')

        return v


class StudentResponse(BaseModel):
    """Student response to assessment question."""
    question_id: str
    selected_option_ids: List[str]
    confidence_level: Optional[int] = Field(None, ge=1, le=5)
    time_spent_seconds: Optional[int] = Field(None, ge=0)
    flagged_for_review: bool = False


class AssessmentSubmission(BaseModel):
    """Complete assessment submission."""
    assessment_id: UUID
    student_identifier: str = Field(..., min_length=1, max_length=255)
    responses: List[StudentResponse]
    submission_timestamp: datetime = Field(default_factory=datetime.now)
    total_time_seconds: int = Field(ge=0)

    @validator('responses')
    def validate_responses(cls, v, values):
        """Validate all questions are answered."""
        # Note: In real implementation, would cross-reference with assessment questions
        if len(v) == 0:
            raise ValueError('Assessment submission must include responses')
        return v


class CourseOutline(BaseModel):
    """Course outline model with slide count validation."""
    title: str = Field(..., min_length=1, max_length=200)
    sections: List[Dict]
    estimated_slides: int = Field(ge=1, le=40)
    duration_minutes: int = Field(ge=10, le=180)
    rag_sources: List[str] = Field(default_factory=list)
    learning_objectives: List[str] = Field(default_factory=list)
    difficulty_level: str = Field(default="intermediate", pattern="^(beginner|intermediate|advanced)$")

    @validator('estimated_slides')
    def validate_estimated_slides(cls, v):
        """Validate estimated slides within 1-40 range."""
        if not 1 <= v <= 40:
            raise ValueError('Estimated slides must be between 1 and 40')
        return v

    @validator('sections')
    def validate_sections_for_slides(cls, v, values):
        """Validate sufficient sections for estimated slides."""
        estimated_slides = values.get('estimated_slides', 20)

        # Rough estimate: need at least 1 section per 5 slides
        min_sections = max(1, estimated_slides // 5)
        if len(v) < min_sections:
            raise ValueError(
                f'Need at least {min_sections} sections for {estimated_slides} slides'
            )
        return v


class ContentGenerationRequest(BaseModel):
    """Request for content generation with RAG context."""
    course_outline: CourseOutline
    target_gaps: List[str] = Field(default_factory=list)
    rag_context_required: bool = True
    include_citations: bool = True
    content_type: str = Field(..., pattern="^(presentation|video|outline)$")

    @validator('course_outline')
    def validate_slide_count_limits(cls, v):
        """Ensure slide count is within system limits."""
        if v.estimated_slides > 40:
            raise ValueError('Cannot generate more than 40 slides per presentation')
        return v