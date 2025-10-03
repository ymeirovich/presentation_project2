"""
PresGen-Core Client for Sprint 3

HTTP client for PresGen-Core presentation generation service.
Includes mock implementation for testing without PresGen-Core dependency.
"""

import logging
import asyncio
from typing import Optional, Callable, Any
from datetime import datetime
from uuid import uuid4

from src.schemas.presentation import PresentationContentSpec
from src.common.config import settings

logger = logging.getLogger(__name__)


class PresentationResult:
    """Result from PresGen-Core presentation generation."""

    def __init__(self, **kwargs):
        self.presentation_url = kwargs.get("presentation_url")
        self.file_data = kwargs.get("file_data")
        self.slide_count = kwargs.get("slide_count", 0)
        self.thumbnail_url = kwargs.get("thumbnail_url")
        self.generation_duration_ms = kwargs.get("generation_duration_ms", 0)


class DriveResult:
    """Result from Google Drive save operation."""

    def __init__(self, **kwargs):
        self.file_id = kwargs.get("file_id")
        self.folder_id = kwargs.get("folder_id")
        self.download_url = kwargs.get("download_url")
        self.file_size_mb = kwargs.get("file_size_mb", 0.0)


class PresGenCoreClient:
    """
    Client for PresGen-Core presentation generation service.

    Sprint 3: Mock implementation for testing.
    Production: Replace with actual HTTP client to PresGen-Core API.
    """

    def __init__(self, base_url: Optional[str] = None, api_key: Optional[str] = None):
        self.base_url = base_url or settings.presgen_core_url
        self.api_key = api_key
        self.timeout = 600.0  # 10 minutes for long-running generation

        # Use mock mode in debug mode, production mode otherwise
        # Can be overridden with PRESGEN_USE_MOCK environment variable
        if settings.presgen_use_mock is not None:
            self.use_mock = settings.presgen_use_mock
        else:
            self.use_mock = settings.debug

        logger.info(
            f"🔧 PresGenCoreClient initialized | "
            f"base_url={self.base_url} | "
            f"mock_mode={self.use_mock} | "
            f"debug={settings.debug}"
        )

    async def generate_presentation(
        self,
        content_spec: PresentationContentSpec,
        progress_callback: Optional[Callable[[int, str], None]] = None
    ) -> PresentationResult:
        """
        Generate presentation using PresGen-Core.

        Sprint 3: Mock implementation simulates presentation generation.

        Args:
            content_spec: Content specification for ONE skill presentation
            progress_callback: Optional callback for progress updates

        Returns:
            PresentationResult with presentation URL and metadata
        """
        logger.info(
            f"🎨 {'[MOCK] ' if self.use_mock else ''}Generating presentation | "
            f"skill={content_spec.skill_name} | "
            f"template={content_spec.template_type}"
        )

        if self.use_mock:
            return await self._mock_generate_presentation(content_spec, progress_callback)

        # TODO: Implement actual PresGen-Core API call
        # async with httpx.AsyncClient(timeout=self.timeout) as client:
        #     response = await client.post(
        #         f"{self.base_url}/api/v1/presentations/generate",
        #         json=content_spec.dict(),
        #         headers={
        #             "Authorization": f"Bearer {self.api_key}",
        #             "Content-Type": "application/json"
        #         }
        #     )
        #     response.raise_for_status()
        #     result_data = response.json()
        #     return PresentationResult(**result_data)

    async def _mock_generate_presentation(
        self,
        content_spec: PresentationContentSpec,
        progress_callback: Optional[Callable[[int, str], None]] = None
    ) -> PresentationResult:
        """
        Mock presentation generation for testing.

        Simulates:
        - 3-7 minute generation time (simulated with short delays)
        - Progress updates
        - Realistic slide counts (7-11 slides)
        """
        start_time = datetime.utcnow()

        # Simulate generation steps with progress updates
        steps = [
            (20, "Analyzing content"),
            (40, "Generating slide structure"),
            (60, "Creating slide content"),
            (80, "Formatting slides"),
            (100, "Finalizing presentation")
        ]

        for progress, step_name in steps:
            if progress_callback:
                await progress_callback(progress, step_name)

            # Simulate processing time (short delay for testing)
            await asyncio.sleep(0.2)  # 0.2 seconds per step = 1 second total

        # Generate mock slide count (7-11 slides for short-form)
        slide_count = 7 + (len(content_spec.skill_name) % 5)  # Pseudo-random 7-11

        # Calculate duration
        end_time = datetime.utcnow()
        duration_ms = int((end_time - start_time).total_seconds() * 1000)

        # Generate mock Google Slides URL
        mock_presentation_id = str(uuid4())[:8]
        presentation_url = f"https://docs.google.com/presentation/d/{mock_presentation_id}/edit"

        logger.info(
            f"✅ [MOCK] Presentation generated | "
            f"slides={slide_count} | "
            f"duration={duration_ms}ms | "
            f"url={presentation_url}"
        )

        return PresentationResult(
            presentation_url=presentation_url,
            file_data=b"",  # Mock empty file data
            slide_count=slide_count,
            thumbnail_url=f"https://docs.google.com/presentation/d/{mock_presentation_id}/thumbnail",
            generation_duration_ms=duration_ms
        )

    async def save_to_drive(
        self,
        file_data: bytes,
        folder_path: str,
        file_name: Optional[str] = None
    ) -> DriveResult:
        """
        Save presentation to Google Drive.

        Sprint 3: Mock implementation simulates Drive upload.

        Args:
            file_data: Presentation file data (empty in mock)
            folder_path: Drive folder path (e.g., "Assessments/AWS_SA_user@email.com_123/Presentations/EC2/")
            file_name: Optional file name (auto-generated if not provided)

        Returns:
            DriveResult with file ID and download URL
        """
        logger.info(f"💾 {'[MOCK] ' if self.use_mock else ''}Saving to Drive | path={folder_path}")

        if self.use_mock:
            return await self._mock_save_to_drive(file_data, folder_path, file_name)

        # TODO: Implement actual Google Drive API call
        # from googleapiclient.discovery import build
        # service = build('drive', 'v3', credentials=creds)
        # ...

    async def _mock_save_to_drive(
        self,
        file_data: bytes,
        folder_path: str,
        file_name: Optional[str] = None
    ) -> DriveResult:
        """Mock Drive save operation for testing."""

        # Simulate upload time
        await asyncio.sleep(0.1)

        # Generate mock IDs
        mock_file_id = str(uuid4())[:16]
        mock_folder_id = str(uuid4())[:16]

        # Generate mock URLs
        download_url = f"https://drive.google.com/file/d/{mock_file_id}/export?format=pptx"

        # Estimate file size (mock: 2-4 MB for short-form presentation)
        file_size_mb = 2.0 + (len(folder_path) % 20) / 10.0  # Pseudo-random 2.0-3.9 MB

        logger.info(
            f"✅ [MOCK] Saved to Drive | "
            f"file_id={mock_file_id} | "
            f"size={file_size_mb:.1f}MB | "
            f"path={folder_path}"
        )

        return DriveResult(
            file_id=mock_file_id,
            folder_id=mock_folder_id,
            download_url=download_url,
            file_size_mb=file_size_mb
        )

    def build_drive_folder_path(
        self,
        assessment_title: str,
        user_email: Optional[str],
        workflow_id: str,
        skill_name: str
    ) -> str:
        """
        Build human-readable Google Drive folder path.

        Format:
        - With email: Assessments/{assessment_title}_{user_email}_{workflow_id}/Presentations/{skill_name}/
        - Without email: Assessments/{assessment_title}_{workflow_id}/Presentations/{skill_name}/

        Example:
        - Assessments/AWS_Solutions_Architect_john.doe@company.com_123e4567/Presentations/EC2_Instance_Types/
        """
        # Sanitize components for folder naming
        safe_title = assessment_title.replace(" ", "_").replace("/", "-")
        safe_skill = skill_name.replace(" ", "_").replace("/", "-")
        short_workflow_id = str(workflow_id)[:8]  # First 8 chars for brevity

        if user_email:
            # Include user email in folder name
            base_folder = f"{safe_title}_{user_email}_{short_workflow_id}"
        else:
            # Omit user email
            base_folder = f"{safe_title}_{short_workflow_id}"

        return f"Assessments/{base_folder}/Presentations/{safe_skill}/"
