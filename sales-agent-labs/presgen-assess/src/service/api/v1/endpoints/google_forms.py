"""API endpoints for Google Forms automation workflows."""

from __future__ import annotations

import logging
from fastapi import APIRouter, HTTPException

from src.schemas.google_forms import (
    AddQuestionsRequest,
    CreateFormRequest,
    FormSettings,
)
from src.services.google_forms_service import GoogleFormsService

logger = logging.getLogger(__name__)

router = APIRouter()

google_forms_service: GoogleFormsService | None = None


def get_google_forms_service() -> GoogleFormsService:
    """Instantiate the Google Forms service lazily to simplify testing."""

    global google_forms_service
    if google_forms_service is None:
        google_forms_service = GoogleFormsService()
    return google_forms_service


@router.post("/create")
async def create_form(payload: CreateFormRequest):
    """Create a Google Form for a generated assessment."""
    try:
        service = google_forms_service or get_google_forms_service()
        result = await service.create_assessment_form(
            assessment_data={
                "assessment_id": payload.assessment_id,
                "questions": payload.questions or [],
                "metadata": {
                    "certification_name": payload.form_title or "Assessment",
                    "form_title": payload.form_title,
                    "form_description": payload.form_description,
                    "total_questions": len(payload.questions or []),
                },
            },
            form_title=payload.form_title,
            form_description=payload.form_description,
            settings=payload.settings or FormSettings(),
        )
        return result
    except Exception as exc:  # pragma: no cover - surfaced in tests
        logger.error("Failed to create Google Form: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/{form_id}/questions")
async def add_questions(form_id: str, payload: AddQuestionsRequest):
    """Append questions to an existing form."""
    try:
        service = google_forms_service or get_google_forms_service()
        result = await service.add_questions_to_form(
            form_id=form_id,
            questions=payload.questions,
            start_index=payload.start_index,
        )
        return result
    except Exception as exc:  # pragma: no cover
        logger.error("Failed to add questions to form %s: %s", form_id, exc)
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/{form_id}/responses")
async def get_responses(form_id: str):
    """Retrieve responses for a specified form."""
    try:
        service = google_forms_service or get_google_forms_service()
        result = await service.get_form_responses(form_id=form_id)
        return result
    except Exception as exc:  # pragma: no cover
        logger.error("Failed to retrieve responses for form %s: %s", form_id, exc)
        raise HTTPException(status_code=500, detail=str(exc))
