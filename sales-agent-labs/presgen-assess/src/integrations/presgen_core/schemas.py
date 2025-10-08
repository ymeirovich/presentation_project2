"""Pydantic schemas for PresGen-Core integration."""

from pydantic import BaseModel, Field
from typing import Dict, Any, Optional


class PresGenPresentationRequest(BaseModel):
    """Request payload for PresGen-Core presentation generation."""

    skill: str
    domain: Optional[str] = None
    target_duration_minutes: int = Field(default=10, ge=1, le=60)
    custom_prompt: Optional[str] = None
    presentation_url: Optional[str] = Field(
        default=None,
        description="Existing Google Slides deck to narrate (if already created).",
    )
    content_text: Optional[str] = Field(
        default=None,
        description="Script or slide content for PresGen-Core to synthesize into narration.",
    )
    voice_profile_name: Optional[str] = Field(
        default=None,
        description="Override for the default voice profile used by PresGen-Core.",
    )
    quality_level: Optional[str] = Field(
        default=None,
        description="Override quality profile (e.g., fast, standard, studio).",
    )
    use_cache: Optional[bool] = Field(
        default=None,
        description="Whether PresGen-Core should reuse existing assets when possible.",
    )
    metadata: Dict[str, Any] = Field(default_factory=dict)


class PresGenPresentationResponse(BaseModel):
    """Response from PresGen-Core service."""

    success: bool
    job_id: str
    presentation_url: Optional[str] = None
    slide_count: Optional[int] = None
    message: Optional[str] = None
    prompt_used: Optional[str] = None
    download_url: Optional[str] = Field(
        default=None,
        description="Direct link to the rendered video asset.",
    )
    processing_time: Optional[float] = Field(
        default=None,
        description="Processing time reported by PresGen-Core (seconds).",
    )
    total_duration: Optional[float] = None
    avatar_duration: Optional[float] = None
    presentation_duration: Optional[float] = None
    error: Optional[str] = None
    duration_ms: Optional[int] = Field(
        default=None,
        description="Client-measured round-trip duration in milliseconds.",
    )
