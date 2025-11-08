"""Service layer for managing Google Forms assessment automation."""

from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path
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
        import traceback
        attempt = 0
        while True:
            try:
                result = func()
                if asyncio.iscoroutine(result) or isinstance(result, asyncio.Future):
                    return await result
                return result
            except HttpError as exc:  # type: ignore[misc]
                status = getattr(exc.resp, "status", None)

                # DEBUG: Log detailed error information
                logger.error(f"🔴 Google API HttpError Details:")
                logger.error(f"  Status: {status}")
                logger.error(f"  URI: {exc.uri}")
                logger.error(f"  Error details: {exc.error_details}")
                logger.error(f"  Response: {exc.resp}")
                logger.error(f"  Content: {getattr(exc.resp, 'content', 'N/A')}")

                if status not in self.retry_statuses or attempt >= self.max_retries:
                    logger.error(f"🔴 Max retries reached or non-retryable status. Raising exception.")
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
        print("🚨 DEBUG: GoogleFormsService.__init__() called")
        self.mapper = mapper or AssessmentFormsMapper()
        self.validator = FormCreationValidator()
        self.error_handler = error_handler or GoogleAPIErrorHandler()
        self.auth_manager = auth_manager or GoogleAuthManager()

        credentials = None
        if forms_service is None or drive_service is None:
            print("🚨 DEBUG: Loading credentials via auth_manager.get_service_credentials()")
            try:
                credentials = self.auth_manager.get_service_credentials()
                print(f"🚨 DEBUG: Credentials loaded - type: {type(credentials)}")
                print(f"🚨 DEBUG: Has _subject: {hasattr(credentials, '_subject')}")
                if hasattr(credentials, '_subject'):
                    print(f"🚨 DEBUG: Impersonating: {credentials._subject}")
                logger.info(f"✅ GoogleFormsService credentials loaded successfully")
                logger.info(f"   Credential type: {type(credentials)}")
                logger.info(f"   Has scopes: {hasattr(credentials, 'scopes')}")
                if hasattr(credentials, 'scopes'):
                    logger.info(f"   Scopes: {credentials.scopes}")
                if hasattr(credentials, '_subject'):
                    logger.info(f"   Impersonating: {credentials._subject}")
            except Exception as exc:  # pragma: no cover - surfaced via tests when mocked
                print(f"🚨 DEBUG: Exception loading credentials: {exc}")
                logger.warning("Using deferred credential loading: %s", exc)

        print("🚨 DEBUG: Building forms_service...")
        self.forms_service = forms_service or self._build_service("forms", "v1", credentials)
        self.drive_service = drive_service or self._build_service("drive", "v3", credentials)
        print(f"🚨 DEBUG: GoogleFormsService initialized - forms_service type: {type(self.forms_service)}")
        logger.info(f"✅ GoogleFormsService initialized - forms_service type: {type(self.forms_service)}")

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

        # DEBUG: Use print() to bypass logger
        print(f"🚨 DEBUG: Creating form with title: {base_title}")
        print(f"🚨 DEBUG: Questions to add: {len(assessment_data.get('questions', []))}")

        logger.info(f"📝 Creating form with title: {base_title}")
        logger.info(f"📝 Questions to add: {len(assessment_data.get('questions', []))}")

        # DEBUG: Log the exact request body
        import json
        create_body = {"info": {"title": base_title}}
        print(f"🚨 DEBUG: EXACT REQUEST BODY: {json.dumps(create_body, indent=2)}")
        logger.info(f"🔍 EXACT REQUEST BODY for forms().create():")
        logger.info(f"   {json.dumps(create_body, indent=2)}")
        logger.info(f"   Title type: {type(base_title)}, Title repr: {repr(base_title)}")

        async def _create_form():
            print(f"🚨 DEBUG: Inside _create_form(), about to call forms().create()...")
            logger.info(f"🔍 Inside _create_form(), about to call forms().create()...")
            request = self.forms_service.forms().create(body=create_body)
            print(f"🚨 DEBUG: Request object created, executing...")
            logger.info(f"🔍 Request object created, executing...")
            result = request.execute()
            print(f"🚨 DEBUG: Request executed successfully!")
            logger.info(f"🔍 Request executed successfully!")
            return result

        print(f"🚨 DEBUG: Step 1: Creating base form...")
        logger.info("🔨 Step 1: Creating base form...")
        creation_response = await self.error_handler.execute_with_retry(_create_form)
        form_id = creation_response.get("formId")
        form_url = creation_response.get("responderUri")
        logger.info(f"✅ Base form created: {form_id}")

        if description_to_apply:
            logger.info(f"🔨 Step 2: Adding description...")
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
            logger.info(f"✅ Description added")

        questions = assessment_data.get("questions", [])
        if questions:
            logger.info(f"🔨 Step 3: Adding {len(questions)} questions...")
            await self.add_questions_to_form(form_id=form_id, questions=questions, start_index=0)
            logger.info(f"✅ Questions added successfully")

        if settings:
            await self.configure_form_settings(form_id=form_id, settings=settings)

        # Set public access (Anyone with Link can view/respond)
        print(f"🔨 Step 4: Setting public access...")
        await self._set_public_access(form_id)

        # Move form to shared Drive folder
        print(f"🔨 Step 5: Moving to shared folder...")
        await self._move_to_shared_folder(form_id)

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
        import json

        requests = self.mapper.build_batch_update_requests(questions, start_index=start_index)

        # DEBUG: Log the actual batch update payload
        logger.info(f"🔍 Batch update payload for {len(questions)} questions:")
        logger.info(f"🔍 First question sample: {json.dumps(requests[0] if requests else {}, indent=2)}")

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

    async def get_form_structure(
        self,
        *,
        form_id: str,
    ) -> Dict[str, Any]:
        """Retrieve the form structure including questions."""

        async def _fetch_form():
            request = self.forms_service.forms().get(formId=form_id)
            return request.execute()

        form_data = await self.error_handler.execute_with_retry(_fetch_form)

        # Extract questions from form
        questions = []
        items = form_data.get("items", [])
        for item in items:
            question_item = item.get("questionItem", {})
            question = question_item.get("question", {})
            question_id = question.get("questionId")
            title = item.get("title", "")

            if question_id:
                questions.append({
                    "question_id": question_id,
                    "title": title,
                    "index": item.get("index", 0)
                })

        return {"success": True, "questions": questions, "form_id": form_id}

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

    async def _set_public_access(self, form_id: str) -> None:
        """Set form to be publicly accessible (Anyone with Link can view/respond)."""
        import os

        print(f"🔓 Setting public access for form {form_id}...")
        logger.info(f"Setting public access for form: {form_id}")

        try:
            # Use Drive API to set permissions
            async def _set_permission():
                permission = {
                    'type': 'anyone',
                    'role': 'writer',  # Allow anyone to respond
                }
                request = self.drive_service.permissions().create(
                    fileId=form_id,
                    body=permission,
                    fields='id'
                )
                return request.execute()

            await self.error_handler.execute_with_retry(_set_permission)
            print(f"✅ Public access enabled for form {form_id}")
            logger.info(f"✅ Public access enabled for form: {form_id}")
        except Exception as e:
            logger.warning(f"⚠️ Could not set public access for form {form_id}: {e}")
            print(f"⚠️ Could not set public access: {e}")

    async def _move_to_shared_folder(self, form_id: str) -> None:
        """Move form to the shared Drive folder specified by GOOGLE_DRIVE_FOLDER_ID."""
        import os

        folder_id = os.getenv("GOOGLE_DRIVE_FOLDER_ID")
        if not folder_id:
            logger.warning("⚠️ GOOGLE_DRIVE_FOLDER_ID not set - skipping folder move")
            return

        print(f"📁 Moving form {form_id} to folder {folder_id}...")
        logger.info(f"Moving form {form_id} to shared folder: {folder_id}")

        try:
            # First, get the current parents
            async def _get_file():
                request = self.drive_service.files().get(
                    fileId=form_id,
                    fields='parents'
                )
                return request.execute()

            file_data = await self.error_handler.execute_with_retry(_get_file)
            previous_parents = ",".join(file_data.get('parents', []))

            # Move the file to the new folder
            async def _move_file():
                request = self.drive_service.files().update(
                    fileId=form_id,
                    addParents=folder_id,
                    removeParents=previous_parents,
                    fields='id, parents'
                )
                return request.execute()

            await self.error_handler.execute_with_retry(_move_file)
            print(f"✅ Form moved to shared folder {folder_id}")
            logger.info(f"✅ Form {form_id} moved to folder: {folder_id}")
        except Exception as e:
            logger.warning(f"⚠️ Could not move form {form_id} to folder: {e}")
            print(f"⚠️ Could not move to folder: {e}")

    async def upload_video_to_drive(
        self,
        video_path: str,
        filename: str,
        folder_id: str,
    ) -> str:
        """Upload a video file to Google Drive and return public download link.

        Args:
            video_path: Local path to the video file
            filename: Name for the file in Google Drive
            folder_id: Google Drive folder ID to upload to

        Returns:
            Public download URL for the uploaded video
        """
        from googleapiclient.http import MediaFileUpload

        local_path = Path(video_path)
        file_size = local_path.stat().st_size if local_path.exists() else None
        logger.info(
            "drive.video_upload.start | filename=%s | folder_id=%s | local_path=%s | size_bytes=%s",
            filename,
            folder_id,
            video_path,
            file_size,
        )

        try:
            # Upload the file
            async def _upload_file():
                file_metadata = {
                    'name': filename,
                    'parents': [folder_id],
                    'mimeType': 'video/mp4'
                }

                media = MediaFileUpload(
                    video_path,
                    mimetype='video/mp4',
                    resumable=True
                )

                request = self.drive_service.files().create(
                    body=file_metadata,
                    media_body=media,
                    fields='id, webViewLink, webContentLink'
                )
                return request.execute()

            file_data = await self.error_handler.execute_with_retry(_upload_file)
            file_id = file_data.get('id')

            logger.info(
                "drive.video_upload.complete | filename=%s | file_id=%s | folder_id=%s",
                filename,
                file_id,
                folder_id,
            )

            # Set public access (Anyone with Link can view/download)
            async def _set_public_permission():
                permission = {
                    'type': 'anyone',
                    'role': 'reader',  # Allow anyone to view/download
                }
                request = self.drive_service.permissions().create(
                    fileId=file_id,
                    body=permission,
                    fields='id'
                )
                return request.execute()

            await self.error_handler.execute_with_retry(_set_public_permission)
            logger.info("drive.video_upload.permission_granted | file_id=%s", file_id)

            # Return the download link
            download_url = f"https://drive.google.com/uc?export=download&id={file_id}"
            logger.info(
                "drive.video_upload.download_url | file_id=%s | url=%s",
                file_id,
                download_url,
            )

            return download_url

        except Exception as e:
            logger.error("❌ Failed to upload video to Drive: %s", e, exc_info=True)
            raise
