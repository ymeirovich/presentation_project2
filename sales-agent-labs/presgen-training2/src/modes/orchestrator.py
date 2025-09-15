import time
import logging
import uuid
import os
from pathlib import Path
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from enum import Enum

# Use simple logging for now - can integrate with parent project later
def jlog(logger, level, event, **kwargs):
    """Simple logging wrapper"""
    logger.log(level, f"Event: {event}, Data: {kwargs}")
from core.liveportrait.avatar_engine import LivePortraitEngine, AvatarGenerationResult
from core.voice.voice_manager import VoiceProfileManager, VoiceProfile
from core.content.processor import ContentProcessor
from presentation.slides.google_slides_processor import GoogleSlidesProcessor, GoogleSlidesResult
from presentation.renderer.slides_to_video import SlidesToVideoRenderer, VideoRenderResult
from pipeline.appender.video_appender import VideoAppendingEngine, VideoSegment, VideoAppendResult

class OperationMode(Enum):
    """Three operation modes"""
    VIDEO_ONLY = "video_only"
    PRESENTATION_ONLY = "presentation_only"
    VIDEO_PRESENTATION = "video_presentation"

@dataclass
class GenerationRequest:
    """Request for video generation"""
    mode: OperationMode
    voice_profile_name: str
    quality_level: str = "standard"

    # Content inputs
    content_text: Optional[str] = None
    content_file_path: Optional[str] = None
    reference_video_path: Optional[str] = None

    # Presentation inputs
    google_slides_url: Optional[str] = None
    generate_new_slides: bool = False

    # Output settings
    output_path: Optional[str] = None
    temp_dir: str = "temp"

@dataclass
class GenerationResult:
    """Result of video generation"""
    success: bool
    output_path: Optional[str] = None
    processing_time: Optional[float] = None
    mode: Optional[OperationMode] = None
    total_duration: Optional[float] = None
    avatar_duration: Optional[float] = None
    presentation_duration: Optional[float] = None
    error: Optional[str] = None

class ModeOrchestrator:
    """
    Main orchestrator for the three operation modes
    Coordinates all components to generate final videos
    """

    def __init__(self, logger: Optional[logging.Logger] = None, testing_mode: bool = False):
        self.logger = logger or logging.getLogger("presgen_training2.orchestrator")

        # Initialize all components
        self.avatar_engine = LivePortraitEngine(logger)
        self.voice_manager = VoiceProfileManager(logger=logger)
        self.content_processor = ContentProcessor(logger=logger)
        self.slides_processor = GoogleSlidesProcessor(logger, skip_auth=testing_mode)
        self.slides_renderer = SlidesToVideoRenderer(logger)
        self.video_appender = VideoAppendingEngine(logger)

    def generate_video(self, request: GenerationRequest) -> GenerationResult:
        """
        Generate video based on the operation mode

        Args:
            request: GenerationRequest with all parameters

        Returns:
            GenerationResult with video path and metadata
        """

        start_time = time.time()

        try:
            self.logger.info(f"Starting video generation: mode={request.mode.value}")
            jlog(self.logger, logging.INFO,
                event="video_generation_started",
                mode=request.mode.value,
                voice_profile=request.voice_profile_name,
                quality_level=request.quality_level)

            # Validate voice profile exists
            if not self.voice_manager.get_profile(request.voice_profile_name):
                return GenerationResult(
                    success=False,
                    error=f"Voice profile not found: {request.voice_profile_name}"
                )

            # Create temp directory
            temp_dir = Path(request.temp_dir)
            temp_dir.mkdir(parents=True, exist_ok=True)

            # Generate output path if not provided
            if not request.output_path:
                request.output_path = f"output/generated_video_{uuid.uuid4().hex[:8]}.mp4"

            # Route to appropriate mode handler
            if request.mode == OperationMode.VIDEO_ONLY:
                result = self._handle_video_only_mode(request, temp_dir)
            elif request.mode == OperationMode.PRESENTATION_ONLY:
                result = self._handle_presentation_only_mode(request, temp_dir)
            elif request.mode == OperationMode.VIDEO_PRESENTATION:
                result = self._handle_video_presentation_mode(request, temp_dir)
            else:
                return GenerationResult(
                    success=False,
                    error=f"Unsupported operation mode: {request.mode}"
                )

            processing_time = time.time() - start_time

            if result.success:
                result.processing_time = processing_time
                result.mode = request.mode

                self.logger.info(f"Video generation completed in {processing_time:.2f}s")
                jlog(self.logger, logging.INFO,
                    event="video_generation_completed",
                    processing_time=processing_time,
                    output_path=result.output_path,
                    mode=request.mode.value,
                    total_duration=result.total_duration)

            return result

        except Exception as e:
            error_msg = f"Video generation failed: {str(e)}"
            self.logger.error(error_msg)
            return GenerationResult(
                success=False,
                error=error_msg,
                processing_time=time.time() - start_time
            )

    def _handle_video_only_mode(self, request: GenerationRequest, temp_dir: Path) -> GenerationResult:
        """Handle Video-Only mode: Avatar video generation with narration"""

        try:
            # Step 1: Process content into script
            script_text = self._prepare_script(request)
            if not script_text:
                return GenerationResult(
                    success=False,
                    error="Failed to generate script from content"
                )

            # Step 2: Generate TTS audio
            audio_path = temp_dir / f"narration_{uuid.uuid4().hex[:8]}.wav"

            tts_success = self.voice_manager.generate_speech(
                text=script_text,
                voice_profile_name=request.voice_profile_name,
                output_path=str(audio_path)
            )

            if not tts_success:
                return GenerationResult(
                    success=False,
                    error="Failed to generate TTS audio"
                )

            # Step 3: Extract reference image from video (if provided)
            if request.reference_video_path:
                reference_image = temp_dir / f"reference_{uuid.uuid4().hex[:8]}.jpg"
                extract_success = self.avatar_engine.extract_reference_frame(
                    video_path=request.reference_video_path,
                    output_image_path=str(reference_image)
                )

                if not extract_success:
                    return GenerationResult(
                        success=False,
                        error="Failed to extract reference image from video"
                    )
            else:
                # Use default reference image if no video provided
                reference_image = "assets/default_avatar.jpg"  # Would need to be provided
                if not Path(reference_image).exists():
                    return GenerationResult(
                        success=False,
                        error="No reference video or default avatar image found"
                    )

            # Step 4: Generate avatar video
            avatar_result = self.avatar_engine.generate_avatar_video(
                audio_path=str(audio_path),
                reference_image=str(reference_image),
                output_dir=str(temp_dir),
                quality_level=request.quality_level
            )

            if not avatar_result.success:
                return GenerationResult(
                    success=False,
                    error=f"Avatar generation failed: {avatar_result.error}"
                )

            # Step 5: Move to final output location
            final_output = Path(request.output_path)
            final_output.parent.mkdir(parents=True, exist_ok=True)

            import shutil
            shutil.move(avatar_result.output_path, str(final_output))

            return GenerationResult(
                success=True,
                output_path=str(final_output),
                total_duration=avatar_result.processing_time,
                avatar_duration=avatar_result.processing_time
            )

        except Exception as e:
            return GenerationResult(
                success=False,
                error=f"Video-Only mode failed: {str(e)}"
            )

    def _handle_presentation_only_mode(self, request: GenerationRequest, temp_dir: Path) -> GenerationResult:
        """Handle Presentation-Only mode: Narrated slideshow generation"""

        try:
            # Step 1: Get slides data
            if request.google_slides_url:
                # Process Google Slides URL
                slides_result = self.slides_processor.process_google_slides_url(
                    url=request.google_slides_url,
                    output_dir=str(temp_dir / "slides")
                )

                if not slides_result.success:
                    return GenerationResult(
                        success=False,
                        error=f"Failed to process Google Slides: {slides_result.error}"
                    )

                slides_data = slides_result.slides

            elif request.generate_new_slides:
                # Generate new slides from content
                script_text = self._prepare_script(request)
                if not script_text:
                    return GenerationResult(
                        success=False,
                        error="Failed to generate script for slides"
                    )

                # TODO: Integrate with existing PresGen slide generation
                # For now, return error as this requires PresGen-Core integration
                return GenerationResult(
                    success=False,
                    error="New slide generation not yet implemented - use Google Slides URL"
                )
            else:
                return GenerationResult(
                    success=False,
                    error="Must provide Google Slides URL or enable new slide generation"
                )

            # Step 2: Generate TTS audio for each slide
            audio_files = []

            for i, slide in enumerate(slides_data):
                if not slide.notes_text.strip():
                    # Skip slides without notes
                    continue

                audio_path = temp_dir / f"slide_{i:03d}_audio.wav"

                tts_success = self.voice_manager.generate_speech(
                    text=slide.notes_text,
                    voice_profile_name=request.voice_profile_name,
                    output_path=str(audio_path)
                )

                if tts_success:
                    audio_files.append(str(audio_path))
                else:
                    self.logger.warning(f"Failed to generate audio for slide {i + 1}")

            if not audio_files:
                return GenerationResult(
                    success=False,
                    error="No audio generated for any slides"
                )

            # Step 3: Render slides to video
            video_result = self.slides_renderer.render_presentation_video(
                slides=[slide for slide in slides_data if slide.notes_text.strip()],
                audio_files=audio_files,
                output_path=request.output_path
            )

            if not video_result.success:
                return GenerationResult(
                    success=False,
                    error=f"Slides rendering failed: {video_result.error}"
                )

            return GenerationResult(
                success=True,
                output_path=video_result.output_path,
                total_duration=video_result.total_duration,
                presentation_duration=video_result.total_duration
            )

        except Exception as e:
            return GenerationResult(
                success=False,
                error=f"Presentation-Only mode failed: {str(e)}"
            )

    def _handle_video_presentation_mode(self, request: GenerationRequest, temp_dir: Path) -> GenerationResult:
        """Handle Video-Presentation mode: Combined avatar intro + narrated presentation"""

        try:
            # Step 1: Generate Video-Only portion
            video_request = GenerationRequest(
                mode=OperationMode.VIDEO_ONLY,
                voice_profile_name=request.voice_profile_name,
                quality_level=request.quality_level,
                content_text=request.content_text,
                content_file_path=request.content_file_path,
                reference_video_path=request.reference_video_path,
                output_path=str(temp_dir / "avatar_video.mp4"),
                temp_dir=str(temp_dir / "avatar_temp")
            )

            avatar_result = self._handle_video_only_mode(video_request, temp_dir / "avatar_temp")

            if not avatar_result.success:
                return GenerationResult(
                    success=False,
                    error=f"Avatar video generation failed: {avatar_result.error}"
                )

            # Step 2: Generate Presentation-Only portion
            presentation_request = GenerationRequest(
                mode=OperationMode.PRESENTATION_ONLY,
                voice_profile_name=request.voice_profile_name,
                quality_level=request.quality_level,
                google_slides_url=request.google_slides_url,
                generate_new_slides=request.generate_new_slides,
                output_path=str(temp_dir / "presentation_video.mp4"),
                temp_dir=str(temp_dir / "presentation_temp")
            )

            presentation_result = self._handle_presentation_only_mode(
                presentation_request, temp_dir / "presentation_temp"
            )

            if not presentation_result.success:
                return GenerationResult(
                    success=False,
                    error=f"Presentation video generation failed: {presentation_result.error}"
                )

            # Step 3: Append videos together
            video_segments = [
                VideoSegment(
                    path=avatar_result.output_path,
                    title="Avatar Introduction"
                ),
                VideoSegment(
                    path=presentation_result.output_path,
                    title="Presentation"
                )
            ]

            append_result = self.video_appender.append_videos(
                video_segments=video_segments,
                output_path=request.output_path,
                normalize_format=True
            )

            if not append_result.success:
                return GenerationResult(
                    success=False,
                    error=f"Video appending failed: {append_result.error}"
                )

            return GenerationResult(
                success=True,
                output_path=append_result.output_path,
                total_duration=append_result.total_duration,
                avatar_duration=avatar_result.total_duration,
                presentation_duration=presentation_result.total_duration
            )

        except Exception as e:
            return GenerationResult(
                success=False,
                error=f"Video-Presentation mode failed: {str(e)}"
            )

    def _prepare_script(self, request: GenerationRequest) -> Optional[str]:
        """Prepare script text from various content sources"""

        try:
            if request.content_text:
                # Use provided text directly
                return request.content_text

            elif request.content_file_path:
                # Process content file
                script_result = self.content_processor.process_content_file(
                    file_path=request.content_file_path,
                    custom_instructions="Create an engaging presentation script suitable for video narration."
                )

                if script_result.success:
                    return script_result.script
                else:
                    self.logger.error(f"Content processing failed: {script_result.error}")
                    return None

            else:
                self.logger.error("No content source provided")
                return None

        except Exception as e:
            self.logger.error(f"Script preparation failed: {e}")
            return None

    def list_voice_profiles(self) -> List[Dict[str, Any]]:
        """List available voice profiles"""
        return self.voice_manager.list_profiles()

    def clone_voice_from_video(self, video_path: str, profile_name: str) -> bool:
        """Clone voice from video and save as profile"""

        try:
            profile = self.voice_manager.clone_voice_from_video(
                video_path=video_path,
                profile_name=profile_name
            )

            return profile is not None

        except Exception as e:
            self.logger.error(f"Voice cloning failed: {e}")
            return False

    def validate_google_slides_url(self, url: str) -> bool:
        """Validate Google Slides URL access"""
        return self.slides_processor.validate_slides_access(url)