import httpx
import asyncio
from typing import Optional, Dict, Any
from pydantic import BaseModel
import logging
from datetime import datetime

logger = logging.getLogger("presgen_avatar_client")

class AvatarGenerationRequest(BaseModel):
    """Request to PresGen-Avatar for video generation"""
    presentation_url: str
    mode: str = "presentation-only"
    quality: str = "fast"
    voice_config: Dict[str, Any] = {
        "provider": "openai",
        "voice_id": "alloy"
    }

class AvatarGenerationResponse(BaseModel):
    """Response from PresGen-Avatar"""
    job_id: str
    status: str
    video_url: Optional[str] = None
    progress: int = 0
    estimated_completion_seconds: Optional[int] = None

class PresGenAvatarClient:
    """Client for PresGen-Avatar API"""

    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip('/')
        self.client = httpx.AsyncClient(timeout=30.0)
        logger.info(f"🎬 PresGenAvatarClient initialized | base_url={self.base_url}")

    async def generate_video(
        self,
        presentation_url: str,
        mode: str = "presentation-only",
        quality: str = "fast",
        voice_provider: str = "openai",
        voice_id: str = "alloy"
    ) -> AvatarGenerationResponse:
        """
        Submit presentation for avatar video generation

        Args:
            presentation_url: URL to the presentation file
            mode: Generation mode (presentation-only, custom-script, etc.)
            quality: Quality setting (fast, standard, high)
            voice_provider: Voice provider (openai, elevenlabs, etc.)
            voice_id: Voice ID for the provider

        Returns:
            AvatarGenerationResponse with job_id and initial status
        """
        request = AvatarGenerationRequest(
            presentation_url=presentation_url,
            mode=mode,
            quality=quality,
            voice_config={
                "provider": voice_provider,
                "voice_id": voice_id
            }
        )

        logger.info(
            f"🎬 Submitting avatar generation request | "
            f"presentation_url={presentation_url} | mode={mode} | quality={quality}"
        )

        response = await self.client.post(
            f"{self.base_url}/api/v1/avatar/generate",
            json=request.dict()
        )
        response.raise_for_status()

        result = AvatarGenerationResponse(**response.json())
        logger.info(f"✅ Avatar generation submitted | job_id={result.job_id} | status={result.status}")

        return result

    async def get_status(self, job_id: str) -> AvatarGenerationResponse:
        """
        Get status of avatar generation job

        Args:
            job_id: Job identifier

        Returns:
            AvatarGenerationResponse with current status and progress
        """
        logger.info(f"📊 Checking avatar job status | job_id={job_id}")

        response = await self.client.get(
            f"{self.base_url}/api/v1/avatar/status/{job_id}"
        )
        response.raise_for_status()

        result = AvatarGenerationResponse(**response.json())
        logger.info(
            f"📊 Avatar job status | job_id={job_id} | status={result.status} | "
            f"progress={result.progress}%"
        )

        return result

    async def poll_until_complete(
        self,
        job_id: str,
        max_wait_seconds: int = 900,
        poll_interval_seconds: int = 10
    ) -> AvatarGenerationResponse:
        """
        Poll job status until completion or timeout

        Args:
            job_id: Job identifier
            max_wait_seconds: Maximum time to wait (default 15 minutes)
            poll_interval_seconds: Time between status checks

        Returns:
            Final AvatarGenerationResponse
        """
        start_time = datetime.now()
        logger.info(
            f"⏳ Starting avatar job polling | job_id={job_id} | "
            f"max_wait={max_wait_seconds}s | interval={poll_interval_seconds}s"
        )

        while True:
            elapsed = (datetime.now() - start_time).total_seconds()
            if elapsed > max_wait_seconds:
                raise TimeoutError(f"Avatar generation timed out after {max_wait_seconds}s")

            status = await self.get_status(job_id)

            if status.status == "completed":
                logger.info(f"✅ Avatar generation completed | job_id={job_id} | video_url={status.video_url}")
                return status
            elif status.status == "failed":
                raise RuntimeError(f"Avatar generation failed | job_id={job_id}")

            logger.info(f"⏳ Still generating... | progress={status.progress}% | elapsed={elapsed:.0f}s")
            await asyncio.sleep(poll_interval_seconds)

    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()