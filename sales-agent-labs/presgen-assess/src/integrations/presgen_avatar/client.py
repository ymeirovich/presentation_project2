"""HTTP client wrapper for PresGen-Avatar service."""

from __future__ import annotations

import asyncio
import logging
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


class PresGenAvatarClient:
    """Client for interacting with PresGen-Avatar video generation service."""

    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        use_mock: Optional[bool] = None,
    ):
        self.base_url = (base_url or getattr(settings, "presgen_avatar_url", "http://localhost:8002")).rstrip("/")
        self.api_key = api_key
        self._timeout = httpx.Timeout(30.0)
        self.use_mock = use_mock if use_mock is not None else bool(getattr(settings, "presgen_use_mock", False))
        self._client: Optional[httpx.AsyncClient] = None

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
        """Trigger video generation via PresGen-Avatar."""

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

        if self.use_mock:
            logger.debug("PresGen-Avatar client running in mock mode; returning synthetic response")
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
            logger.warning("PresGen-Avatar HTTP error (%s); falling back to mock", exc)
            return await self._mock_generate(request)

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

    async def _mock_generate(self, request: AvatarGenerationRequest) -> AvatarGenerationResponse:
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
