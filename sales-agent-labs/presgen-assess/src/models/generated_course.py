"""SQLAlchemy model for generated courses (Sprint 4)."""

from datetime import datetime
from typing import Optional

from sqlalchemy import Column, String, Integer, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship

from src.models.base import Base


class GeneratedCourse(Base):
    """Persisted record of a generated course for an individual skill."""

    __tablename__ = "generated_courses"

    id: str = Column(String(32), primary_key=True)
    workflow_id: str = Column(String(32), ForeignKey("workflow_executions.id", ondelete="CASCADE"), nullable=False, index=True)
    skill_id: str = Column(String(255), nullable=False, index=True)
    skill_name: str = Column(String(500), nullable=False)
    course_title: Optional[str] = Column(String(500))

    # Integration metadata
    presgen_core_job_id: Optional[str] = Column(String(255))
    presgen_core_download_url: Optional[str] = Column(String(1000))
    presgen_core_processing_time_ms: Optional[int] = Column(Integer)
    presgen_avatar_job_id: Optional[str] = Column(String(255))
    presentation_url: Optional[str] = Column(String(1000))
    video_url: Optional[str] = Column(String(1000))
    drive_download_url: Optional[str] = Column(String(1000))  # Public Google Drive download link
    local_video_path: Optional[str] = Column(String(1024))

    # Status tracking
    progress: int = Column(Integer, default=0)
    status: str = Column(String(50), default='pending')
    error_message: Optional[str] = Column(Text)

    # Timestamps
    created_at: datetime = Column(DateTime, default=datetime.utcnow)
    updated_at: datetime = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at: Optional[datetime] = Column(DateTime)

    # Back-reference to workflow
    workflow = relationship("WorkflowExecution", back_populates="generated_courses")

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return (
            f"<GeneratedCourse id={self.id} skill_name={self.skill_name!r} "
            f"status={self.status!r} progress={self.progress}>"
        )
