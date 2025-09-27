"""Pydantic schemas for Google Forms integration."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, validator


class FormSettings(BaseModel):
    """Configuration options applied to a Google Form."""

    collect_email: bool = Field(default=False,
                                description="Collect respondent email addresses.")
    require_login: bool = Field(default=False,
                                description="Restrict responses to authenticated users.")
    allow_response_editing: bool = Field(default=False,
                                         description="Allow respondents to edit submissions.")
    shuffle_questions: bool = Field(default=False,
                                    description="Shuffle question order for respondents.")
    show_progress_bar: bool = Field(default=False,
                                    description="Display progress bar during completion.")
    confirmation_message: Optional[str] = Field(default=None,
                                                description="Custom message shown after submission.")


class CreateFormRequest(BaseModel):
    """Request payload for creating an assessment-backed Google Form."""

    assessment_id: Optional[str] = Field(default=None)
    form_title: Optional[str] = Field(default=None)
    form_description: Optional[str] = Field(default=None)
    certification_profile_id: Optional[str] = Field(default=None)
    questions: Optional[List[Dict[str, Any]]] = Field(default=None)
    settings: FormSettings = Field(default_factory=FormSettings)

    @validator("form_title")
    def validate_title(cls, value: Optional[str]) -> Optional[str]:
        if value and len(value) > 300:
            raise ValueError("Form title must be 300 characters or fewer")
        return value


class AddQuestionsRequest(BaseModel):
    """Request payload for appending questions to an existing form."""

    questions: List[Dict[str, Any]]
    start_index: int = Field(default=0, ge=0)


class FormResponse(BaseModel):
    """Raw form response as returned by Google Forms API."""

    response_id: str
    respondent_email: Optional[str] = None
    submitted_at: Optional[str] = None
    answers: Dict[str, Any]
    completion_time_seconds: Optional[int] = None


class ProcessedFormResponse(FormResponse):
    """Processed form response enriched with scoring details."""

    scores: Dict[str, float] = Field(default_factory=dict)
    total_score: float = 0.0
    percentage: float = 0.0


class AssessmentWorkflowRequest(BaseModel):
    """Kick-off payload for assessment-to-form workflow orchestration."""

    certification_profile_id: str
    assessment_parameters: Dict[str, Any] = Field(default_factory=dict)
    workflow_name: Optional[str] = None
    form_settings: Optional[FormSettings] = None
