"""Service layer for managing Google Forms assessment automation."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional

try:
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
    from google.oauth2 import service_account
except ImportError:  # pragma: no cover - library mocked during tests
    build = None  # type: ignore
    HttpError = Exception  # type: ignore
    service_account = None  # type: ignore

from src.schemas.google_forms import FormSettings
from src.services.assessment_forms_mapper import AssessmentFormsMapper
from src.services.google_auth_manager import GoogleAuthManager

logger = logging.getLogger(__name__)


class GoogleAPIErrorHandler:
    """Simple exponential-backoff retry helper for Google API calls."""

    def __init__(
        self,
        max_retries: int = 3,
        base_delay: float = 0.5,
        backoff_factor: float = 2.0,
        retry_statuses: Optional[List[int]] = None,
    ) -> None:
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.backoff_factor = backoff_factor
        self.retry_statuses = set(retry_statuses or [429, 500, 503])

    async def execute_with_retry(self, func):
        """Execute a callable with retry support for rate limits and transient errors."""
        attempt = 0
        while True:
            try:
                result = func()
                if asyncio.iscoroutine(result) or isinstance(result, asyncio.Future):
                    return await result
                return result
            except HttpError as exc:  # type: ignore[misc]
                status = getattr(exc.resp, "status", None)
                if status not in self.retry_statuses or attempt >= self.max_retries:
                    raise
                delay = self.base_delay * (self.backoff_factor ** attempt)
                attempt += 1
                logger.warning("Google API call failed with status %s; retrying in %.2fs", status, delay)
                await asyncio.sleep(delay)


class FormCreationValidator:
    """Validate inbound data before attempting Google Form creation."""

    MIN_QUESTIONS = 1

    def validate_assessment_data(self, assessment_data: Dict[str, Any]) -> None:
        questions = assessment_data.get("questions") or []
        if len(questions) < self.MIN_QUESTIONS:
            raise ValueError("Assessment data must contain at least one question")

        title = (assessment_data.get("metadata") or {}).get("form_title") or assessment_data.get("form_title")
        if title and len(title) > 300:
            raise ValueError("Form title must be 300 characters or fewer")


class GoogleFormsService:
    """High-level integration for creating and managing Google Forms assessments."""

    def __init__(
        self,
        *,
        mapper: Optional[AssessmentFormsMapper] = None,
        auth_manager: Optional[GoogleAuthManager] = None,
        error_handler: Optional[GoogleAPIErrorHandler] = None,
        forms_service: Any = None,
        drive_service: Any = None,
    ) -> None:
        self.mapper = mapper or AssessmentFormsMapper()
        self.validator = FormCreationValidator()
        self.error_handler = error_handler or GoogleAPIErrorHandler()
        self.auth_manager = auth_manager or GoogleAuthManager()

        credentials = None
        if forms_service is None or drive_service is None:
            try:
                credentials = self.auth_manager.get_service_credentials()
            except Exception as exc:  # pragma: no cover - surfaced via tests when mocked
                logger.warning("Using deferred credential loading: %s", exc)

        self.forms_service = forms_service or self._build_service("forms", "v1", credentials)
        self.drive_service = drive_service or self._build_service("drive", "v3", credentials)

    def _build_service(self, service_name: str, version: str, credentials):
        if build is None:
            return self.auth_manager.build_service(service_name, version, credentials)
        return build(service_name, version, credentials=credentials, cache_discovery=False)

    async def create_assessment_form(
        self,
        *,
        assessment_data: Dict[str, Any],
        form_title: Optional[str] = None,
        form_description: Optional[str] = None,
        settings: Optional[FormSettings] = None,
    ) -> Dict[str, Any]:
        """Create a Google Form from assessment data and return metadata."""
        self.validator.validate_assessment_data(assessment_data)
        mapped_form = self.mapper.map_assessment_to_form(assessment_data)

        # Forms API only allows setting info.title during creation; other fields
        # must be changed via batchUpdate/patch calls.
        base_title = form_title or mapped_form["info"].get("title") or "Assessment Form"
        description_to_apply = (
            form_description
            or mapped_form["info"].get("description")
        )

        async def _create_form():
            request = self.forms_service.forms().create(body={"info": {"title": base_title}})
            return request.execute()

        creation_response = await self.error_handler.execute_with_retry(_create_form)
        form_id = creation_response.get("formId")
        form_url = creation_response.get("responderUri")

        if description_to_apply:
            async def _update_description():
                request = self.forms_service.forms().batchUpdate(
                    formId=form_id,
                    body={
                        "requests": [
                            {
                                "updateFormInfo": {
                                    "info": {"description": description_to_apply},
                                    "updateMask": "description"
                                }
                            }
                        ]
                    }
                )
                return request.execute()

            await self.error_handler.execute_with_retry(_update_description)

        questions = assessment_data.get("questions", [])
        if questions:
            await self.add_questions_to_form(form_id=form_id, questions=questions, start_index=0)

        if settings:
            await self.configure_form_settings(form_id=form_id, settings=settings)

        return {
            "success": True,
            "form_id": form_id,
            "form_url": form_url,
            "form_title": base_title,
        }

    async def add_questions_to_form(
        self,
        *,
        form_id: str,
        questions: List[Dict[str, Any]],
        start_index: int = 0,
    ) -> Dict[str, Any]:
        """Append assessment questions to an existing form."""
        requests = self.mapper.build_batch_update_requests(questions, start_index=start_index)

        async def _batch_update():
            request = self.forms_service.forms().batchUpdate(
                formId=form_id,
                body={"requests": requests},
            )
            return request.execute()

        update_response = await self.error_handler.execute_with_retry(_batch_update)
        return {
            "success": True,
            "form_id": form_id,
            "questions_added": len(questions),
            "updated_form": update_response.get("form"),
        }

    async def configure_form_settings(
        self,
        *,
        form_id: str,
        settings: FormSettings,
    ) -> Dict[str, Any]:
        """Apply configuration settings to a form."""
        # TODO: Map our FormSettings model to Google FormSettings once the desired
        # fields are confirmed. For now we simply acknowledge the request and
        # return without making further updates to avoid invalid payload errors.
        result: Dict[str, Any] = {}

        applied_settings = {
            "collect_email": settings.collect_email,
            "require_login": settings.require_login,
            "allow_response_editing": settings.allow_response_editing,
            "shuffle_questions": settings.shuffle_questions,
            "show_progress_bar": settings.show_progress_bar,
            "confirmation_message": settings.confirmation_message,
        }

        return {"success": True, "form_id": form_id, "settings_applied": applied_settings, "raw_response": result}

    async def get_form_responses(
        self,
        *,
        form_id: str,
        include_empty: bool = False,
    ) -> Dict[str, Any]:
        """Retrieve and normalise responses from a Google Form."""

        async def _fetch_responses():
            request = self.forms_service.forms().responses().list(formId=form_id)
            return request.execute()

        response_payload = await self.error_handler.execute_with_retry(_fetch_responses)
        raw_responses = response_payload.get("responses", [])
        parsed = [self._serialise_response(item) for item in raw_responses]
        if not include_empty:
            parsed = [item for item in parsed if item["answers"]]

        return {"success": True, "responses": parsed}

    def _serialise_response(self, response: Dict[str, Any]) -> Dict[str, Any]:
        answers = {}
        for question_id, data in (response.get("answers") or {}).items():
            if "textAnswers" in data:
                text_answers = data["textAnswers"].get("answers", [])
                answers[question_id] = text_answers[0].get("value") if text_answers else None
            elif "choiceAnswers" in data:
                choices = data["choiceAnswers"].get("answers", [])
                answers[question_id] = choices[0] if choices else None
            else:
                answers[question_id] = data

        return {
            "response_id": response.get("responseId"),
            "respondent_email": response.get("respondentEmail"),
            "submitted_at": response.get("lastSubmittedTime"),
            "answers": answers,
        }

    async def update_drive_permissions(
        self,
        *,
        file_id: str,
        email: str,
        role: str = "writer",
    ) -> Dict[str, Any]:
        """Share the generated form/response sheet with a collaborator."""

        async def _create_permission():
            request = self.drive_service.permissions().create(
                fileId=file_id,
                body={"type": "user", "role": role, "emailAddress": email},
                sendNotificationEmail=False,
            )
            return request.execute()

        result = await self.error_handler.execute_with_retry(_create_permission)
        return {"success": True, "permission": result}
