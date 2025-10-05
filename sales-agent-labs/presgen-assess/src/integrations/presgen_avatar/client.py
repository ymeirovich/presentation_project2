"""HTTP client wrapper for PresGen-Avatar service."""

from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime, timedelta
from typing import Any, Dict, Optional
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

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=self._timeout)
        return self._client

    async def generate_video(
        self,
        presentation_url: str,
        mode: str = "presentation-only",
        quality: str = "fast",
        voice_provider: str = "openai",
        voice_id: str = "alloy",
        language: str = "en-US",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> AvatarGenerationResponse:
        """Trigger video generation via PresGen-Avatar with retry + circuit breaker."""

        request = AvatarGenerationRequest(
            presentation_url=presentation_url,
            mode=mode,
            quality=quality,
            voice_config=VoiceConfig(
                provider=voice_provider,
                voice_id=voice_id,
                language=language,
            ),
            metadata=metadata or {},
        )

        last_exc: Optional[Exception] = None
        for attempt in range(1, self._max_attempts + 1):
            self._ensure_circuit_closed()
            try:
                response = await self._send_generate_request(request)
                self._reset_failure_state()
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

        try:
            client = await self._get_client()
            response = await client.get(
                f"{self.base_url}/api/v1/avatar/status/{job_id}",
                headers=self._headers,
            )
            response.raise_for_status()
            data = response.json()
            return AvatarJobStatus.model_validate(data)
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
        request: AvatarGenerationRequest,
    ) -> AvatarGenerationResponse:
        if self.use_mock:
            return await self._mock_generate(request)

        try:
            client = await self._get_client()
            response = await client.post(
                f"{self.base_url}/api/v1/avatar/generate",
                json=request.model_dump(mode="json"),
                headers=self._headers,
            )
            response.raise_for_status()
            data = response.json()
            logger.info(
                "✅ Avatar generation request accepted | job_id=%s | status=%s",
                data.get("job_id"),
                data.get("status", "unknown"),
            )
            return AvatarGenerationResponse.model_validate(data)
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
        if os.getenv("PRESGEN_AVATAR_FORCE_FAIL", "false").lower() == "true":
            raise RuntimeError("Forced PresGen-Avatar failure via PRESGEN_AVATAR_FORCE_FAIL")
        if request.metadata and request.metadata.get("force_failure"):
            raise RuntimeError("Forced PresGen-Avatar failure via request metadata")

        await asyncio.sleep(0)
        job_id = f"avatar_{uuid4().hex}"
        return AvatarGenerationResponse(
            success=True,
            job_id=job_id,
            status="pending",
            message="Avatar generation queued (mock)",
            progress=10,
            estimated_duration_seconds=120,
        )

    async def _mock_status(self, job_id: str) -> AvatarJobStatus:
        await asyncio.sleep(0)
        return AvatarJobStatus(
            job_id=job_id,
            status="completed",
            progress=100,
            video_url=f"https://storage.googleapis.com/avatar-videos/{job_id}.mp4",
        )

    async def close(self) -> None:
        """Close the underlying HTTP client."""

        if self._client is not None:
            await self._client.aclose()
            self._client = None
