"""Pydantic schemas for async workflows."""

from datetime import datetime
from typing import Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, validator


class WorkflowBase(BaseModel):
    """Base workflow schema."""
    user_id: str = Field(..., description="User identifier")
    certification_profile_id: UUID = Field(..., description="Associated certification profile")
    assessment_id: Optional[UUID] = Field(None, description="Associated assessment ID")
    workflow_type: str = Field(..., description="Type of workflow")
    parameters: Dict = Field(default_factory=dict, description="Workflow parameters")
    google_sheet_url: Optional[str] = Field(None, description="Google Sheet URL for async resume")
    presentation_url: Optional[str] = Field(None, description="Generated presentation URL")
    progress: int = Field(default=0, ge=0, le=100, description="Completion progress percentage")
    error_message: Optional[str] = Field(None, description="Error message if workflow failed")

    @validator('workflow_type')
    def validate_workflow_type(cls, v):
        """Validate workflow type."""
        allowed_types = ['assessment_generation', 'presentation_generation', 'bulk_processing']
        if v not in allowed_types:
            raise ValueError(f"Workflow type must be one of: {allowed_types}")
        return v

    @validator('google_sheet_url')
    def validate_sheet_url(cls, v):
        """Validate Google Sheet URL format."""
        if v is not None:
            if not v.startswith('https://docs.google.com/spreadsheets/'):
                raise ValueError("Google Sheet URL must be a valid Google Sheets URL")
        return v


class WorkflowCreate(WorkflowBase):
    """Schema for creating workflows."""
    pass


class WorkflowUpdate(BaseModel):
    """Schema for updating workflows."""
    parameters: Optional[Dict] = Field(None, description="Updated workflow parameters")
    google_sheet_url: Optional[str] = Field(None, description="Google Sheet URL")
    presentation_url: Optional[str] = Field(None, description="Presentation URL")
    progress: Optional[int] = Field(None, ge=0, le=100, description="Progress percentage")
    error_message: Optional[str] = Field(None, description="Error message")

    @validator('google_sheet_url')
    def validate_sheet_url(cls, v):
        """Validate Google Sheet URL format if provided."""
        if v is not None and not v.startswith('https://docs.google.com/spreadsheets/'):
            raise ValueError("Google Sheet URL must be a valid Google Sheets URL")
        return v


class WorkflowResponse(WorkflowBase):
    """Schema for workflow responses."""
    id: UUID = Field(..., description="Workflow unique identifier")
    status: str = Field(..., description="Current workflow status")
    resume_token: Optional[str] = Field(None, description="Token for resuming workflow")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    class Config:
        from_attributes = True


class WorkflowResumeRequest(BaseModel):
    """Schema for resuming workflows."""
    google_sheet_url: Optional[str] = Field(None, description="Google Sheet URL to continue processing")
    additional_parameters: Optional[Dict] = Field(None, description="Additional parameters for resumption")

    @validator('google_sheet_url')
    def validate_sheet_url(cls, v):
        """Validate Google Sheet URL format."""
        if v is not None and not v.startswith('https://docs.google.com/spreadsheets/'):
            raise ValueError("Google Sheet URL must be a valid Google Sheets URL")
        return v


class WorkflowStatusUpdate(BaseModel):
    """Schema for workflow status updates."""
    status: str = Field(..., description="New workflow status")
    progress: Optional[int] = Field(None, ge=0, le=100, description="Progress percentage")
    error_message: Optional[str] = Field(None, description="Error message if applicable")

    @validator('status')
    def validate_status(cls, v):
        """Validate workflow status."""
        allowed_statuses = [
            'created', 'in_progress', 'awaiting_completion', 'sheet_url_provided',
            'generating_presentation', 'completed', 'failed'
        ]
        if v not in allowed_statuses:
            raise ValueError(f"Status must be one of: {allowed_statuses}")
        return v


class WorkflowSummary(BaseModel):
    """Summary schema for workflows."""
    id: UUID
    workflow_type: str
    status: str
    progress: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class AsyncWorkflowConfig(BaseModel):
    """Configuration for async workflow processing."""
    enable_async_breaks: bool = Field(default=True, description="Enable async break points")
    max_processing_time_minutes: int = Field(default=60, description="Maximum processing time before async break")
    resume_token_ttl_hours: int = Field(default=72, description="Resume token time-to-live in hours")
    notification_webhook: Optional[str] = Field(None, description="Webhook URL for status notifications")

    class Config:
        json_schema_extra = {
            "example": {
                "enable_async_breaks": True,
                "max_processing_time_minutes": 60,
                "resume_token_ttl_hours": 72,
                "notification_webhook": "https://example.com/webhook"
            }
        }