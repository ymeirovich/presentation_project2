"""Gap Analysis data models for Sprint 0+.

Sprint 0-1 Deliverable: Database models for Gap Analysis persistence.
"""

from datetime import datetime
from uuid import UUID, uuid4
from typing import Optional

from sqlalchemy import Column, String, DateTime, JSON, Text, Float, Integer, ForeignKey
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from src.models.base import Base


class GapAnalysisResult(Base):
    """Complete gap analysis results with text summary and metrics."""

    __tablename__ = "gap_analysis_results"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    workflow_id = Column(PGUUID(as_uuid=True), ForeignKey("workflow_executions.id"), nullable=False, index=True)

    # Overall performance metrics
    overall_score = Column(Float, nullable=False)  # 0-100
    total_questions = Column(Integer, nullable=False)
    correct_answers = Column(Integer, nullable=False)
    incorrect_answers = Column(Integer, nullable=False)

    # Skill gaps and performance by domain
    skill_gaps = Column(JSON, nullable=False)  # List[SkillGap]
    performance_by_domain = Column(JSON, nullable=False)  # Dict[domain, score]
    severity_scores = Column(JSON, nullable=False)  # Dict[skill_id, severity]

    # Text summary (plain language explanation)
    text_summary = Column(Text, nullable=False)

    # Charts data for dashboard
    charts_data = Column(JSON)  # Pre-computed chart data

    # Metadata
    certification_profile_id = Column(PGUUID(as_uuid=True), nullable=False)
    generated_at = Column(DateTime(timezone=True), server_default=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    content_outlines = relationship("ContentOutline", back_populates="gap_analysis", cascade="all, delete-orphan")
    recommended_courses = relationship("RecommendedCourse", back_populates="gap_analysis", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<GapAnalysisResult(id={self.id}, workflow_id={self.workflow_id}, overall_score={self.overall_score})>"


class ContentOutline(Base):
    """Content outline mapped to skill gaps via RAG retrieval."""

    __tablename__ = "content_outlines"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    gap_analysis_id = Column(PGUUID(as_uuid=True), ForeignKey("gap_analysis_results.id"), nullable=False, index=True)
    workflow_id = Column(PGUUID(as_uuid=True), ForeignKey("workflow_executions.id"), nullable=False, index=True)

    # Skill gap information
    skill_id = Column(String(255), nullable=False)
    skill_name = Column(String(500), nullable=False)
    exam_domain = Column(String(255), nullable=False)
    exam_guide_section = Column(String(500), nullable=False)

    # RAG-retrieved content
    content_items = Column(JSON, nullable=False)  # List[{topic, source, page_ref, summary}]
    rag_retrieval_score = Column(Float, nullable=False)  # Relevance score 0-1

    # Metadata
    retrieved_at = Column(DateTime(timezone=True), server_default=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    gap_analysis = relationship("GapAnalysisResult", back_populates="content_outlines")

    def __repr__(self):
        return f"<ContentOutline(id={self.id}, skill_name={self.skill_name}, items={len(self.content_items)})>"


class RecommendedCourse(Base):
    """Recommended PresGen-Avatar courses for skill gaps."""

    __tablename__ = "recommended_courses"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    gap_analysis_id = Column(PGUUID(as_uuid=True), ForeignKey("gap_analysis_results.id"), nullable=False, index=True)
    workflow_id = Column(PGUUID(as_uuid=True), ForeignKey("workflow_executions.id"), nullable=False, index=True)

    # Skill gap information
    skill_id = Column(String(255), nullable=False)
    skill_name = Column(String(500), nullable=False)
    exam_domain = Column(String(255), nullable=False)
    exam_subsection = Column(String(500))

    # Course information
    course_title = Column(String(500), nullable=False)
    course_description = Column(Text, nullable=False)
    estimated_duration_minutes = Column(Integer, nullable=False)
    difficulty_level = Column(String(50), nullable=False)  # beginner, intermediate, advanced

    # Course outline
    learning_objectives = Column(JSON, nullable=False)  # List[str]
    content_outline = Column(JSON, nullable=False)  # Course structure

    # PresGen-Avatar generation status
    generation_status = Column(String(50), default='pending')  # pending, in_progress, completed, failed
    generation_started_at = Column(DateTime(timezone=True))
    generation_completed_at = Column(DateTime(timezone=True))
    generation_error = Column(Text)

    # Generated course resources
    video_url = Column(Text)  # PresGen-Avatar generated video
    presentation_url = Column(Text)  # Source slides
    download_url = Column(Text)  # Downloadable course file

    # Metadata
    priority = Column(Integer, default=0)  # Higher priority = more critical gap
    recommended_at = Column(DateTime(timezone=True), server_default=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    gap_analysis = relationship("GapAnalysisResult", back_populates="recommended_courses")

    def __repr__(self):
        return f"<RecommendedCourse(id={self.id}, title={self.course_title}, status={self.generation_status})>"