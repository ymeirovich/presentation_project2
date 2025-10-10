"""HTTP client wrapper for PresGen-Core presentation service."""

from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime, timedelta
from typing import Any, Dict, Optional
from uuid import uuid4
from urllib.parse import urljoin

import httpx

from src.common.config import settings
from .schemas import PresGenPresentationRequest, PresGenPresentationResponse


logger = logging.getLogger("presgen_core_client")


class CircuitOpenError(RuntimeError):
    """Raised when the circuit breaker is open for the client."""


class PresGenCoreHTTPError(RuntimeError):
    """Raised when PresGen-Core returns a non-success HTTP status."""


class PresGenCoreTimeoutError(RuntimeError):
    """Raised when PresGen-Core times out."""


class PresGenCoreClient:
    """Client for PresGen-Core presentation generation with retry + circuit breaker."""

    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        use_mock: Optional[bool] = None,
        voice_profile_name: Optional[str] = None,
        quality_level: Optional[str] = None,
        use_cache: Optional[bool] = None,
        max_attempts: int = 3,
        base_backoff_seconds: float = 1.0,
        failure_threshold: int = 3,
        recovery_seconds: int = 60,
        timeout_seconds: Optional[float] = None,
    ) -> None:
        configured_base = base_url or getattr(settings, "presgen_core_url", "http://localhost:8080")
        self.base_url = configured_base.rstrip("/")
        configured_key = api_key or os.getenv("PRESGEN_CORE_API_KEY")
        self.api_key = configured_key

        # Configure timeout: default 600 seconds (10 minutes) for video generation
        # Can be overridden via settings or parameter
        default_timeout = getattr(settings, "presgen_core_timeout_seconds", 600.0)
        configured_timeout = timeout_seconds if timeout_seconds is not None else default_timeout
        self._timeout = httpx.Timeout(configured_timeout)

        default_mock = getattr(settings, "presgen_use_mock", None)
        if default_mock is None:
            default_mock = False
        self.use_mock = use_mock if use_mock is not None else default_mock
        self.voice_profile_name = voice_profile_name or getattr(
            settings,
            "presgen_core_voice_profile",
            "OpenAI Demo Voice (Your Audio)",
        )
        self.quality_level = quality_level or getattr(
            settings,
            "presgen_core_quality_level",
            "fast",
        )
        default_cache = getattr(settings, "presgen_core_use_cache", False)
        self.use_cache = use_cache if use_cache is not None else default_cache
        self._client: Optional[httpx.AsyncClient] = None

        self._max_attempts = max(1, max_attempts)
        self._base_backoff = base_backoff_seconds
        self._failure_threshold = max(1, failure_threshold)
        self._recovery_delta = timedelta(seconds=max(1, recovery_seconds))

        self._failure_count = 0
        self._circuit_reset_at: Optional[datetime] = None

    async def generate_presentation(
        self,
        request: PresGenPresentationRequest,
    ) -> PresGenPresentationResponse:
        """Generate presentation for a skill with retry + circuit breaker."""
        last_exc: Optional[Exception] = None

        for attempt in range(1, self._max_attempts + 1):
            self._ensure_circuit_closed()
            try:
                if self.use_mock:
                    response = await self._mock_generate(request)
                else:
                    response = await self._generate_via_http(request)
                self._reset_failure_state()
                return response
            except Exception as exc:  # pylint: disable=broad-except
                last_exc = exc
                self._record_failure(exc)
                self._log_core_stage(
                    "core_request_failed",
                    request,
                    {
                        "attempt": attempt,
                        "error": str(exc),
                        "use_mock": self.use_mock,
                    },
                )
                if attempt >= self._max_attempts:
                    logger.error(
                        "PresGen-Core generation failed after %s attempts | error=%s",
                        attempt,
                        exc,
                    )
                    raise

                delay = self._base_backoff * attempt
                logger.warning(
                    "PresGen-Core generation attempt %s failed | retrying in %.1fs | error=%s",
                    attempt,
                    delay,
                    exc,
                )
                await asyncio.sleep(delay)

        raise RuntimeError("PresGen-Core generation failed") from last_exc

    def _ensure_circuit_closed(self) -> None:
        if self._circuit_reset_at and datetime.utcnow() < self._circuit_reset_at:
            raise CircuitOpenError(
                "PresGen-Core circuit open; retry after "
                f"{self._circuit_reset_at.isoformat()}"
            )
        if self._circuit_reset_at and datetime.utcnow() >= self._circuit_reset_at:
            logger.info("PresGen-Core circuit reset; resuming requests")
            self._reset_failure_state()

    def _record_failure(self, exc: Exception) -> None:
        self._failure_count += 1
        if self._failure_count >= self._failure_threshold:
            self._circuit_reset_at = datetime.utcnow() + self._recovery_delta
            logger.error(
                "PresGen-Core circuit opened after %s failures | error=%s",
                self._failure_count,
                exc,
            )

    def _reset_failure_state(self) -> None:
        self._failure_count = 0
        self._circuit_reset_at = None

    async def _mock_generate(
        self,
        request: PresGenPresentationRequest,
    ) -> PresGenPresentationResponse:
        """Mocked generation with optional forced failure for testing."""

        logger.warning("⚠️ PresGen-Core mock path used")

        if os.getenv("PRESGEN_CORE_FORCE_FAIL", "false").lower() == "true":
            raise RuntimeError("Forced PresGen-Core failure via PRESGEN_CORE_FORCE_FAIL")
        if request.metadata.get("force_failure"):
            raise RuntimeError("Forced PresGen-Core failure via request metadata")

        await asyncio.sleep(0)
        job_id = f"core_{uuid4().hex}"
        slide_count = max(8, min(20, request.target_duration_minutes + 5))
        presentation_url = f"https://drive.google.com/presentation/d/{job_id}/edit"
        response = PresGenPresentationResponse(
            success=True,
            job_id=job_id,
            presentation_url=presentation_url,
            slide_count=slide_count,
            message="Presentation generated (mock)",
            prompt_used=request.custom_prompt,
        )
        response.duration_ms = 0
        self._log_core_stage(
            "core_request_complete",
            request,
            {"job_id": job_id, "use_mock": True},
        )
        return response

    async def _generate_via_http(
        self,
        request: PresGenPresentationRequest,
    ) -> PresGenPresentationResponse:
        payload = self._build_training_video_request(request)

        # Enhanced logging of request payload
        logger.info("=" * 80)
        logger.info("📤 PresGen-Core REQUEST")
        logger.info("  URL: %s%s", self.base_url, "/training/presentation-only")
        logger.info("  Payload:")
        for key, value in payload.items():
            if key == "content_text" and value:
                logger.info("    %s: %s... (%d chars)", key, str(value)[:100], len(value))
            elif key == "google_slides_url" and value:
                logger.info("    %s: %s", key, value)
            else:
                logger.info("    %s: %s", key, value)
        logger.info("=" * 80)

        self._log_core_stage(
            "core_request_start",
            request,
            {
                "voice_profile": payload.get("voice_profile_name"),
                "quality_level": payload.get("quality_level"),
                "use_cache": payload.get("use_cache"),
                "has_slides": bool(payload.get("google_slides_url")),
                "has_content_text": bool(payload.get("content_text")),
            },
        )

        start = datetime.utcnow()
        try:
            response = await self._post_presentations("/training/presentation-only", payload)
        except httpx.TimeoutException as exc:
            logger.error("❌ PresGen-Core TIMEOUT after %s seconds", (datetime.utcnow() - start).total_seconds())
            raise PresGenCoreTimeoutError("PresGen-Core request timed out") from exc
        except httpx.HTTPStatusError as exc:
            logger.error("❌ PresGen-Core HTTP ERROR %s: %s", exc.response.status_code, exc.response.text)
            raise PresGenCoreHTTPError(
                f"PresGen-Core returned {exc.response.status_code}: {exc.response.text}"
            ) from exc
        except httpx.HTTPError as exc:
            logger.error("❌ PresGen-Core TRANSPORT ERROR: %s", exc)
            raise PresGenCoreHTTPError(f"PresGen-Core transport error: {exc}") from exc

        data = response.json()

        # Enhanced logging of response
        logger.info("=" * 80)
        logger.info("📥 PresGen-Core RESPONSE")
        logger.info("  Status: %s", response.status_code)
        logger.info("  Response data:")
        for key, value in data.items():
            if key == "message" and value and len(str(value)) > 200:
                logger.info("    %s: %s... (%d chars)", key, str(value)[:200], len(str(value)))
            else:
                logger.info("    %s: %s", key, value)
        logger.info("=" * 80)

        normalised = self._normalise_response(data)
        result = PresGenPresentationResponse.model_validate(normalised)
        result.prompt_used = result.prompt_used or request.custom_prompt
        elapsed_ms = int((datetime.utcnow() - start).total_seconds() * 1000)
        result.duration_ms = result.duration_ms or elapsed_ms

        # Enhanced logging of parsed result
        if not result.success or result.error:
            logger.warning("⚠️  PresGen-Core returned success=False or error:")
            logger.warning("  success: %s", result.success)
            logger.warning("  error: %s", result.error)
            logger.warning("  job_id: %s", result.job_id)
            logger.warning("  message: %s", result.message)

        self._log_core_stage(
            "core_request_complete",
            request,
            {
                "job_id": result.job_id,
                "success": result.success,
                "duration_ms": result.duration_ms,
                "download_url": result.download_url,
                "error": result.error,
                "slide_count": result.slide_count,
            },
        )
        return result

    def _build_training_video_request(self, request: PresGenPresentationRequest) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "mode": request.metadata.get("mode") or "presentation_only",
            "voice_profile_name": request.voice_profile_name or self.voice_profile_name,
            "quality_level": request.quality_level or self.quality_level,
            "use_cache": request.use_cache if request.use_cache is not None else self.use_cache,
        }

        slides_url = request.presentation_url or request.metadata.get("presentation_url")
        if slides_url:
            payload["google_slides_url"] = slides_url

        content_text = request.content_text or request.custom_prompt
        if content_text:
            payload["content_text"] = content_text

        reference_video = request.metadata.get("reference_video_path")
        if reference_video:
            payload["reference_video_path"] = reference_video

        return payload

    async def _post_presentations(self, path: str, payload: Dict[str, Any]) -> httpx.Response:
        client = await self._get_client()
        response = await client.post(path, json=payload)
        response.raise_for_status()
        return response

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            headers = {"Content-Type": "application/json"}
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=self._timeout,
                headers=headers,
            )
        return self._client

    def _normalise_response(self, data: Dict[str, Any]) -> Dict[str, Any]:
        result = dict(data)
        download_url = result.get("download_url")
        if download_url:
            if download_url.startswith("/"):
                result["download_url"] = urljoin(f"{self.base_url}/", download_url.lstrip("/"))
        return result

    def _log_core_stage(
        self,
        stage: str,
        request: PresGenPresentationRequest,
        extra: Optional[Dict[str, Any]] = None,
    ) -> None:
        extra = extra or {}
        workflow_id = request.metadata.get("workflow_id")
        logger.info(
            "PresGen-Core %s | workflow_id=%s | skill=%s | details=%s",
            stage,
            workflow_id,
            request.skill,
            extra,
        )

    async def close(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None
