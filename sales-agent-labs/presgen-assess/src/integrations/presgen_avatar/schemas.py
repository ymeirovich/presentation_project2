"""Pydantic schemas for PresGen-Avatar requests and responses."""

from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field, ConfigDict, HttpUrl


class VoiceConfig(BaseModel):
    """Voice metadata sent to PresGen-Avatar."""

    provider: str = Field(default="openai")
    voice_id: str = Field(default="alloy")
    language: str = Field(default="en-US")
    style: Optional[str] = Field(default=None, description="Optional style preset or profile override")


class AvatarGenerationRequest(BaseModel):
    """Request payload for PresGen-Avatar video generation."""

    presentation_url: HttpUrl
    mode: str = Field(default="presentation-only")
    quality: str = Field(default="fast")
    voice_config: VoiceConfig = Field(default_factory=VoiceConfig)
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Opaque context forwarded to PresGen-Avatar")


class AvatarGenerationResponse(BaseModel):
    """Response returned after initiating generation."""

    model_config = ConfigDict(extra="allow")

    success: bool = True
    job_id: Optional[str] = None
    status: str = Field(default="pending")
    message: Optional[str] = None
    error_message: Optional[str] = None
    progress: Optional[int] = Field(default=None, ge=0, le=100)
    video_url: Optional[str] = None
    estimated_duration_seconds: Optional[int] = None
    course_id: Optional[str] = None
    workflow_id: Optional[str] = None
    skill_id: Optional[str] = None
    context: Dict[str, Any] = Field(default_factory=dict)
    raw_response: Dict[str, Any] = Field(default_factory=dict)


class AvatarJobStatus(BaseModel):
    """Status payload for polling job state."""

    model_config = ConfigDict(extra="allow")

    job_id: str
    status: str = Field(default="pending")
    progress: Optional[int] = Field(default=None, ge=0, le=100)
    video_url: Optional[str] = None
    error_message: Optional[str] = None
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    raw_response: Dict[str, Any] = Field(default_factory=dict)

    def is_terminal(self) -> bool:
        """Return True when the avatar job reached a terminal state."""
        return self.status in {"completed", "failed"}
