"""Google authentication helper utilities for Google APIs."""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional
from pathlib import Path

try:
    from google.oauth2 import service_account
    from google.oauth2.credentials import Credentials as UserCredentials
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
except ImportError:  # pragma: no cover - dependency handled in tests
    service_account = None  # type: ignore
    UserCredentials = None  # type: ignore
    Request = None  # type: ignore
    build = None  # type: ignore
    HttpError = Exception  # type: ignore

from src.common.config import settings

logger = logging.getLogger(__name__)


class GoogleAuthManager:
    """Manage service account credentials and permission validation."""

    FORMS_SCOPE = "https://www.googleapis.com/auth/forms.body"
    DRIVE_SCOPE = "https://www.googleapis.com/auth/drive"

    def __init__(
        self,
        credentials_path: Optional[str] = None,
        user_token_path: Optional[str] = None,
    ):
        self.credentials_path = credentials_path or settings.google_application_credentials
        configured_user_token = user_token_path or settings.google_user_token_path
        self.user_token_path = (
            Path(configured_user_token).expanduser()
            if configured_user_token
            else None
        )
        self.scopes = [self.FORMS_SCOPE, self.DRIVE_SCOPE]

    def get_service_credentials(self):
        """Load Google credentials, preferring user OAuth tokens when available."""

        # Prefer user OAuth credentials when a token file is configured and present.
        if self.user_token_path and self.user_token_path.exists():
            if UserCredentials is None or Request is None:
                raise RuntimeError("google-auth oauth client library is not available")

            # Load credentials WITHOUT passing scopes - the token already has scopes embedded
            # Passing scopes can cause scope mismatch errors with the Google API
            credentials = UserCredentials.from_authorized_user_file(
                str(self.user_token_path)
            )

            if credentials and credentials.expired and credentials.refresh_token:
                credentials.refresh(Request())

            logger.debug("Loaded Google OAuth credentials from %s (scopes: %s)",
                        self.user_token_path, credentials.scopes)
            return credentials

        # Fall back to service account credentials if configured.
        if self.credentials_path:
            if service_account is None:
                raise RuntimeError("google-auth service account library is not available")

            credentials = service_account.Credentials.from_service_account_file(
                self.credentials_path,
                scopes=self.scopes,
            )
            logger.debug("Loaded Google service account credentials from %s", self.credentials_path)
            return credentials

        raise FileNotFoundError(
            "No Google OAuth token or service account credentials available"
        )

    def build_service(self, service_name: str, version: str, credentials) -> Any:
        """Construct a Google API client for the given service."""
        if build is None:
            raise RuntimeError("googleapiclient discovery library is not available")
        return build(service_name, version, credentials=credentials, cache_discovery=False)

    def validate_permissions(self, credentials) -> Dict[str, Any]:
        """Validate that the provided credentials can access Forms and Drive APIs."""
        try:
            forms_service = self.build_service("forms", "v1", credentials)
            drive_service = self.build_service("drive", "v3", credentials)

            forms_service.forms().create(body={"info": {"title": "permission_check"}}).execute()
            drive_service.files().delete(fileId="dummy-test-id").execute()

            return {"valid": True, "message": "Credentials validated successfully"}
        except HttpError as exc:  # pragma: no cover - exercised via tests
            logger.error("Google API permission validation failed: %s", exc)
            return {"valid": False, "error": str(exc)}
        except Exception as exc:  # pragma: no cover
            logger.error("Unexpected error while validating permissions: %s", exc)
            return {"valid": False, "error": str(exc)}
