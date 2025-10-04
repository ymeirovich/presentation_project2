"""
Background Job System for Sprint 3 Presentation Generation

Handles async presentation generation with progress tracking.
Sprint 3: Simple in-memory queue (upgrade to Celery/Redis for production).
"""

import logging
import asyncio
from typing import Dict, Optional, Any
from uuid import UUID, uuid4
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from src.schemas.presentation import PresentationStatus, PresentationJobStatus, PresentationContentSpec
from src.models.presentation import GeneratedPresentation
from src.service.presgen_core_client import PresGenCoreClient
from src.service.database import AsyncSessionLocal

logger = logging.getLogger(__name__)


class PresentationGenerationJob:
    """
    Background job for generating a single skill presentation.

    Handles:
    - Progress tracking (0-100%)
    - PresGen-Core API integration
    - Drive folder organization
    - Database persistence
    """

    def __init__(
        self,
        job_id: str,
        presentation_id: UUID,
        content_spec: PresentationContentSpec
    ):
        self.job_id = job_id
        self.presentation_id = presentation_id
        self.content_spec = content_spec
        self.db: Optional[AsyncSession] = None  # Created in execute()
        self.presgen_client = PresGenCoreClient()  # Uses mock by default

        self.progress = 0
        self.current_step = "Initializing"
        self.status = PresentationStatus.PENDING

    async def execute(self) -> None:
        """
        Execute the presentation generation job.

        Steps:
        1. Validate content spec (10%)
        2. Call PresGen-Core API (20-80%)
        3. Save to Drive (80-90%)
        4. Update database (90-100%)

        Creates its own database session for proper lifecycle management.
        Session is guaranteed to be closed even on errors.
        """
        # Create independent database session for this background job
        async with AsyncSessionLocal() as session:
            self.db = session

            try:
                logger.info(f"🎬 Starting presentation generation job {self.job_id}")

                await self._update_status(PresentationStatus.GENERATING, 0, "Starting generation")

                # Step 1: Validate content spec (10%)
                await self._update_progress(10, "Validating content specification")
                await asyncio.sleep(0.1)  # Small delay for testing

                # Step 2: Call PresGen-Core API (20-80%)
                await self._update_progress(20, "Generating slides")
                presentation_result = await self.presgen_client.generate_presentation(
                    self.content_spec,
                    progress_callback=self._presgen_progress_callback
                )

                # Build human-readable folder path (for metadata tracking)
                folder_path = self.presgen_client.build_drive_folder_path(
                    assessment_title=self.content_spec.assessment_title,
                    user_email=self.content_spec.user_email,
                    workflow_id=str(self.content_spec.workflow_id),
                    skill_name=self.content_spec.skill_name
                )

                # Production mode: Google Slides URL is already available (no separate Drive save needed)
                # Mock mode: Also returns mock URL (no file data to save)
                # Step 3: Update database (90-100%)
                await self._update_progress(90, "Finalizing")
                await self._finalize_presentation(presentation_result, folder_path)

                await self._update_status(PresentationStatus.COMPLETED, 100, "Generation complete")

                logger.info(
                    f"✅ Presentation generation complete | "
                    f"job_id={self.job_id} | "
                    f"presentation_id={self.presentation_id} | "
                    f"slides={presentation_result.slide_count}"
                )

            except Exception as e:
                logger.error(f"❌ Presentation generation failed: {e}", exc_info=True)
                try:
                    # Attempt to update status to failed
                    await self._update_status(
                        PresentationStatus.FAILED,
                        self.progress,
                        f"Generation failed: {str(e)}",
                        error_message=str(e)
                    )
                except Exception as update_error:
                    logger.error(f"❌ Failed to update error status: {update_error}")
                raise
            finally:
                # Session automatically closed by context manager
                self.db = None
                logger.debug(f"🔒 Database session closed for job {self.job_id}")

    async def _update_status(
        self,
        status: PresentationStatus,
        progress: int,
        current_step: str,
        error_message: Optional[str] = None
    ) -> None:
        """Update job status in database."""
        self.status = status
        self.progress = progress
        self.current_step = current_step

        update_values = {
            "generation_status": status.value,
            "job_progress": progress,
            "updated_at": datetime.utcnow()
        }

        if status == PresentationStatus.GENERATING and progress == 0:
            update_values["generation_started_at"] = datetime.utcnow()
        elif status in [PresentationStatus.COMPLETED, PresentationStatus.FAILED]:
            update_values["generation_completed_at"] = datetime.utcnow()

        if error_message:
            update_values["job_error_message"] = error_message

        stmt = update(GeneratedPresentation).where(
            GeneratedPresentation.id == str(self.presentation_id)
        ).values(**update_values)

        await self.db.execute(stmt)
        await self.db.commit()

    async def _update_progress(self, progress: int, step: str) -> None:
        """Update job progress."""
        await self._update_status(self.status, progress, step)

    async def _presgen_progress_callback(self, progress: int, step: str) -> None:
        """Callback for PresGen-Core progress updates (maps 0-100% to 20-80%)."""
        adjusted_progress = 20 + int(progress * 0.6)
        await self._update_progress(adjusted_progress, step)

    async def _finalize_presentation(
        self,
        presentation_result: Any,
        folder_path: str
    ) -> None:
        """Finalize presentation record in database."""

        # Calculate duration
        stmt = select(GeneratedPresentation.generation_started_at).where(
            GeneratedPresentation.id == str(self.presentation_id)
        )
        result = await self.db.execute(stmt)
        started_at_str = result.scalar_one()

        if started_at_str:
            started_at = datetime.fromisoformat(started_at_str) if isinstance(started_at_str, str) else started_at_str
            duration_ms = int((datetime.utcnow() - started_at).total_seconds() * 1000)
        else:
            duration_ms = 0

        # Estimate duration in minutes (3-7 minutes)
        estimated_minutes = duration_ms // 60000 or 5  # Default 5 minutes

        # Production workflow: Google Slides URL is returned directly (with public permissions)
        # The presentation_url IS the shareable Google Slides URL
        update_values = {
            "presentation_url": presentation_result.presentation_url,
            "drive_folder_path": folder_path,
            "total_slides": presentation_result.slide_count,
            "thumbnail_url": presentation_result.thumbnail_url,
            "generation_duration_ms": duration_ms,
            "estimated_duration_minutes": estimated_minutes
        }

        # Optional: Extract file_id from Google Slides URL for reference
        # Example URL: https://docs.google.com/presentation/d/{file_id}/edit
        if presentation_result.presentation_url:
            parts = presentation_result.presentation_url.split('/')
            if len(parts) > 5 and parts[3] == 'presentation':
                file_id = parts[5]
                update_values["drive_file_id"] = file_id

        update_stmt = update(GeneratedPresentation).where(
            GeneratedPresentation.id == str(self.presentation_id)
        ).values(**update_values)

        await self.db.execute(update_stmt)
        await self.db.commit()


class JobQueue:
    """
    Simple in-memory job queue for presentation generation.

    Sprint 3: In-memory implementation (replace with Celery/RQ for production).

    Supports:
    - Job enqueueing
    - Status tracking
    - Background execution
    """

    def __init__(self):
        self.jobs: Dict[str, PresentationGenerationJob] = {}

    async def enqueue(
        self,
        presentation_id: UUID,
        content_spec: PresentationContentSpec
    ) -> str:
        """
        Enqueue a new presentation generation job.

        The job will create its own database session for proper lifecycle management.

        Args:
            presentation_id: ID of presentation record
            content_spec: Content specification for this skill

        Returns:
            job_id: Unique job identifier
        """
        job_id = str(uuid4())

        job = PresentationGenerationJob(
            job_id=job_id,
            presentation_id=presentation_id,
            content_spec=content_spec
        )

        self.jobs[job_id] = job

        # Start job in background (use Celery/RQ in production)
        # Job will create its own database session
        asyncio.create_task(job.execute())

        logger.info(
            f"📝 Enqueued presentation generation job {job_id} | "
            f"skill={content_spec.skill_name}"
        )

        return job_id

    def get_job_status(self, job_id: str) -> Optional[PresentationJobStatus]:
        """Get status of a job."""
        job = self.jobs.get(job_id)
        if not job:
            return None

        return PresentationJobStatus(
            job_id=job.job_id,
            presentation_id=job.presentation_id,
            status=job.status,
            progress=job.progress,
            current_step=job.current_step
        )

    def get_all_jobs(self) -> Dict[str, PresentationJobStatus]:
        """Get status of all jobs."""
        return {
            job_id: PresentationJobStatus(
                job_id=job.job_id,
                presentation_id=job.presentation_id,
                status=job.status,
                progress=job.progress,
                current_step=job.current_step
            )
            for job_id, job in self.jobs.items()
        }


# Global job queue instance (use Redis/Celery for production)
job_queue = JobQueue()
