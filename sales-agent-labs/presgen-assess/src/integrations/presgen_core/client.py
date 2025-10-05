"""HTTP client wrapper for PresGen-Core presentation service."""

from __future__ import annotations

import asyncio
from typing import Optional
from uuid import uuid4

import httpx

from src.common.config import settings
from .schemas import PresGenPresentationRequest, PresGenPresentationResponse


class PresGenCoreClient:
    """Client for PresGen-Core presentation generation.

    Currently returns mock responses so local development does not require the
    external service. Swap implementation with real HTTP calls when the
    PresGen-Core endpoint is available.
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
    ):
        self.base_url = base_url or getattr(settings, 'presgen_core_url', 'http://localhost:8080')
        self.api_key = api_key
        self._timeout = httpx.Timeout(30.0)

    async def generate_presentation(self, request: PresGenPresentationRequest) -> PresGenPresentationResponse:
        """Generate presentation for a skill (mock implementation)."""

        payload = request.model_dump(mode="json")

        # TODO: swap to real HTTP call once service is available
        await asyncio.sleep(0)  # yield control for cooperative scheduling
        job_id = f"core_{uuid4().hex}"
        slide_count = max(8, min(20, request.target_duration_minutes + 5))
        presentation_url = f"https://drive.google.com/presentation/d/{job_id}/edit"
        return PresGenPresentationResponse(
            success=True,
            job_id=job_id,
            presentation_url=presentation_url,
            slide_count=slide_count,
            message="Presentation generated (mock)",
            prompt_used=payload.get("custom_prompt"),
        )

    async def _post(self, path: str, payload: dict) -> httpx.Response:
        """Reserved for future real integration HTTP call."""
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            return await client.post(f"{self.base_url}{path}", json=payload, headers=headers)
