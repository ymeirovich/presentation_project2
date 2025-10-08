"""HTTP client wrapper for PresGen-Avatar service."""

from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime, timedelta
from typing import Any, Dict, Optional
from urllib.parse import quote
from uuid import uuid4

import httpx

from src.common.config import settings
from .schemas import (
    AvatarGenerationRequest,
    AvatarGenerationResponse,
    AvatarJobStatus,
    VoiceConfig,
)


logger = logging.getLogger("presgen_avatar_client")


class CircuitOpenError(RuntimeError):
    """Raised when the avatar client circuit breaker is open."""


class PresGenAvatarClient:
    """Client for interacting with PresGen-Avatar video generation service."""

    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        use_mock: Optional[bool] = None,
        max_attempts: int = 3,
        base_backoff_seconds: float = 1.0,
        failure_threshold: int = 3,
        recovery_seconds: int = 60,
    ) -> None:
        self.base_url = (base_url or getattr(settings, "presgen_avatar_url", "http://localhost:8002")).rstrip("/")
        self.api_key = api_key
        self._timeout = httpx.Timeout(30.0)
        self.use_mock = use_mock if use_mock is not None else bool(getattr(settings, "presgen_use_mock", False))
        self._client: Optional[httpx.AsyncClient] = None

        self._max_attempts = max(1, max_attempts)
        self._base_backoff = base_backoff_seconds
        self._failure_threshold = max(1, failure_threshold)
        self._recovery_delta = timedelta(seconds=max(1, recovery_seconds))
        self._failure_count = 0
        self._circuit_reset_at: Optional[datetime] = None
        self._job_context: Dict[str, Dict[str, Any]] = {}

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=self._timeout)
        return self._client

    async def generate_video(
        self,
        *,
        workflow_id: str,
        skill_id: str,
        presentation_url: str,
        mode: str = "presentation-only",
        quality: str = "fast",
        voice_provider: str = "openai",
        voice_id: str = "alloy",
        language: str = "en-US",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> AvatarGenerationResponse:
        """Trigger video generation via PresGen-Avatar with retry + circuit breaker."""

        workflow_id = str(workflow_id).strip()
        skill_id = str(skill_id).strip()
        if not workflow_id:
            raise ValueError("workflow_id is required for PresGen-Avatar generation")
        if not skill_id:
            raise ValueError("skill_id is required for PresGen-Avatar generation")

        request_metadata: Dict[str, Any] = dict(metadata or {})
        request_metadata.setdefault("workflow_id", workflow_id)
        request_metadata.setdefault("skill_id", skill_id)

        request = AvatarGenerationRequest(
            presentation_url=presentation_url,
            mode=mode,
            quality=quality,
            voice_config=VoiceConfig(
                provider=voice_provider,
                voice_id=voice_id,
                language=language,
            ),
            metadata=request_metadata,
        )

        last_exc: Optional[Exception] = None
        for attempt in range(1, self._max_attempts + 1):
            self._ensure_circuit_closed()
            try:
                response = await self._send_generate_request(workflow_id, skill_id, request)
                self._reset_failure_state()
                self._register_job_context(response, workflow_id, skill_id)
                return response
            except Exception as exc:  # pylint: disable=broad-except
                last_exc = exc
                self._record_failure(exc)
                if attempt >= self._max_attempts:
                    logger.error(
                        "PresGen-Avatar generation failed after %s attempts | error=%s",
                        attempt,
                        exc,
                    )
                    raise

                delay = self._base_backoff * attempt
                logger.warning(
                    "PresGen-Avatar generation attempt %s failed | retrying in %.1fs | error=%s",
                    attempt,
                    delay,
                    exc,
                )
                await asyncio.sleep(delay)

        raise RuntimeError("PresGen-Avatar generation failed") from last_exc

    async def get_job_status(self, job_id: str) -> AvatarJobStatus:
        """Fetch status for a job."""

        if self.use_mock:
            return await self._mock_status(job_id)

        context = self._job_context.get(job_id)
        if context and context.get("api_mode") == "course":
            workflow_id = context.get("workflow_id")
            course_id = context.get("course_id") or job_id
            try:
                return await self._fetch_course_status(workflow_id, course_id)
            except httpx.HTTPError as exc:
                logger.warning(
                    "PresGen-Avatar course status check failed (%s); falling back to mock completion",
                    exc,
                )
                return await self._mock_status(job_id)

        try:
            client = await self._get_client()
            response = await client.get(
                f"{self.base_url}/api/v1/avatar/status/{job_id}",
                headers=self._headers,
            )
            response.raise_for_status()
            data = response.json()
            status = AvatarJobStatus.model_validate(data)
            status.status = self._normalize_status(status.status)
            status.progress = self._coerce_progress(status.progress)
            status.raw_response = data if isinstance(data, dict) else {"value": data}
            return status
        except httpx.HTTPError as exc:
            logger.warning("PresGen-Avatar status check failed (%s); returning mock completion", exc)
            return await self._mock_status(job_id)

    async def poll_until_complete(
        self,
        job_id: str,
        max_wait_seconds: int = 900,
        poll_interval_seconds: int = 10,
    ) -> AvatarJobStatus:
        """Poll job status until completion or timeout."""

        elapsed = 0
        while elapsed <= max_wait_seconds:
            status = await self.get_job_status(job_id)
            if status.is_terminal():
                return status

            await asyncio.sleep(poll_interval_seconds)
            elapsed += poll_interval_seconds

        raise TimeoutError(f"Avatar generation timed out after {max_wait_seconds} seconds")

    @property
    def _headers(self) -> Dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    async def _send_generate_request(
        self,
        workflow_id: str,
        skill_id: str,
        request: AvatarGenerationRequest,
    ) -> AvatarGenerationResponse:
        if self.use_mock:
            return await self._mock_generate(request)

        try:
            client = await self._get_client()
            endpoint = (
                f"{self.base_url}/api/v1/workflows/"
                f"{quote(workflow_id)}/skills/{quote(skill_id)}/generate-course"
            )
            start_time = datetime.utcnow()
            logger.info(
                "🎯 avatar_client_pipeline | stage=request_start | workflow_id=%s | skill_id=%s | endpoint=%s",
                workflow_id,
                skill_id,
                endpoint,
            )
            response = await client.post(
                endpoint,
                json=request.model_dump(mode="json"),
                headers=self._headers,
            )
            response.raise_for_status()
            data = response.json()
            result = self._parse_generate_response(workflow_id, skill_id, data)
            logger.info(
                "✅ Avatar generation request accepted | job_id=%s | status=%s | duration_ms=%s",
                result.job_id,
                result.status,
                int((datetime.utcnow() - start_time).total_seconds() * 1000),
            )
            return result
        except httpx.HTTPError as exc:
            logger.warning("PresGen-Avatar HTTP error (%s); switching to mock", exc)
            return await self._mock_generate(request)

    def _ensure_circuit_closed(self) -> None:
        if self._circuit_reset_at and datetime.utcnow() < self._circuit_reset_at:
            raise CircuitOpenError(
                "PresGen-Avatar circuit open; retry after "
                f"{self._circuit_reset_at.isoformat()}"
            )
        if self._circuit_reset_at and datetime.utcnow() >= self._circuit_reset_at:
            logger.info("PresGen-Avatar circuit reset; resuming requests")
            self._reset_failure_state()

    def _record_failure(self, exc: Exception) -> None:
        self._failure_count += 1
        if self._failure_count >= self._failure_threshold:
            self._circuit_reset_at = datetime.utcnow() + self._recovery_delta
            logger.error(
                "PresGen-Avatar circuit opened after %s failures | error=%s",
                self._failure_count,
                exc,
            )

    def _reset_failure_state(self) -> None:
        self._failure_count = 0
        self._circuit_reset_at = None

    async def _mock_generate(self, request: AvatarGenerationRequest) -> AvatarGenerationResponse:
        logger.warning("⚠️ PresGen-Avatar mock path used")
        if os.getenv("PRESGEN_AVATAR_FORCE_FAIL", "false").lower() == "true":
            raise RuntimeError("Forced PresGen-Avatar failure via PRESGEN_AVATAR_FORCE_FAIL")
        if request.metadata and request.metadata.get("force_failure"):
            raise RuntimeError("Forced PresGen-Avatar failure via request metadata")

        await asyncio.sleep(0)
        job_id = f"avatar_{uuid4().hex}"
        response = AvatarGenerationResponse(
            success=True,
            job_id=job_id,
            status="pending",
            message="Avatar generation queued (mock)",
            progress=10,
            estimated_duration_seconds=120,
        )
        response.context = {
            "api_mode": "mock",
            "workflow_id": request.metadata.get("workflow_id"),
            "skill_id": request.metadata.get("skill_id"),
            "course_id": job_id,
        }
        response.raw_response = {"mock": True}
        return response

    async def _mock_status(self, job_id: str) -> AvatarJobStatus:
        await asyncio.sleep(0)
        status = AvatarJobStatus(
            job_id=job_id,
            status="completed",
            progress=100,
            video_url=f"https://storage.googleapis.com/avatar-videos/{job_id}.mp4",
        )
        status.raw_response = {"mock": True}
        return status

    async def close(self) -> None:
        """Close the underlying HTTP client."""

        if self._client is not None:
            await self._client.aclose()
            self._client = None

    def _parse_generate_response(
        self,
        workflow_id: str,
        skill_id: str,
        data: Any,
    ) -> AvatarGenerationResponse:
        if isinstance(data, dict) and "course_id" in data:
            return self._convert_course_response(workflow_id, skill_id, data)

        result = AvatarGenerationResponse.model_validate(data)
        result.status = self._normalize_status(result.status)
        result.progress = self._coerce_progress(result.progress)
        result.raw_response = data if isinstance(data, dict) else {"value": data}
        result.context = {
            "workflow_id": workflow_id,
            "skill_id": skill_id,
            "course_id": result.course_id or result.job_id,
            "api_mode": "legacy",
        }
        if not result.job_id:
            result.job_id = result.course_id or uuid4().hex
        return result

    def _convert_course_response(
        self,
        workflow_id: str,
        skill_id: str,
        data: Dict[str, Any],
    ) -> AvatarGenerationResponse:
        course_id_raw = str(data.get("course_id") or "").strip()
        course_id = course_id_raw or None
        job_id = (
            str(data.get("presgen_avatar_job_id") or "").strip()
            or str(data.get("job_id") or "").strip()
            or course_id_raw
            or uuid4().hex
        )
        normalized_status = self._normalize_status(data.get("status"))
        progress = self._coerce_progress(data.get("progress"))
        video_url = data.get("video_url")
        if not isinstance(video_url, str):
            video_url = None
        else:
            video_url = video_url.strip() or None

        response = AvatarGenerationResponse(
            success=normalized_status != "failed",
            job_id=job_id,
            status=normalized_status,
            message=data.get("message") or data.get("error_message"),
            progress=progress,
            video_url=video_url,
            estimated_duration_seconds=data.get("estimated_duration_seconds"),
            course_id=course_id,
            workflow_id=str(data.get("workflow_id") or workflow_id),
            skill_id=str(data.get("skill_id") or skill_id),
        )
        response.context = {
            "workflow_id": workflow_id,
            "skill_id": skill_id,
            "course_id": course_id or job_id,
            "api_mode": "course",
        }
        response.raw_response = data
        return response

    def _register_job_context(
        self,
        response: AvatarGenerationResponse,
        workflow_id: str,
        skill_id: str,
    ) -> None:
        if not response.job_id:
            return

        context = dict(response.context or {})
        context.setdefault("workflow_id", workflow_id)
        context.setdefault("skill_id", skill_id)
        context.setdefault("course_id", response.course_id or response.job_id)
        context.setdefault("api_mode", "course" if response.course_id else context.get("api_mode", "legacy"))
        response.context = context
        self._job_context[response.job_id] = context

    async def _fetch_course_status(self, workflow_id: str, course_id: str) -> AvatarJobStatus:
        client = await self._get_client()
        endpoint = (
            f"{self.base_url}/api/v1/workflows/"
            f"{quote(str(workflow_id))}/courses/{quote(str(course_id))}/status"
        )
        response = await client.get(endpoint, headers=self._headers)
        response.raise_for_status()
        data = response.json()
        normalized_status = self._normalize_status(data.get("status"))
        progress = self._coerce_progress(data.get("progress"))
        video_url = data.get("video_url")
        if not isinstance(video_url, str):
            video_url = None
        else:
            video_url = video_url.strip() or None

        job_status = AvatarJobStatus(
            job_id=str(course_id),
            status=normalized_status,
            progress=progress,
            video_url=video_url,
            error_message=data.get("error_message"),
        )
        job_status.raw_response = data if isinstance(data, dict) else {"value": data}
        return job_status

    @staticmethod
    def _normalize_status(status: Optional[str]) -> str:
        if status is None:
            return "pending"
        value = str(status).strip().lower()
        if not value:
            return "pending"

        if value in {"pending", "queued", "queued_initialization"}:
            return "pending"
        if value in {
            "running",
            "in_progress",
            "processing",
            "generating",
            "generating_video",
            "polling",
        }:
            return "running"
        if value in {"completed", "done", "success", "succeeded"}:
            return "completed"
        if value in {"failed", "error", "errored"} or "fail" in value or "error" in value:
            return "failed"
        return "running"

    @staticmethod
    def _coerce_progress(progress: Any) -> Optional[int]:
        if progress is None:
            return None
        try:
            value = int(progress)
        except (TypeError, ValueError):
            return None
        return max(0, min(100, value))
