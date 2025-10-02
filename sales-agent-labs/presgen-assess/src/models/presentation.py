"""Presentation Generation data models for Sprint 3.

Sprint 3 Deliverable: Database models for per-skill presentation generation.

Supports:
- One presentation per skill gap (not one comprehensive presentation)
- Human-readable Drive folder organization
- Background job tracking with progress updates
- 1:1 course-to-presentation mapping
"""

from uuid import uuid4
from typing import Optional

from sqlalchemy import Column, String, DateTime, Text, Float, Integer, ForeignKey, CheckConstraint
from sqlalchemy.sql import func

from src.models.base import Base


class GeneratedPresentation(Base):
    """
    Generated presentation record (ONE per skill gap).

    Sprint 3: Each skill gap gets its own short-form presentation (3-7 minutes).
    """

    __tablename__ = "generated_presentations"

    # Primary key
    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))

    # Workflow reference
    workflow_id = Column(
        String(36),
        ForeignKey("workflow_executions.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Skill mapping (ONE presentation per skill)
    skill_id = Column(String(255), nullable=False, index=True)
    skill_name = Column(String(500), nullable=False)
    course_id = Column(
        String(36),
        ForeignKey("recommended_courses.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )

    # Drive folder naming (human-readable)
    assessment_title = Column(String(500), nullable=True)  # e.g., "AWS Solutions Architect"
    user_email = Column(String(255), nullable=True)  # For folder naming (optional)
    drive_folder_path = Column(Text, nullable=True)  # Full path for reference

    # Presentation metadata
    presentation_title = Column(String(500), nullable=False)
    presentation_url = Column(Text, nullable=True)  # Google Slides URL
    download_url = Column(Text, nullable=True)  # Direct download URL
    drive_file_id = Column(String(255), nullable=True)  # Google Drive file ID
    drive_folder_id = Column(String(255), nullable=True)  # Skill-specific folder ID

    # Generation metadata
    generation_status = Column(
        String(50),
        nullable=False,
        server_default='pending',
        index=True
    )
    generation_started_at = Column(DateTime(timezone=True), nullable=True)
    generation_completed_at = Column(DateTime(timezone=True), nullable=True)
    generation_duration_ms = Column(Integer, nullable=True)
    estimated_duration_minutes = Column(Integer, nullable=True)  # 3-7 minutes

    # Job tracking
    job_id = Column(String(36), nullable=True, index=True)  # Background job ID
    job_progress = Column(Integer, nullable=False, server_default='0')  # 0-100
    job_error_message = Column(Text, nullable=True)

    # Template and content (SHORT-FORM)
    template_id = Column(String(100), nullable=True, server_default='short_form_skill')
    template_name = Column(String(255), nullable=True, server_default='Skill-Focused Presentation')
    total_slides = Column(Integer, nullable=True)  # Expected: 7-11 slides
    content_outline_id = Column(
        String(36),
        ForeignKey("content_outlines.id", ondelete="SET NULL"),
        nullable=True
    )

    # Metadata
    file_size_mb = Column(Float, nullable=True)
    thumbnail_url = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    # workflow = relationship("WorkflowExecution", back_populates="presentations")
    # course = relationship("RecommendedCourse", back_populates="presentation")
    # content_outline = relationship("ContentOutline", back_populates="presentations")

    # Table arguments
    __table_args__ = (
        CheckConstraint(
            "generation_status IN ('pending', 'generating', 'completed', 'failed', 'cancelled')",
            name='check_generation_status'
        ),
        CheckConstraint(
            'job_progress >= 0 AND job_progress <= 100',
            name='check_job_progress_range'
        ),
        # Note: Unique constraint for job_id would be handled in migration
        # (can't easily express "unique where not null" in declarative)
    )

    def __repr__(self) -> str:
        return (
            f"<GeneratedPresentation(id={self.id}, skill_name='{self.skill_name}', "
            f"status={self.generation_status}, progress={self.job_progress}%)>"
        )

    @property
    def is_generating(self) -> bool:
        """Check if presentation is currently being generated."""
        return self.generation_status in ['pending', 'generating']

    @property
    def is_complete(self) -> bool:
        """Check if presentation generation is complete."""
        return self.generation_status == 'completed'

    @property
    def has_failed(self) -> bool:
        """Check if presentation generation has failed."""
        return self.generation_status == 'failed'

    @property
    def duration_seconds(self) -> Optional[int]:
        """Get generation duration in seconds."""
        if self.generation_duration_ms:
            return self.generation_duration_ms // 1000
        return None
