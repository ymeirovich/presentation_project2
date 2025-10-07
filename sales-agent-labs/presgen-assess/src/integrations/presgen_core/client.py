"""HTTP client wrapper for PresGen-Core presentation service."""

from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime, timedelta
from typing import Optional
from uuid import uuid4

import httpx

from src.common.config import settings
from .schemas import PresGenPresentationRequest, PresGenPresentationResponse


logger = logging.getLogger("presgen_core_client")


class CircuitOpenError(RuntimeError):
    """Raised when the circuit breaker is open for the client."""


class PresGenCoreClient:
    """Client for PresGen-Core presentation generation with retry + circuit breaker."""

    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        max_attempts: int = 3,
        base_backoff_seconds: float = 1.0,
        failure_threshold: int = 3,
        recovery_seconds: int = 60,
    ) -> None:
        self.base_url = base_url or getattr(settings, "presgen_core_url", "http://localhost:8080")
        self.api_key = api_key
        self._timeout = httpx.Timeout(30.0)

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

        payload = request.model_dump(mode="json")
        last_exc: Optional[Exception] = None

        for attempt in range(1, self._max_attempts + 1):
            self._ensure_circuit_closed()
            try:
                response = await self._mock_generate(request, payload)
                self._reset_failure_state()
                return response
            except Exception as exc:  # pylint: disable=broad-except
                last_exc = exc
                self._record_failure(exc)
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
        payload: dict,
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
