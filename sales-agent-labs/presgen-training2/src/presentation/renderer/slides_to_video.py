import subprocess
import json
import time
import logging
import uuid
import os
from pathlib import Path
from typing import List, Optional, Dict, Any
from dataclasses import dataclass

# Use simple logging for now - can integrate with parent project later
def jlog(logger, level, event, **kwargs):
    """Simple logging wrapper"""
    logger.log(level, f"Event: {event}, Data: {kwargs}")
from presentation.slides.google_slides_processor import SlideData

@dataclass
class VideoRenderResult:
    """Result of slides-to-video rendering"""
    success: bool
    output_path: Optional[str] = None
    processing_time: Optional[float] = None
    total_duration: Optional[float] = None
    slides_count: Optional[int] = None
    error: Optional[str] = None

@dataclass
class TransitionConfig:
    """Video transition configuration"""
    type: str = "fade"  # fade, dissolve, slide, none
    duration: float = 0.5  # seconds

class SlidesToVideoRenderer:
    """
    Converts presentation slides with audio narration into MP4 video
    Handles slide timing, transitions, and audio synchronization
    """

    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger("presgen_training2.slides_renderer")

        # Video configuration
        self.video_config = {
            "resolution": "1280x720",  # 720p standard
            "fps": 30,
            "video_codec": "libx264",
            "audio_codec": "aac",
            "audio_bitrate": "192k",
            "crf": 23,  # Quality factor (lower = better quality)
        }

        # Transition configurations
        self.transitions = {
            "fade": "fade=t=in:st={start}:d={duration},fade=t=out:st={end}:d={duration}",
            "dissolve": "blend=all_mode=average:all_opacity=0.5",
            "slide": "slide=direction=right:duration={duration}",
            "none": ""
        }

    def render_presentation_video(self,
                                slides: List[SlideData],
                                audio_files: List[str],
                                output_path: str,
                                transition_config: TransitionConfig = None) -> VideoRenderResult:
        """
        Render presentation slides with narration audio into video

        Args:
            slides: List of SlideData with image paths and timing
            audio_files: List of audio file paths (one per slide)
            output_path: Output video file path
            transition_config: Transition configuration

        Returns:
            VideoRenderResult with video path and metadata
        """

        start_time = time.time()

        try:
            if not slides:
                return VideoRenderResult(
                    success=False,
                    error="No slides provided for rendering"
                )

            if len(audio_files) != len(slides):
                return VideoRenderResult(
                    success=False,
                    error=f"Mismatch: {len(slides)} slides but {len(audio_files)} audio files"
                )

            # Validate all input files exist
            for i, slide in enumerate(slides):
                if not slide.local_image_path or not Path(slide.local_image_path).exists():
                    return VideoRenderResult(
                        success=False,
                        error=f"Slide image not found: {slide.local_image_path}"
                    )

                if not Path(audio_files[i]).exists():
                    return VideoRenderResult(
                        success=False,
                        error=f"Audio file not found: {audio_files[i]}"
                    )

            transition_config = transition_config or TransitionConfig()

            self.logger.info(f"Starting slides-to-video rendering: {len(slides)} slides")
            jlog(self.logger, logging.INFO,
                event="slides_video_rendering_started",
                slides_count=len(slides),
                output_path=output_path,
                transition_type=transition_config.type)

            # Create temporary directory for processing
            temp_dir = Path("temp") / f"video_render_{uuid.uuid4().hex[:8]}"
            temp_dir.mkdir(parents=True, exist_ok=True)

            # Method 1: Simple concatenation (fast and reliable)
            if transition_config.type == "none":
                result = self._render_simple_concatenation(
                    slides, audio_files, output_path, temp_dir
                )
            else:
                # Method 2: Complex transitions (slower but smoother)
                result = self._render_with_transitions(
                    slides, audio_files, output_path, temp_dir, transition_config
                )

            processing_time = time.time() - start_time

            if result.success:
                self.logger.info(f"Slides-to-video rendering completed in {processing_time:.2f}s")
                jlog(self.logger, logging.INFO,
                    event="slides_video_rendering_completed",
                    processing_time=processing_time,
                    output_path=result.output_path,
                    total_duration=result.total_duration)

                result.processing_time = processing_time

            # Cleanup temporary files
            self._cleanup_temp_directory(temp_dir)

            return result

        except Exception as e:
            error_msg = f"Slides-to-video rendering failed: {str(e)}"
            self.logger.error(error_msg)
            return VideoRenderResult(
                success=False,
                error=error_msg,
                processing_time=time.time() - start_time
            )

    def _render_simple_concatenation(self,
                                   slides: List[SlideData],
                                   audio_files: List[str],
                                   output_path: str,
                                   temp_dir: Path) -> VideoRenderResult:
        """Render video using simple concatenation (fastest method)"""

        try:
            # Create individual slide videos
            slide_videos = []
            total_duration = 0.0

            for i, (slide, audio_file) in enumerate(zip(slides, audio_files)):
                slide_video_path = temp_dir / f"slide_{i:03d}.mp4"

                duration = self._create_slide_video(
                    image_path=slide.local_image_path,
                    audio_path=audio_file,
                    output_path=str(slide_video_path),
                    duration=slide.estimated_duration
                )

                if duration is None:
                    return VideoRenderResult(
                        success=False,
                        error=f"Failed to create video for slide {i + 1}"
                    )

                slide_videos.append(str(slide_video_path))
                total_duration += duration

            # Concatenate all slide videos
            success = self._concatenate_videos(slide_videos, output_path)

            if not success:
                return VideoRenderResult(
                    success=False,
                    error="Failed to concatenate slide videos"
                )

            return VideoRenderResult(
                success=True,
                output_path=output_path,
                total_duration=total_duration,
                slides_count=len(slides)
            )

        except Exception as e:
            return VideoRenderResult(
                success=False,
                error=f"Simple concatenation failed: {str(e)}"
            )

    def _render_with_transitions(self,
                               slides: List[SlideData],
                               audio_files: List[str],
                               output_path: str,
                               temp_dir: Path,
                               transition_config: TransitionConfig) -> VideoRenderResult:
        """Render video with transitions between slides"""

        try:
            # For transitions, we'll create a complex FFmpeg filter
            # This is more advanced but provides smoother transitions

            # Build FFmpeg command with complex filter graph
            cmd = self._build_transition_ffmpeg_command(
                slides, audio_files, output_path, transition_config
            )

            self.logger.debug(f"FFmpeg transition command: {' '.join(cmd)}")

            # Execute FFmpeg
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300  # 5 minutes timeout
            )

            if result.returncode != 0:
                self.logger.error(f"FFmpeg transition rendering failed: {result.stderr}")
                return VideoRenderResult(
                    success=False,
                    error=f"FFmpeg error: {result.stderr}"
                )

            total_duration = sum(slide.estimated_duration for slide in slides)

            return VideoRenderResult(
                success=True,
                output_path=output_path,
                total_duration=total_duration,
                slides_count=len(slides)
            )

        except subprocess.TimeoutExpired:
            return VideoRenderResult(
                success=False,
                error="Transition rendering timed out after 5 minutes"
            )
        except Exception as e:
            return VideoRenderResult(
                success=False,
                error=f"Transition rendering failed: {str(e)}"
            )

    def _create_slide_video(self,
                          image_path: str,
                          audio_path: str,
                          output_path: str,
                          duration: float) -> Optional[float]:
        """Create individual slide video from image and audio using audio duration as primary timing"""

        try:
            # Get actual audio duration to ensure precise timing
            actual_audio_duration = self._get_actual_audio_duration(audio_path)
            if actual_audio_duration:
                duration = actual_audio_duration
                self.logger.debug(f"Using actual audio duration: {duration:.2f}s for {audio_path}")

            cmd = [
                "ffmpeg",
                "-loop", "1",
                "-i", image_path,
                "-i", audio_path,
                "-c:v", self.video_config["video_codec"],
                "-c:a", self.video_config["audio_codec"],
                "-b:a", self.video_config["audio_bitrate"],
                "-crf", str(self.video_config["crf"]),
                "-r", str(self.video_config["fps"]),
                "-s", self.video_config["resolution"],
                "-t", str(duration),  # Use explicit duration instead of -shortest
                "-avoid_negative_ts", "make_zero",
                "-y", output_path
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)

            if result.returncode != 0:
                self.logger.error(f"Failed to create slide video: {result.stderr}")
                return None

            # Get actual duration from output
            duration_cmd = [
                "ffprobe",
                "-v", "quiet",
                "-show_entries", "format=duration",
                "-of", "csv=p=0",
                output_path
            ]

            duration_result = subprocess.run(duration_cmd, capture_output=True, text=True)

            if duration_result.returncode == 0:
                try:
                    actual_duration = float(duration_result.stdout.strip())
                    return actual_duration
                except ValueError:
                    pass

            return duration  # Fallback to estimated duration

        except subprocess.TimeoutExpired:
            self.logger.error("Slide video creation timed out")
            return None
        except Exception as e:
            self.logger.error(f"Error creating slide video: {e}")
            return None

    def _concatenate_videos(self, video_files: List[str], output_path: str) -> bool:
        """Concatenate multiple video files into single output"""

        try:
            # Create concatenation file list
            concat_file = Path("temp") / f"concat_{uuid.uuid4().hex[:8]}.txt"

            with open(concat_file, 'w') as f:
                for video_file in video_files:
                    f.write(f"file '{Path(video_file).absolute()}'\n")

            cmd = [
                "ffmpeg",
                "-f", "concat",
                "-safe", "0",
                "-i", str(concat_file),
                "-c", "copy",
                "-y", output_path
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)

            # Cleanup concat file
            if concat_file.exists():
                concat_file.unlink()

            if result.returncode != 0:
                self.logger.error(f"Video concatenation failed: {result.stderr}")
                return False

            return True

        except Exception as e:
            self.logger.error(f"Error concatenating videos: {e}")
            return False

    def _build_transition_ffmpeg_command(self,
                                       slides: List[SlideData],
                                       audio_files: List[str],
                                       output_path: str,
                                       transition_config: TransitionConfig) -> List[str]:
        """Build complex FFmpeg command for transitions"""

        # This is a simplified version - real implementation would be much more complex
        # For now, we'll fall back to simple concatenation with fade effects

        cmd = ["ffmpeg"]

        # Add all input files with actual audio durations
        for i, (slide, audio_file) in enumerate(zip(slides, audio_files)):
            # Use actual audio duration for precise timing
            actual_duration = self._get_actual_audio_duration(audio_file)
            duration = actual_duration if actual_duration else slide.estimated_duration

            cmd.extend(["-loop", "1", "-t", str(duration), "-i", slide.local_image_path])
            cmd.extend(["-i", audio_file])

        # For simplicity, create basic concatenation with fade
        filter_complex = ""
        audio_filter = ""

        for i in range(len(slides)):
            if i == 0:
                filter_complex += f"[{i*2}:v]scale={self.video_config['resolution']},setsar=1,fps={self.video_config['fps']}[v{i}];"
            else:
                filter_complex += f"[{i*2}:v]scale={self.video_config['resolution']},setsar=1,fps={self.video_config['fps']},fade=t=in:st=0:d={transition_config.duration}[v{i}];"

            audio_filter += f"[{i*2+1}:a]"

        # Concatenate videos
        video_concat = "".join([f"[v{i}]" for i in range(len(slides))])
        filter_complex += f"{video_concat}concat=n={len(slides)}:v=1:a=0[outv];"

        # Concatenate audio
        filter_complex += f"{audio_filter}concat=n={len(slides)}:v=0:a=1[outa]"

        cmd.extend([
            "-filter_complex", filter_complex,
            "-map", "[outv]",
            "-map", "[outa]",
            "-c:v", self.video_config["video_codec"],
            "-c:a", self.video_config["audio_codec"],
            "-b:a", self.video_config["audio_bitrate"],
            "-crf", str(self.video_config["crf"]),
            "-y", output_path
        ])

        return cmd

    def _cleanup_temp_directory(self, temp_dir: Path):
        """Clean up temporary files"""
        try:
            if temp_dir.exists():
                import shutil
                shutil.rmtree(temp_dir)
        except Exception as e:
            self.logger.warning(f"Could not cleanup temp directory: {e}")

    def get_video_info(self, video_path: str) -> Optional[Dict[str, Any]]:
        """Get video information using ffprobe"""

        try:
            cmd = [
                "ffprobe",
                "-v", "quiet",
                "-print_format", "json",
                "-show_format",
                "-show_streams",
                video_path
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

            if result.returncode != 0:
                return None

            return json.loads(result.stdout)

        except Exception as e:
            self.logger.error(f"Error getting video info: {e}")
            return None

    def _get_actual_audio_duration(self, audio_path: str) -> Optional[float]:
        """Get precise audio duration using ffprobe"""
        try:
            cmd = [
                "ffprobe",
                "-v", "quiet",
                "-show_entries", "format=duration",
                "-of", "csv=p=0",
                audio_path
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

            if result.returncode == 0:
                duration_str = result.stdout.strip()
                if duration_str:
                    return float(duration_str)

            self.logger.warning(f"Could not get audio duration for {audio_path}")
            return None

        except Exception as e:
            self.logger.error(f"Error getting audio duration: {e}")
            return None