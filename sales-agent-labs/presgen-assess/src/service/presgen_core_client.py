"""
PresGen-Core Client for Sprint 3

HTTP client for PresGen-Core presentation generation service.
Includes mock implementation for testing without PresGen-Core dependency.
"""

import logging
import asyncio
import aiohttp
import sys
from pathlib import Path
from typing import Optional, Callable, Any, List, Dict
from datetime import datetime
from uuid import uuid4
import os

# Add sales-agent-labs directory to path for Google Slides imports
# This file is at: .../sales-agent-labs/presgen-assess/src/service/presgen_core_client.py
# We need: .../sales-agent-labs/ (one level up from presgen-assess) to import src.agent.slides_google
presgen_assess_dir = Path(__file__).parent.parent.parent.parent
sales_agent_labs_dir = presgen_assess_dir.parent
if str(sales_agent_labs_dir) not in sys.path:
    sys.path.insert(0, str(sales_agent_labs_dir))

from src.schemas.presentation import PresentationContentSpec
from src.common.config import settings
from src.services.course_generation_service import log_course_event

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
        if not self.use_mock and not self._slides_module_available():
            logger.warning(
                "Slides integration module missing; falling back to mock PresGen-Core implementation."
            )
            self.use_mock = True

        logger.info(
            f"🎨 {'[MOCK] ' if self.use_mock else ''}Generating presentation | "
            f"skill={content_spec.skill_name} | "
            f"template={content_spec.template_type}"
        )

        if self.use_mock:
            return await self._mock_generate_presentation(content_spec, progress_callback)

        # Production mode: Call actual PresGen-Core API
        return await self._production_generate_presentation(content_spec, progress_callback)

    async def _production_generate_presentation(
        self,
        content_spec: PresentationContentSpec,
        progress_callback: Optional[Callable[[int, str], None]] = None
    ) -> PresentationResult:
        """
        Production mode: Full workflow for presentation generation.

        Workflow:
        1. Create Google Slides presentation (0-30%)
        2. Upload to Drive with public permissions (30-40%)
        3. Generate video with PresGen-Core /training/presentation-only (40-90%)
        4. Return presentation URL and video URL (90-100%)
        """
        start_time = datetime.utcnow()
        logger.info(
            "🎬 core_client_pipeline | stage=start | workflow_id=%s | skill_id=%s",
            getattr(content_spec, "workflow_id", "unknown"),
            getattr(content_spec, "skill_id", "unknown"),
        )

        # Helper to call progress callback (sync or async)
        async def call_progress(progress: int, step: str):
            if progress_callback:
                if asyncio.iscoroutinefunction(progress_callback):
                    await progress_callback(progress, step)
                else:
                    progress_callback(progress, step)

        presentation_id = presentation_url = None
        slide_plans: List[Dict[str, Any]] = []
        try:
            # ========== STEP 1: Create Google Slides Presentation ==========
            await call_progress(5, "Creating Google Slides presentation")

            # Import Google Slides module using helper to handle namespace collision
            import sys
            sys.path.insert(0, str(Path(__file__).parent.parent))  # Add src to path for common imports
            from common.google_slides_import_v2 import get_slides_google
            slides_google = get_slides_google()
            create_presentation = slides_google.create_presentation
            create_main_slide_with_content = slides_google.create_main_slide_with_content
            delete_default_slide = slides_google.delete_default_slide

            presentation_title = content_spec.title

            slide_plans = self._build_slide_plans(content_spec)

            outline_preview = " | ".join(
                f"{idx + 1}: {plan['title']}"
                for idx, plan in enumerate(slide_plans)
            ) if slide_plans else "No slides planned"

            log_course_event(
                "PRESGEN_SLIDE_OUTLINE_READY",
                workflow_id=str(getattr(content_spec, "workflow_id", "unknown")),
                skill_id=getattr(content_spec, "skill_id", "unknown"),
                slide_count=len(slide_plans),
                outline_preview=outline_preview[:500]
            )

            logger.info("📊 Creating Google Slides | title=%s | slides=%s", presentation_title, len(slide_plans))

            presentation_id, presentation_url = create_presentation(
                title=presentation_title,
                content=presentation_title,
            )

            try:
                delete_default_slide(presentation_id)
            except Exception as exc:  # pylint: disable=broad-except
                logger.warning("⚠️ Failed to delete default slide: %s", exc)

            for plan in slide_plans:
                try:
                    create_main_slide_with_content(
                        presentation_id,
                        title=plan["title"],
                        subtitle=plan.get("subtitle", ""),
                        bullets=plan.get("bullets", []),
                        image_url=None,
                        script=plan.get("script", ""),
                    )
                except Exception as exc:  # pylint: disable=broad-except
                    logger.warning(
                        "⚠️ Failed to create slide '%s': %s",
                        plan.get("title"),
                        exc,
                    )

            await call_progress(30, "Google Slides created")
            logger.info("✅ Slides created | id=%s | url=%s", presentation_id, presentation_url)

            # ========== STEP 2: Set public permissions ==========
            await call_progress(35, "Setting public permissions")

            _load_credentials = slides_google._load_credentials
            from googleapiclient.discovery import build

            creds = _load_credentials()
            drive_service = build("drive", "v3", credentials=creds)

            drive_service.permissions().create(
                fileId=presentation_id,
                body={"type": "anyone", "role": "reader"},
            ).execute()

            await call_progress(40, "Public permissions set")
            logger.info("🌐 Presentation is now public | url=%s", presentation_url)

            # ========== STEP 3: Generate video with PresGen-Core ==========
            await call_progress(45, "Generating presentation video")

            # Prepare payload for PresGen-Avatar via /training/presentation-only
            # Using OpenAI voice profile for TTS
            training_payload = {
                "mode": "presentation_only",
                "voice_profile_name": "OpenAI Demo Voice (Your Audio)",  # OpenAI TTS voice
                "google_slides_url": presentation_url,
                "quality_level": "fast",  # Fast mode for quick generation
                "slide_count": len(slide_plans),
            }

            api_url = f"{self.base_url}/training/presentation-only"
            logger.info(f"🎥 Calling PresGen-Core video generation | url={api_url}")

            # Make HTTP request to PresGen-Core
            timeout = aiohttp.ClientTimeout(total=self.timeout)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                headers = {
                    "Content-Type": "application/json"
                }
                if self.api_key:
                    headers["Authorization"] = f"Bearer {self.api_key}"

                # Progress update: Sending request
                await call_progress(50, "Requesting video generation")

                async with session.post(api_url, json=training_payload, headers=headers) as response:
                    # Progress update: Waiting for response
                    await call_progress(60, "Generating presentation video")

                    # Check response status
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(
                            f"❌ PresGen-Core API error | status={response.status} | error={error_text}"
                        )
                        raise Exception(f"PresGen-Core API returned {response.status}: {error_text}")

                    # Parse response
                    result_data = await response.json()

                    # Progress update: Processing response
                    await call_progress(85, "Processing video result")

                    # PresGen-Core /training/presentation-only returns TrainingVideoResponse:
                    # { job_id, success, output_path, download_url, processing_time, mode, error, ... }
                    success = result_data.get("success", False)
                    video_output_path = result_data.get("output_path")  # Path to generated .mp4 file
                    download_url = result_data.get("download_url")
                    error = result_data.get("error")
                    processing_time = result_data.get("processing_time", 0)

                    if not success or error:
                        # Video generation failed, but we still have the Google Slides
                        logger.warning(f"⚠️ Video generation failed: {error}")
                        logger.info(f"📊 Google Slides still available at: {presentation_url}")

                    # Calculate actual duration
                    end_time = datetime.utcnow()
                    actual_duration_ms = int((end_time - start_time).total_seconds() * 1000)

                    # Log success
                    logger.info(
                        f"✅ Presentation workflow complete | "
                        f"slides_url={presentation_url} | "
                        f"video_path={video_output_path} | "
                        f"video_success={success} | "
                        f"duration={actual_duration_ms}ms"
                    )
                    logger.info(
                        "🎬 core_client_pipeline | stage=complete | workflow_id=%s | skill_id=%s | slides_url=%s | duration_ms=%s",
                        getattr(content_spec, "workflow_id", "unknown"),
                        getattr(content_spec, "skill_id", "unknown"),
                        presentation_url,
                        actual_duration_ms,
                    )

                    # Final progress update
                    await call_progress(100, "Presentation complete")

                    # Return result with Google Slides URL (always available) and video info
                    return PresentationResult(
                        presentation_url=presentation_url,  # Google Slides URL
                        file_data=b"",  # Don't load large video files into memory
                        slide_count=len(slide_plans) if slide_plans else 1,
                        thumbnail_url=None,
                        generation_duration_ms=actual_duration_ms
                    )

        except asyncio.TimeoutError:
            logger.error(f"⏱️ PresGen-Core API timeout after {self.timeout}s")
            raise Exception(f"Presentation generation timed out after {self.timeout} seconds")

        except aiohttp.ClientError as e:
            logger.error(f"🔌 PresGen-Core connection error | error={str(e)}")
            raise Exception(f"Failed to connect to PresGen-Core: {str(e)}")

        except Exception as e:
            logger.error(f"❌ PresGen-Core generation failed | error={str(e)}", exc_info=True)
            raise

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

    def _slides_module_available(self) -> bool:
        """Return True if the PresGen slides integration module can be imported."""
        try:
            from importlib import import_module

            import_module("src.agent.slides_google")
            return True
        except ModuleNotFoundError:
            return False

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
    def _build_slide_plans(self, content_spec: PresentationContentSpec) -> List[Dict[str, Any]]:
        """Derive a slide plan (title, bullets, presenter notes) from the content spec."""

        def _clean_list(values: Optional[List[str]]) -> List[str]:
            if not values:
                return []
            cleaned = []
            for value in values:
                if value is None:
                    continue
                text = str(value).strip()
                if text:
                    cleaned.append(text)
            return cleaned

        plans: List[Dict[str, Any]] = []
        target = max(1, min(content_spec.target_slide_count or 12, 40))

        learning_objectives = _clean_list(content_spec.learning_objectives)
        sections = content_spec.content_outline.get("sections", []) if isinstance(content_spec.content_outline, dict) else []
        content_items = content_spec.content_outline.get("content_items", []) if isinstance(content_spec.content_outline, dict) else []

        def add_plan(title: str, subtitle: str = "", bullets: Optional[List[str]] = None, script: str = "") -> None:
            bullet_list = _clean_list(bullets) if bullets else []
            plans.append({
                "title": title.strip() or "Untitled Slide",
                "subtitle": subtitle.strip() if subtitle else "",
                "bullets": bullet_list,
                "script": (script.strip() or title.strip() or "Presenter notes unavailable."),
            })

        # Title / overview slide
        overview_points = learning_objectives[:3] or [f"Why {content_spec.skill_name} matters"]
        add_plan(
            title=content_spec.title,
            subtitle=content_spec.subtitle or content_spec.assessment_title,
            bullets=overview_points,
            script=(
                f"Welcome to this session on {content_spec.skill_name}. "
                f"We will focus on {', '.join(overview_points)}."
            ),
        )

        # Gap summary slide
        skill_gap = content_spec.skill_gap or {}
        bullets = []
        if skill_gap.get("severity") is not None:
            bullets.append(f"Gap severity: {skill_gap['severity']}/10")
        if skill_gap.get("confidence_delta") is not None:
            bullets.append(f"Confidence delta: {skill_gap['confidence_delta']}")
        if learning_objectives:
            bullets.append("Priority objectives: " + ", ".join(learning_objectives[:3]))
        add_plan(
            title="Current Skill Snapshot",
            subtitle=content_spec.skill_name,
            bullets=bullets or ["Review current performance and target outcomes."],
            script=skill_gap.get("summary")
            or skill_gap.get("description")
            or f"We will address the critical gaps in {content_spec.skill_name} and map remediation steps.",
        )

        objective_queue = learning_objectives.copy()
        section_queue = list(sections) if isinstance(sections, list) else []
        item_queue = list(content_items) if isinstance(content_items, list) else []

        def _objective_plan(objective: str) -> None:
            add_plan(
                title=objective,
                subtitle="Learning objective",
                bullets=[
                    "Clarify the core concept",
                    "Connect theory to practical implementation",
                    "Identify resources to reinforce learning",
                ],
                script=f"In this segment we will focus on the objective '{objective}' and how to demonstrate proficiency.",
            )

        def _section_plan(section: Dict[str, Any]) -> None:
            title = str(section.get("title") or "Key Section").strip()
            duration = section.get("duration_minutes")
            bullets = []
            if duration:
                bullets.append(f"Estimated focus time: {duration} minutes")
            bullets.extend([
                "Highlight foundational knowledge",
                "Discuss implementation considerations",
                "Note common pitfalls and exam tips",
            ])
            add_plan(
                title=title,
                subtitle="Section focus",
                bullets=bullets,
                script=f"This section explores {title.lower()} with guidance on how to master it for certification success.",
            )

        def _content_item_plan(item: Dict[str, Any]) -> None:
            topic = (item.get("topic") or item.get("title") or "Key Concept").strip()
            source = (item.get("source") or "Reference material").strip()
            key_points = item.get("key_points")
            bullets = _clean_list(key_points if isinstance(key_points, list) else None)
            summary = (item.get("summary") or item.get("description") or "Explain why this concept matters.").strip()
            if not bullets:
                sentences = [seg.strip() for seg in summary.replace("\n", " ").split('.') if seg.strip()]
                bullets = sentences[:3] if sentences else [summary]
            add_plan(
                title=topic,
                subtitle=f"Source: {source}" if source else "",
                bullets=bullets,
                script=summary,
            )

        while len(plans) < target:
            if objective_queue:
                _objective_plan(objective_queue.pop(0))
            elif item_queue:
                _content_item_plan(item_queue.pop(0))
            elif section_queue:
                _section_plan(section_queue.pop(0))
            else:
                add_plan(
                    title="Review & Next Steps",
                    subtitle=content_spec.skill_name,
                    bullets=[
                        "Summarize key insights",
                        "Plan immediate practice tasks",
                        "Schedule follow-up assessment",
                    ],
                    script="Consolidate what we learned and outline concrete next actions for continued progress.",
                )

        # Ensure we don't exceed the target (rare if loops add exactly one per iteration)
        return plans[:target]
