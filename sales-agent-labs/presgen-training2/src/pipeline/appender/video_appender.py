import subprocess
import json
import time
import logging
import uuid
import os
from pathlib import Path
from typing import List, Optional, Dict, Any, Tuple
from dataclasses import dataclass

# Use simple logging for now - can integrate with parent project later
def jlog(logger, level, event, **kwargs):
    """Simple logging wrapper"""
    logger.log(level, f"Event: {event}, Data: {kwargs}")

@dataclass
class VideoSegment:
    """Video segment for appending"""
    path: str
    title: str
    duration: Optional[float] = None
    resolution: Optional[Tuple[int, int]] = None
    fps: Optional[float] = None

@dataclass
class VideoAppendResult:
    """Result of video appending operation"""
    success: bool
    output_path: Optional[str] = None
    processing_time: Optional[float] = None
    total_duration: Optional[float] = None
    segments_count: Optional[int] = None
    error: Optional[str] = None

@dataclass
class TransitionSettings:
    """Transition settings between video segments"""
    type: str = "fade"  # fade, crossfade, cut, dissolve
    duration: float = 1.0  # seconds
    enabled: bool = True

class VideoAppendingEngine:
    """
    Advanced video appending system for seamless concatenation
    Handles format normalization, transitions, and quality optimization
    """

    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger("presgen_training2.video_appender")

        # Standard output configuration
        self.output_config = {
            "resolution": "1280x720",  # 720p standard
            "fps": 30,
            "video_codec": "libx264",
            "audio_codec": "aac",
            "audio_bitrate": "192k",
            "crf": 23,  # Quality factor
            "preset": "medium",  # Encoding speed vs compression
        }

    def append_videos(self,
                     video_segments: List[VideoSegment],
                     output_path: str,
                     transition_settings: TransitionSettings = None,
                     normalize_format: bool = True) -> VideoAppendResult:
        """
        Append multiple video segments into single output video

        Args:
            video_segments: List of video segments to append
            output_path: Output video file path
            transition_settings: Transition configuration between segments
            normalize_format: Whether to normalize video formats

        Returns:
            VideoAppendResult with video path and metadata
        """

        start_time = time.time()

        try:
            if not video_segments:
                return VideoAppendResult(
                    success=False,
                    error="No video segments provided for appending"
                )

            # Validate all input videos exist
            for i, segment in enumerate(video_segments):
                if not Path(segment.path).exists():
                    return VideoAppendResult(
                        success=False,
                        error=f"Video segment {i + 1} not found: {segment.path}"
                    )

            transition_settings = transition_settings or TransitionSettings()

            self.logger.info(f"Starting video appending: {len(video_segments)} segments")
            jlog(self.logger, logging.INFO,
                event="video_appending_started",
                segments_count=len(video_segments),
                output_path=output_path,
                transition_type=transition_settings.type if transition_settings.enabled else "none")

            # Analyze input videos
            analyzed_segments = self._analyze_video_segments(video_segments)

            if not analyzed_segments:
                return VideoAppendResult(
                    success=False,
                    error="Failed to analyze input video segments"
                )

            # Create temporary directory for processing
            temp_dir = Path("temp") / f"video_append_{uuid.uuid4().hex[:8]}"
            temp_dir.mkdir(parents=True, exist_ok=True)

            # Normalize formats if requested
            if normalize_format:
                normalized_segments = self._normalize_video_formats(
                    analyzed_segments, temp_dir
                )
                if not normalized_segments:
                    return VideoAppendResult(
                        success=False,
                        error="Failed to normalize video formats"
                    )
            else:
                normalized_segments = analyzed_segments

            # Append videos based on transition settings
            if transition_settings.enabled and transition_settings.type != "cut":
                result = self._append_with_transitions(
                    normalized_segments, output_path, transition_settings, temp_dir
                )
            else:
                result = self._append_simple_concatenation(
                    normalized_segments, output_path, temp_dir
                )

            processing_time = time.time() - start_time

            if result.success:
                self.logger.info(f"Video appending completed in {processing_time:.2f}s")
                jlog(self.logger, logging.INFO,
                    event="video_appending_completed",
                    processing_time=processing_time,
                    output_path=result.output_path,
                    total_duration=result.total_duration)

                result.processing_time = processing_time

            # Cleanup temporary files
            self._cleanup_temp_directory(temp_dir)

            return result

        except Exception as e:
            error_msg = f"Video appending failed: {str(e)}"
            self.logger.error(error_msg)
            return VideoAppendResult(
                success=False,
                error=error_msg,
                processing_time=time.time() - start_time
            )

    def _analyze_video_segments(self, segments: List[VideoSegment]) -> List[VideoSegment]:
        """Analyze video segments and extract metadata"""

        analyzed_segments = []

        for segment in segments:
            try:
                info = self._get_video_info(segment.path)
                if not info:
                    self.logger.warning(f"Could not analyze video: {segment.path}")
                    continue

                # Extract video stream info
                video_stream = None
                audio_stream = None

                for stream in info.get('streams', []):
                    if stream.get('codec_type') == 'video' and not video_stream:
                        video_stream = stream
                    elif stream.get('codec_type') == 'audio' and not audio_stream:
                        audio_stream = stream

                if not video_stream:
                    self.logger.warning(f"No video stream found in: {segment.path}")
                    continue

                # Update segment with analyzed data
                updated_segment = VideoSegment(
                    path=segment.path,
                    title=segment.title,
                    duration=float(info.get('format', {}).get('duration', 0)),
                    resolution=(
                        int(video_stream.get('width', 0)),
                        int(video_stream.get('height', 0))
                    ),
                    fps=self._parse_fps(video_stream.get('r_frame_rate', '30/1'))
                )

                analyzed_segments.append(updated_segment)

                self.logger.debug(f"Analyzed video: {segment.path} - "
                                f"{updated_segment.resolution[0]}x{updated_segment.resolution[1]} "
                                f"@ {updated_segment.fps}fps, {updated_segment.duration:.2f}s")

            except Exception as e:
                self.logger.error(f"Error analyzing video {segment.path}: {e}")
                continue

        return analyzed_segments

    def _normalize_video_formats(self,
                               segments: List[VideoSegment],
                               temp_dir: Path) -> List[VideoSegment]:
        """Normalize video formats for consistent concatenation"""

        normalized_segments = []

        for i, segment in enumerate(segments):
            try:
                # Check if normalization is needed
                needs_normalization = (
                    segment.resolution != (1280, 720) or
                    abs(segment.fps - 30.0) > 0.1
                )

                if not needs_normalization:
                    # No normalization needed, use original
                    normalized_segments.append(segment)
                    continue

                # Create normalized version
                normalized_path = temp_dir / f"normalized_{i:03d}.mp4"

                success = self._normalize_single_video(
                    segment.path, str(normalized_path)
                )

                if not success:
                    self.logger.error(f"Failed to normalize video: {segment.path}")
                    return []

                # Create updated segment
                normalized_segment = VideoSegment(
                    path=str(normalized_path),
                    title=segment.title,
                    duration=segment.duration,
                    resolution=(1280, 720),
                    fps=30.0
                )

                normalized_segments.append(normalized_segment)

                self.logger.debug(f"Normalized video: {segment.path} -> {normalized_path}")

            except Exception as e:
                self.logger.error(f"Error normalizing video {segment.path}: {e}")
                return []

        return normalized_segments

    def _normalize_single_video(self, input_path: str, output_path: str) -> bool:
        """Normalize single video to standard format"""

        try:
            cmd = [
                "ffmpeg",
                "-i", input_path,
                "-c:v", self.output_config["video_codec"],
                "-c:a", self.output_config["audio_codec"],
                "-b:a", self.output_config["audio_bitrate"],
                "-crf", str(self.output_config["crf"]),
                "-preset", self.output_config["preset"],
                "-r", str(self.output_config["fps"]),
                "-s", self.output_config["resolution"],
                "-aspect", "16:9",
                "-movflags", "+faststart",
                "-y", output_path
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

            if result.returncode != 0:
                self.logger.error(f"Video normalization failed: {result.stderr}")
                return False

            return True

        except subprocess.TimeoutExpired:
            self.logger.error("Video normalization timed out")
            return False
        except Exception as e:
            self.logger.error(f"Error normalizing video: {e}")
            return False

    def _append_simple_concatenation(self,
                                   segments: List[VideoSegment],
                                   output_path: str,
                                   temp_dir: Path) -> VideoAppendResult:
        """Simple video concatenation without transitions"""

        try:
            # Create concatenation file list
            concat_file = temp_dir / "concat_list.txt"

            with open(concat_file, 'w') as f:
                for segment in segments:
                    f.write(f"file '{Path(segment.path).absolute()}'\n")

            cmd = [
                "ffmpeg",
                "-f", "concat",
                "-safe", "0",
                "-i", str(concat_file),
                "-c", "copy",
                "-movflags", "+faststart",
                "-y", output_path
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)

            if result.returncode != 0:
                self.logger.error(f"Video concatenation failed: {result.stderr}")
                return VideoAppendResult(
                    success=False,
                    error=f"FFmpeg concatenation error: {result.stderr}"
                )

            total_duration = sum(segment.duration or 0 for segment in segments)

            return VideoAppendResult(
                success=True,
                output_path=output_path,
                total_duration=total_duration,
                segments_count=len(segments)
            )

        except subprocess.TimeoutExpired:
            return VideoAppendResult(
                success=False,
                error="Video concatenation timed out after 10 minutes"
            )
        except Exception as e:
            return VideoAppendResult(
                success=False,
                error=f"Simple concatenation failed: {str(e)}"
            )

    def _append_with_transitions(self,
                               segments: List[VideoSegment],
                               output_path: str,
                               transition_settings: TransitionSettings,
                               temp_dir: Path) -> VideoAppendResult:
        """Append videos with transitions between segments"""

        try:
            # Build complex filter graph for transitions
            filter_complex = self._build_transition_filter(segments, transition_settings)

            cmd = ["ffmpeg"]

            # Add all input files
            for segment in segments:
                cmd.extend(["-i", segment.path])

            # Add filter complex
            cmd.extend([
                "-filter_complex", filter_complex,
                "-map", "[outv]",
                "-map", "[outa]",
                "-c:v", self.output_config["video_codec"],
                "-c:a", self.output_config["audio_codec"],
                "-b:a", self.output_config["audio_bitrate"],
                "-crf", str(self.output_config["crf"]),
                "-preset", self.output_config["preset"],
                "-movflags", "+faststart",
                "-y", output_path
            ])

            self.logger.debug(f"FFmpeg transition command: {' '.join(cmd)}")

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=900)

            if result.returncode != 0:
                self.logger.error(f"Transition appending failed: {result.stderr}")
                return VideoAppendResult(
                    success=False,
                    error=f"FFmpeg transition error: {result.stderr}"
                )

            total_duration = sum(segment.duration or 0 for segment in segments)

            return VideoAppendResult(
                success=True,
                output_path=output_path,
                total_duration=total_duration,
                segments_count=len(segments)
            )

        except subprocess.TimeoutExpired:
            return VideoAppendResult(
                success=False,
                error="Transition appending timed out after 15 minutes"
            )
        except Exception as e:
            return VideoAppendResult(
                success=False,
                error=f"Transition appending failed: {str(e)}"
            )

    def _build_transition_filter(self,
                               segments: List[VideoSegment],
                               transition_settings: TransitionSettings) -> str:
        """Build FFmpeg filter graph for transitions"""

        filter_parts = []
        audio_parts = []

        # Process each video input
        for i in range(len(segments)):
            # Scale and prepare video
            filter_parts.append(f"[{i}:v]scale={self.output_config['resolution']},"
                              f"setsar=1,fps={self.output_config['fps']}[v{i}]")
            audio_parts.append(f"[{i}:a]")

        # Build transition chain
        if transition_settings.type == "fade":
            # Fade transitions
            current_video = "[v0]"

            for i in range(1, len(segments)):
                if i == 1:
                    filter_parts.append(f"{current_video}[v{i}]blend=all_mode=addition:all_opacity=0.5:"
                                      f"enable='between(t,{segments[i-1].duration-transition_settings.duration},"
                                      f"{segments[i-1].duration})'[blend{i}]")
                    current_video = f"[blend{i}]"
                else:
                    filter_parts.append(f"{current_video}[v{i}]blend=all_mode=addition:all_opacity=0.5:"
                                      f"enable='between(t,{sum(seg.duration for seg in segments[:i])-transition_settings.duration},"
                                      f"{sum(seg.duration for seg in segments[:i])})'[blend{i}]")
                    current_video = f"[blend{i}]"

            # Final output
            filter_parts.append(f"{current_video}null[outv]")

        else:
            # Simple concatenation for other transition types
            video_inputs = "".join([f"[v{i}]" for i in range(len(segments))])
            filter_parts.append(f"{video_inputs}concat=n={len(segments)}:v=1:a=0[outv]")

        # Audio concatenation
        audio_inputs = "".join(audio_parts)
        filter_parts.append(f"{audio_inputs}concat=n={len(segments)}:v=0:a=1[outa]")

        return ";".join(filter_parts)

    def _get_video_info(self, video_path: str) -> Optional[Dict[str, Any]]:
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

    def _parse_fps(self, fps_string: str) -> float:
        """Parse FPS string (e.g., '30/1') to float"""
        try:
            if '/' in fps_string:
                num, den = fps_string.split('/')
                return float(num) / float(den)
            else:
                return float(fps_string)
        except:
            return 30.0  # Default fallback

    def _cleanup_temp_directory(self, temp_dir: Path):
        """Clean up temporary files"""
        try:
            if temp_dir.exists():
                import shutil
                shutil.rmtree(temp_dir)
        except Exception as e:
            self.logger.warning(f"Could not cleanup temp directory: {e}")

    def validate_video_file(self, video_path: str) -> bool:
        """Validate that video file exists and is readable"""
        try:
            if not Path(video_path).exists():
                return False

            info = self._get_video_info(video_path)
            return info is not None and 'streams' in info

        except Exception:
            return False