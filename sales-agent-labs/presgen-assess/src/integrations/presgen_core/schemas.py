"""Pydantic schemas for PresGen-Core integration."""

from pydantic import BaseModel, Field
from typing import Dict, Any, Optional


class PresGenPresentationRequest(BaseModel):
    """Request payload for PresGen-Core presentation generation."""

    skill: str
    domain: Optional[str] = None
    target_duration_minutes: int = Field(default=10, ge=1, le=60)
    custom_prompt: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class PresGenPresentationResponse(BaseModel):
    """Response from PresGen-Core service."""

    success: bool
    job_id: str
    presentation_url: Optional[str] = None
    slide_count: Optional[int] = None
    message: Optional[str] = None
    prompt_used: Optional[str] = None
