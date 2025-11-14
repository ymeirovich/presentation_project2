"""Gap analysis models for multi-dimensional assessment."""

from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional
from uuid import UUID, uuid4

from sqlalchemy import Column, String, DateTime, JSON, Text, Integer, Float, Boolean
from sqlalchemy.dialects.postgresql import UUID as PGUUID, ARRAY
from sqlalchemy.sql import func
from pydantic import BaseModel, Field, validator

from src.models.base import Base


class GapType(str, Enum):
    """Types of learning gaps identified."""
    KNOWLEDGE = "knowledge"
    SKILL = "skill"
    APPLICATION = "application"
    CONFIDENCE = "confidence"
    DEPTH = "depth"


class IdentifiedGap(Base):
    """Database model for identified learning gaps."""

    __tablename__ = "identified_gaps"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    assessment_result_id = Column(PGUUID(as_uuid=True), nullable=False)
    gap_type = Column(String(50), nullable=False)
    domain = Column(String(255), nullable=False)
    specific_skills = Column(ARRAY(Text), nullable=False)
    severity_score = Column(Float, nullable=False)  # 0.0 to 1.0
    confidence_impact = Column(Float)
    remediation_priority = Column(Integer)
    estimated_study_time_minutes = Column(Integer)
    recommended_modalities = Column(ARRAY(Text))
    created_at = Column(DateTime(timezone=True), server_default=func.now())


# Pydantic models for API validation

class LearningGap(BaseModel):
    """Multi-dimensional gap representation."""
    id: UUID = Field(default_factory=uuid4)
    gap_type: GapType
    domain: str = Field(..., min_length=1, max_length=255)
    specific_skills: List[str] = Field(..., min_items=1)
    severity: float = Field(..., ge=0.0, le=1.0)
    confidence_impact: float = Field(0.0, ge=0.0, le=1.0)
    prerequisite_gaps: List[str] = Field(default_factory=list)
    estimated_remediation_time: int = Field(..., ge=1)  # minutes
    recommended_learning_modalities: List[str] = Field(default_factory=list)

    @validator('recommended_learning_modalities')
    def validate_modalities(cls, v):
        """Validate learning modalities."""
        valid_modalities = [
            'reading', 'video', 'hands_on', 'practice_tests',
            'flashcards', 'discussion', 'project', 'simulation'
        ]
        for modality in v:
            if modality not in valid_modalities:
                raise ValueError(f'Invalid learning modality: {modality}')
        return v


class ConfidenceIndicator(BaseModel):
    """Confidence assessment indicators."""
    domain: str
    average_confidence: float = Field(..., ge=0.0, le=5.0)
    confidence_accuracy_ratio: float = Field(..., ge=0.0, le=2.0)
    overconfidence_areas: List[str] = Field(default_factory=list)
    underconfidence_areas: List[str] = Field(default_factory=list)


class RemediationAction(BaseModel):
    """Specific remediation action recommendation."""
    action_type: str = Field(..., pattern="^(study|practice|review|project)$")
    description: str = Field(..., min_length=1, max_length=500)
    estimated_duration_minutes: int = Field(..., ge=5, le=300)
    priority: int = Field(..., ge=1, le=5)
    rag_source_references: List[str] = Field(default_factory=list)
    success_criteria: List[str] = Field(default_factory=list)


class PersonalizedLearningPath(BaseModel):
    """Complete personalized learning path."""
    student_id: str
    certification_target: str
    total_estimated_hours: int = Field(..., ge=1)
    recommended_study_schedule: str = Field(..., pattern="^(intensive|moderate|relaxed)$")
    remediation_actions: List[RemediationAction]
    milestones: List[Dict] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.now)

    @validator('remediation_actions')
    def validate_actions_sequence(cls, v):
        """Validate remediation actions are properly sequenced."""
        if len(v) == 0:
            raise ValueError('Learning path must include at least one remediation action')

        # Check priority ordering
        priorities = [action.priority for action in v]
        if priorities != sorted(priorities):
            raise ValueError('Remediation actions must be ordered by priority (1=highest)')

        return v


class GapAnalysisReport(BaseModel):
    """Comprehensive gap analysis report."""
    assessment_id: UUID
    student_identifier: str
    identified_gaps: List[LearningGap]
    confidence_analysis: List[ConfidenceIndicator]
    overall_readiness_score: float = Field(..., ge=0.0, le=100.0)
    priority_learning_areas: List[str] = Field(..., min_items=1)
    estimated_preparation_time_hours: int = Field(..., ge=1)
    recommended_study_approach: str = Field(..., pattern="^(comprehensive|targeted|maintenance)$")
    personalized_learning_path: PersonalizedLearningPath
    rag_sources_consulted: List[str] = Field(default_factory=list)
    generated_at: datetime = Field(default_factory=datetime.now)

    @validator('identified_gaps')
    def validate_gaps_coverage(cls, v):
        """Ensure gaps cover major domains."""
        if len(v) == 0:
            raise ValueError('Gap analysis must identify at least one learning gap')

        # Check for balanced gap type distribution
        gap_types = {gap.gap_type for gap in v}
        if len(gap_types) < 2:
            raise ValueError('Gap analysis should identify multiple types of gaps')

        return v


class SkillAssessment(BaseModel):
    """Individual skill assessment result."""
    skill_name: str = Field(..., min_length=1, max_length=200)
    domain: str
    current_level: str = Field(..., pattern="^(novice|beginner|intermediate|advanced|expert)$")
    target_level: str = Field(..., pattern="^(novice|beginner|intermediate|advanced|expert)$")
    gap_severity: float = Field(..., ge=0.0, le=1.0)
    evidence_sources: List[str] = Field(default_factory=list)
    improvement_actions: List[str] = Field(default_factory=list)

    @validator('target_level')
    def validate_target_higher_than_current(cls, v, values):
        """Ensure target level is appropriate."""
        level_order = ['novice', 'beginner', 'intermediate', 'advanced', 'expert']
        current = values.get('current_level')

        if current and v in level_order and current in level_order:
            current_idx = level_order.index(current)
            target_idx = level_order.index(v)

            if target_idx < current_idx:
                raise ValueError('Target level cannot be lower than current level')

        return v


class DomainPerformance(BaseModel):
    """Performance analysis for certification domain."""
    domain_name: str
    weight_percentage: int = Field(..., ge=0, le=100)
    score_percentage: float = Field(..., ge=0.0, le=100.0)
    questions_attempted: int = Field(..., ge=0)
    questions_correct: int = Field(..., ge=0)
    average_confidence: float = Field(..., ge=0.0, le=5.0)
    time_spent_minutes: float = Field(..., ge=0.0)
    skill_assessments: List[SkillAssessment] = Field(default_factory=list)
    identified_weaknesses: List[str] = Field(default_factory=list)
    recommended_focus_areas: List[str] = Field(default_factory=list)

    @validator('questions_correct')
    def validate_correct_not_exceed_attempted(cls, v, values):
        """Ensure correct answers don't exceed attempted."""
        attempted = values.get('questions_attempted', 0)
        if v > attempted:
            raise ValueError('Correct answers cannot exceed attempted questions')
        return v