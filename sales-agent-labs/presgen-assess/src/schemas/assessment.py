"""Pydantic schemas for assessments."""

from datetime import datetime
from typing import Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, validator


class AssessmentBase(BaseModel):
    """Base assessment schema."""
    certification_profile_id: UUID = Field(..., description="Associated certification profile ID")
    title: str = Field(..., min_length=1, max_length=255, description="Assessment title")
    description: Optional[str] = Field(None, description="Assessment description")
    difficulty_level: str = Field(..., description="Difficulty level (beginner, intermediate, advanced)")
    question_count: int = Field(..., ge=1, le=100, description="Number of questions")
    time_limit_minutes: Optional[int] = Field(None, ge=1, description="Time limit in minutes")
    passing_score: int = Field(..., ge=0, le=100, description="Passing score percentage")
    slide_count: int = Field(..., ge=1, le=40, description="Number of presentation slides")
    domain_distribution: Dict[str, int] = Field(..., description="Question distribution by domain")
    tags: List[str] = Field(default_factory=list, description="Assessment tags")
    is_active: bool = Field(default=True, description="Whether assessment is active")

    @validator('difficulty_level')
    def validate_difficulty(cls, v):
        """Validate difficulty level."""
        allowed_levels = ['beginner', 'intermediate', 'advanced']
        if v.lower() not in allowed_levels:
            raise ValueError(f"Difficulty level must be one of: {allowed_levels}")
        return v.lower()

    @validator('slide_count')
    def validate_slide_count(cls, v):
        """Validate slide count is within supported range."""
        if not 1 <= v <= 40:
            raise ValueError('Slide count must be between 1 and 40')
        return v

    @validator('domain_distribution')
    def validate_domain_distribution(cls, v, values):
        """Validate that domain distribution sums to question count."""
        if 'question_count' in values:
            total_questions = sum(v.values())
            if total_questions != values['question_count']:
                raise ValueError(f"Domain distribution ({total_questions}) must sum to question count ({values['question_count']})")
        return v


class AssessmentCreate(AssessmentBase):
    """Schema for creating assessments."""
    pass


class AssessmentUpdate(BaseModel):
    """Schema for updating assessments."""
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None)
    difficulty_level: Optional[str] = Field(None)
    question_count: Optional[int] = Field(None, ge=1, le=100)
    time_limit_minutes: Optional[int] = Field(None, ge=1)
    passing_score: Optional[int] = Field(None, ge=0, le=100)
    slide_count: Optional[int] = Field(None, ge=1, le=40)
    domain_distribution: Optional[Dict[str, int]] = Field(None)
    tags: Optional[List[str]] = Field(None)
    is_active: Optional[bool] = Field(None)

    @validator('difficulty_level')
    def validate_difficulty(cls, v):
        """Validate difficulty level if provided."""
        if v is not None:
            allowed_levels = ['beginner', 'intermediate', 'advanced']
            if v.lower() not in allowed_levels:
                raise ValueError(f"Difficulty level must be one of: {allowed_levels}")
            return v.lower()
        return v

    @validator('slide_count')
    def validate_slide_count(cls, v):
        """Validate slide count if provided."""
        if v is not None and not 1 <= v <= 40:
            raise ValueError('Slide count must be between 1 and 40')
        return v


class AssessmentResponse(AssessmentBase):
    """Schema for assessment responses."""
    id: UUID = Field(..., description="Assessment unique identifier")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    class Config:
        from_attributes = True


class AssessmentSummary(BaseModel):
    """Summary schema for assessments."""
    id: UUID
    title: str
    difficulty_level: str
    question_count: int
    slide_count: int
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class QuestionGeneration(BaseModel):
    """Schema for question generation parameters."""
    domain: str = Field(..., description="Question domain")
    count: int = Field(..., ge=1, description="Number of questions to generate")
    difficulty: str = Field(..., description="Question difficulty level")
    topic_focus: Optional[str] = Field(None, description="Specific topic to focus on")


class AssessmentGeneration(BaseModel):
    """Schema for complete assessment generation."""
    certification_profile_id: UUID = Field(..., description="Certification profile to base assessment on")
    assessment_config: AssessmentCreate = Field(..., description="Assessment configuration")
    question_specifications: List[QuestionGeneration] = Field(..., description="Question generation specifications")
    use_rag_context: bool = Field(default=True, description="Whether to use RAG context for generation")
    context_sources: List[str] = Field(default=["exam_guide", "transcript"], description="Context sources to use")