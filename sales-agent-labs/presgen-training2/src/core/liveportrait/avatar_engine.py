import subprocess
import json
import time
import logging
import uuid
import os
import threading
import signal
from pathlib import Path
from typing import Optional, Dict, Any
from dataclasses import dataclass

import logging
# Use simple logging for now - can integrate with parent project later
def jlog(logger, level, event, **kwargs):
    """Simple logging wrapper"""
    logger.log(level, f"Event: {event}, Data: {kwargs}")

def is_verbose_logging_enabled() -> bool:
    """Check if verbose logging is enabled via environment variable"""
    return os.getenv("ENABLE_VERBOSE_LOGGING", "false").lower() == "true"

def verbose_log(logger, message: str, **kwargs):
    """Log message only if verbose logging is enabled"""
    if is_verbose_logging_enabled():
        logger.info(f"[VERBOSE] {message}")
        if kwargs:
            logger.info(f"[VERBOSE] Details: {kwargs}")

def estimate_processing_time(audio_duration: float, quality_level: str) -> Dict[str, float]:
    """Estimate video processing time based on audio duration and quality"""
    # Base processing rates (seconds of processing per second of audio)
    base_rates = {
        "fast": 5.0,     # 5 seconds processing per 1 second audio
        "standard": 12.0, # 12 seconds processing per 1 second audio
        "high": 25.0     # 25 seconds processing per 1 second audio
    }

    rate = base_rates.get(quality_level, base_rates["standard"])

    # Add overhead for model loading, I/O, etc.
    overhead = 120  # 2 minutes base overhead

    estimated_total = (audio_duration * rate) + overhead

    return {
        "audio_duration": audio_duration,
        "processing_rate": rate,
        "overhead_seconds": overhead,
        "estimated_total_seconds": estimated_total,
        "estimated_total_minutes": estimated_total / 60
    }

def get_audio_duration(audio_path: str) -> Optional[float]:
    """Get audio duration in seconds using ffprobe"""
    try:
        cmd = [
            "ffprobe", "-v", "quiet", "-show_entries",
            "format=duration", "-of", "csv=p=0", audio_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            return float(result.stdout.strip())
        return None
    except Exception:
        return None

class ProgressReporter:
    """Reports progress during long-running operations"""

    def __init__(self, logger, operation_name: str, estimated_duration: float):
        self.logger = logger
        self.operation_name = operation_name
        self.estimated_duration = estimated_duration
        self.start_time = time.time()
        self.stop_event = threading.Event()
        self.thread = None

        # Log start of operation with clear visibility
        self.logger.info(f"🚀 Starting {self.operation_name} (estimated: {estimated_duration/60:.1f} minutes)")
        print(f"🚀 Starting {self.operation_name} (estimated: {estimated_duration/60:.1f} minutes)", flush=True)

    def start(self):
        """Start progress reporting in background thread"""
        self.thread = threading.Thread(target=self._progress_loop, daemon=True)
        self.thread.start()

    def stop(self):
        """Stop progress reporting"""
        if self.thread:
            self.stop_event.set()
            self.thread.join(timeout=1)

    def _progress_loop(self):
        """Background loop that reports progress"""
        intervals = [30, 60, 120, 300, 600]  # Progress reports at 30s, 1m, 2m, 5m, 10m
        next_interval_idx = 0

        while not self.stop_event.wait(10):  # Check every 10 seconds
            elapsed = time.time() - self.start_time

            # Report at specific intervals
            if next_interval_idx < len(intervals) and elapsed >= intervals[next_interval_idx]:
                progress_pct = min(100, (elapsed / self.estimated_duration) * 100) if self.estimated_duration > 0 else 0
                remaining = max(0, self.estimated_duration - elapsed) if self.estimated_duration > 0 else 0

                progress_msg = f"⏳ {self.operation_name} Progress: {elapsed:.0f}s elapsed ({progress_pct:.1f}% estimated), ~{remaining:.0f}s remaining"
                self.logger.info(progress_msg)
                print(progress_msg, flush=True)  # Also print to console for visibility

                verbose_log(self.logger, f"{self.operation_name} progress update",
                           elapsed_seconds=elapsed,
                           estimated_progress_pct=progress_pct,
                           estimated_remaining_seconds=remaining)

                next_interval_idx += 1

            # Also report every 5 minutes after the initial intervals
            elif elapsed > 600 and int(elapsed) % 300 == 0:  # Every 5 minutes after 10 minutes
                self.logger.info(f"⏳ {self.operation_name} still running: {elapsed/60:.1f} minutes elapsed...")

def run_subprocess_with_progress(cmd, logger, operation_name: str, estimated_duration: float = 0, **kwargs):
    """Run subprocess with progress reporting"""

    # Start progress reporting
    progress = ProgressReporter(logger, operation_name, estimated_duration)
    progress.start()

    try:
        # Run the subprocess
        result = subprocess.run(cmd, **kwargs)
        return result
    finally:
        # Stop progress reporting
        progress.stop()

@dataclass
class AvatarGenerationResult:
    success: bool
    output_path: Optional[str] = None
    processing_time: Optional[float] = None
    quality_level: Optional[str] = None
    error: Optional[str] = None

class LivePortraitEngine:
    """
    LivePortrait integration engine optimized for M1 Mac
    Handles avatar video generation with hardware-adaptive settings
    """

    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger("presgen_training2.liveportrait")
        # Check multiple possible LivePortrait locations
        possible_paths = [
            Path("LivePortrait"),
            Path("../LivePortrait"),
            Path("../../LivePortrait"),
            Path("/Users/yitzchak/Documents/learn/presentation_project/sales-agent-labs/LivePortrait")
        ]

        self.liveportrait_path = None
        for path in possible_paths:
            if path.exists():
                self.liveportrait_path = path
                break

        if not self.liveportrait_path:
            # For testing, create a dummy path
            self.liveportrait_path = Path("LivePortrait")
            self.logger.warning(f"LivePortrait not found in expected locations. Using dummy path for testing.")
        self.python_path = "python3"  # Use system Python with venv

        # Verify LivePortrait installation
        if not self.liveportrait_path.exists():
            self.logger.warning(f"LivePortrait not found at {self.liveportrait_path}. Some features may not work.")

        # Hardware-adaptive configuration
        self.hardware_config = self._detect_hardware_config()

        # Quality level configurations
        self.quality_configs = {
            "fast": {
                "flag_use_half_precision": True,
                "source_max_dim": 512,
                "driving_max_dim": 512,
                "device_options": "--flag-force-cpu",
                "timeout": 600,  # 10 minutes - reasonable for avatar generation
                "fps": 25,
                "enable_face_cropping": True,
                "smooth_animation": True
            },
            "standard": {
                "flag_use_half_precision": True,
                "source_max_dim": 512,  # Optimized for avatar consistency
                "driving_max_dim": 512,
                "device_options": "",
                "timeout": 900,  # 15 minutes - balanced timeout
                "fps": 25,
                "enable_face_cropping": True,
                "smooth_animation": True
            },
            "high": {
                "flag_use_half_precision": False,
                "source_max_dim": 768,  # Higher quality for avatars
                "driving_max_dim": 768,
                "device_options": "",
                "timeout": 1200,  # 20 minutes - maximum for high quality
                "fps": 30,
                "enable_face_cropping": True,
                "smooth_animation": True
            }
        }

    def _detect_hardware_config(self) -> Dict[str, Any]:
        """Detect M1 Mac configuration and optimize settings"""

        config = {
            "is_m1_mac": False,
            "memory_gb": 8,  # Default assumption
            "recommended_quality": "standard"
        }

        try:
            # Check if running on Apple Silicon
            result = subprocess.run(['uname', '-m'], capture_output=True, text=True)
            if result.returncode == 0 and 'arm64' in result.stdout:
                config["is_m1_mac"] = True

                # Try to detect memory (approximate)
                try:
                    memory_result = subprocess.run(['sysctl', 'hw.memsize'], capture_output=True, text=True)
                    if memory_result.returncode == 0:
                        memory_bytes = int(memory_result.stdout.split(':')[1].strip())
                        config["memory_gb"] = memory_bytes // (1024**3)

                        if config["memory_gb"] >= 16:
                            config["recommended_quality"] = "high"
                        elif config["memory_gb"] >= 8:
                            config["recommended_quality"] = "standard"
                        else:
                            config["recommended_quality"] = "fast"
                except Exception:
                    pass

        except Exception as e:
            self.logger.warning(f"Could not detect hardware configuration: {e}")

        self.logger.info(f"Hardware config detected: {config}")
        return config

    def generate_avatar_video(self,
                            audio_path: str,
                            reference_image: str,
                            output_dir: str = "output",
                            quality_level: str = "standard") -> AvatarGenerationResult:
        """
        Generate avatar video using LivePortrait

        Args:
            audio_path: Path to driving audio file
            reference_image: Path to source image for avatar
            output_dir: Directory to save output video
            quality_level: "fast", "standard", or "high"

        Returns:
            AvatarGenerationResult with video path and metadata
        """

        start_time = time.time()

        try:
            verbose_log(self.logger, "Starting avatar video generation",
                       audio_path=audio_path, reference_image=reference_image,
                       quality_level=quality_level, output_dir=output_dir)

            # Step 1: Validate inputs
            verbose_log(self.logger, "Validating input files")
            if not Path(audio_path).exists():
                return AvatarGenerationResult(
                    success=False,
                    error=f"Audio file not found: {audio_path}"
                )

            if not Path(reference_image).exists():
                return AvatarGenerationResult(
                    success=False,
                    error=f"Reference image not found: {reference_image}"
                )

            # Step 2: Get audio duration and estimate processing time
            verbose_log(self.logger, "Analyzing audio file and estimating processing time")
            audio_duration = get_audio_duration(audio_path)
            if audio_duration:
                time_estimate = estimate_processing_time(audio_duration, quality_level)
                self.logger.info(f"Audio duration: {audio_duration:.2f}s, "
                               f"Estimated processing time: {time_estimate['estimated_total_minutes']:.1f} minutes")
                verbose_log(self.logger, "Processing time estimate", **time_estimate)
            else:
                self.logger.warning("Could not determine audio duration for time estimation")

            # Step 3: Get quality configuration
            verbose_log(self.logger, "Configuring quality settings")
            if quality_level not in self.quality_configs:
                quality_level = self.hardware_config["recommended_quality"]
                verbose_log(self.logger, f"Quality level adjusted to: {quality_level}")

            config = self.quality_configs[quality_level]
            verbose_log(self.logger, "Quality configuration", **config)

            # Step 4: Create output directory
            verbose_log(self.logger, f"Creating output directory: {output_dir}")
            os.makedirs(output_dir, exist_ok=True)

            # Generate unique output filename
            output_filename = f"avatar_{uuid.uuid4().hex[:8]}.mp4"

            # Step 5: Prepare driving video for LivePortrait
            # LivePortrait needs a video with faces for driving motion
            # We'll use the reference image as a simple "video" or find an alternative approach
            verbose_log(self.logger, "Preparing driving input for LivePortrait")
            self.logger.info("LivePortrait requires face motion - using reference image as driving")

            # Create a simple video from the reference image to drive basic motion
            driving_video_path = self._create_driving_video_from_image(
                reference_image=reference_image,
                audio_path=audio_path,
                output_dir=output_dir
            )

            if not driving_video_path:
                return AvatarGenerationResult(
                    success=False,
                    error="Failed to create driving video from reference image"
                )

            audio_convert_time = 0  # No audio conversion in this approach
            verbose_log(self.logger, "Driving video created from reference image")
            self.logger.info(f"Driving video created: {driving_video_path}")

            # Step 6: Build LivePortrait command
            verbose_log(self.logger, "Building LivePortrait execution command")
            cmd = self._build_liveportrait_command(
                source=reference_image,
                driving=driving_video_path,
                output_dir=output_dir,
                config=config
            )

            verbose_log(self.logger, "LivePortrait command", command=" ".join(cmd))

            # Step 7: Start LivePortrait processing
            self.logger.info(f"Starting LivePortrait generation with quality: {quality_level}")
            self.logger.info(f"Timeout configured for: {config['timeout']}s ({config['timeout']/60:.1f} minutes)")
            jlog(self.logger, logging.INFO,
                event="liveportrait_generation_started",
                quality_level=quality_level,
                source_image=reference_image,
                audio_path=audio_path,
                output_dir=output_dir,
                timeout_seconds=config["timeout"])

            # Set environment for M1 Mac optimization
            verbose_log(self.logger, "Setting up execution environment")
            env = os.environ.copy()
            env["PYTORCH_ENABLE_MPS_FALLBACK"] = "1"

            # Execute LivePortrait with progress tracking
            liveportrait_start = time.time()
            self.logger.info("🚀 Executing LivePortrait avatar generation...")
            self.logger.info("💡 This process can take several minutes. Progress updates will be shown below.")
            self.logger.info("🔄 Phase 1: Model loading and initialization...")
            self.logger.info("🔄 Phase 2: Face detection and feature extraction...")
            self.logger.info("🔄 Phase 3: Avatar animation generation...")
            self.logger.info("🔄 Phase 4: Video encoding and finalization...")
            verbose_log(self.logger, f"Working directory: {self.liveportrait_path}")

            # Calculate estimated duration for progress reporting
            estimated_duration = time_estimate['estimated_total_seconds'] if audio_duration else 600  # Default 10 min
            self.logger.info(f"📊 Estimated total processing time: {estimated_duration/60:.1f} minutes")
            self.logger.info("⏰ Progress updates every 30 seconds, 1 minute, 2 minutes, 5 minutes...")
            self.logger.info("───────────────────────────────────────────────────────")

            # Use progress-aware subprocess execution
            result = run_subprocess_with_progress(
                cmd,
                logger=self.logger,
                operation_name="LivePortrait Avatar Generation",
                estimated_duration=estimated_duration,
                cwd=self.liveportrait_path,
                capture_output=True,
                text=True,
                timeout=config["timeout"],
                env=env
            )

            liveportrait_time = time.time() - liveportrait_start
            processing_time = time.time() - start_time

            self.logger.info("───────────────────────────────────────────────────────")
            self.logger.info(f"✅ LivePortrait execution completed in {liveportrait_time:.2f}s")
            verbose_log(self.logger, f"LivePortrait execution details",
                       execution_time=liveportrait_time,
                       return_code=result.returncode,
                       stdout_length=len(result.stdout) if result.stdout else 0,
                       stderr_length=len(result.stderr) if result.stderr else 0)

            if result.returncode != 0:
                error_msg = f"LivePortrait failed: {result.stderr}"
                self.logger.error(error_msg)
                verbose_log(self.logger, "LivePortrait stderr output", stderr=result.stderr)
                return AvatarGenerationResult(
                    success=False,
                    error=error_msg,
                    processing_time=processing_time
                )

            # Step 8: Find and validate generated video
            verbose_log(self.logger, "Searching for generated video file")
            output_video_path = self._find_generated_video(output_dir)

            if not output_video_path:
                self.logger.error(f"Generated video not found in output directory: {output_dir}")
                verbose_log(self.logger, "Available files in output directory",
                           files=[str(f) for f in Path(output_dir).glob("*")])
                return AvatarGenerationResult(
                    success=False,
                    error="Generated video not found in output directory",
                    processing_time=processing_time
                )

            # Step 9: Success - log completion details
            total_time_minutes = processing_time / 60
            self.logger.info(f"Avatar generation completed successfully!")
            self.logger.info(f"Total processing time: {processing_time:.2f}s ({total_time_minutes:.1f} minutes)")
            self.logger.info(f"Output video: {output_video_path}")

            verbose_log(self.logger, "Avatar generation completed",
                       total_time=processing_time,
                       audio_convert_time=audio_convert_time,
                       liveportrait_time=liveportrait_time,
                       output_path=output_video_path)

            jlog(self.logger, logging.INFO,
                event="liveportrait_generation_completed",
                processing_time=processing_time,
                liveportrait_execution_time=liveportrait_time,
                audio_conversion_time=audio_convert_time,
                output_path=output_video_path,
                quality_level=quality_level)

            return AvatarGenerationResult(
                success=True,
                output_path=output_video_path,
                processing_time=processing_time,
                quality_level=quality_level
            )

        except subprocess.TimeoutExpired:
            elapsed_time = time.time() - start_time
            error_msg = f"LivePortrait timed out after {config['timeout']}s ({config['timeout']/60:.1f} minutes)"
            self.logger.error(error_msg)
            self.logger.error(f"Elapsed time before timeout: {elapsed_time:.2f}s ({elapsed_time/60:.1f} minutes)")

            verbose_log(self.logger, "LivePortrait timeout details",
                       configured_timeout=config['timeout'],
                       elapsed_time=elapsed_time,
                       quality_level=quality_level)

            return AvatarGenerationResult(
                success=False,
                error=error_msg,
                processing_time=elapsed_time
            )

        except Exception as e:
            error_msg = f"Unexpected error in avatar generation: {str(e)}"
            self.logger.error(error_msg)
            return AvatarGenerationResult(
                success=False,
                error=error_msg,
                processing_time=time.time() - start_time
            )

    def generate_avatar_video_from_video(self,
                                       driving_video: str,
                                       reference_image: str,
                                       output_dir: str = "output",
                                       quality_level: str = "standard") -> AvatarGenerationResult:
        """
        Generate avatar video using video as driving motion

        Args:
            driving_video: Path to driving video for motion
            reference_image: Path to source image for avatar
            output_dir: Directory to save output video
            quality_level: "fast", "standard", or "high"

        Returns:
            AvatarGenerationResult with video path and metadata
        """

        start_time = time.time()

        try:
            # Validate inputs
            if not Path(driving_video).exists():
                return AvatarGenerationResult(
                    success=False,
                    error=f"Driving video not found: {driving_video}"
                )

            if not Path(reference_image).exists():
                return AvatarGenerationResult(
                    success=False,
                    error=f"Reference image not found: {reference_image}"
                )

            # Get quality configuration
            if quality_level not in self.quality_configs:
                quality_level = self.hardware_config["recommended_quality"]

            config = self.quality_configs[quality_level]

            # Create output directory
            os.makedirs(output_dir, exist_ok=True)

            # Build LivePortrait command for video driving
            cmd = self._build_liveportrait_command(
                source=reference_image,
                driving=driving_video,
                output_dir=output_dir,
                config=config
            )

            self.logger.info(f"Starting LivePortrait video generation with quality: {quality_level}")
            jlog(self.logger, logging.INFO,
                event="liveportrait_video_generation_started",
                quality_level=quality_level,
                source_image=reference_image,
                driving_video=driving_video,
                output_dir=output_dir)

            # Set environment for M1 Mac optimization
            env = os.environ.copy()
            env["PYTORCH_ENABLE_MPS_FALLBACK"] = "1"

            # Execute LivePortrait with progress reporting
            estimated_duration = min(config["timeout"] * 0.8, 900)  # Estimate 80% of timeout or max 15 min
            result = run_subprocess_with_progress(
                cmd,
                self.logger,
                operation_name="LivePortrait Avatar Generation",
                estimated_duration=estimated_duration,
                cwd=self.liveportrait_path,
                capture_output=True,
                text=True,
                timeout=config["timeout"],
                env=env
            )

            processing_time = time.time() - start_time

            if result.returncode != 0:
                error_msg = f"LivePortrait video generation failed: {result.stderr}"
                self.logger.error(error_msg)
                return AvatarGenerationResult(
                    success=False,
                    error=error_msg,
                    processing_time=processing_time
                )

            # Find the generated video file
            output_video_path = self._find_generated_video(output_dir)

            if not output_video_path:
                return AvatarGenerationResult(
                    success=False,
                    error="Generated video not found in output directory",
                    processing_time=processing_time
                )

            # Post-process for avatar optimization
            processed_video_path = self._post_process_avatar_video(output_video_path, config)
            if processed_video_path:
                output_video_path = processed_video_path

            self.logger.info(f"Avatar video generation completed in {processing_time:.2f}s")
            jlog(self.logger, logging.INFO,
                event="liveportrait_video_generation_completed",
                processing_time=processing_time,
                output_path=output_video_path,
                quality_level=quality_level)

            return AvatarGenerationResult(
                success=True,
                output_path=output_video_path,
                processing_time=processing_time,
                quality_level=quality_level
            )

        except subprocess.TimeoutExpired:
            error_msg = f"LivePortrait video generation timed out after {config['timeout']}s"
            self.logger.error(error_msg)
            return AvatarGenerationResult(
                success=False,
                error=error_msg,
                processing_time=time.time() - start_time
            )

        except Exception as e:
            error_msg = f"Unexpected error in avatar video generation: {str(e)}"
            self.logger.error(error_msg)
            return AvatarGenerationResult(
                success=False,
                error=error_msg,
                processing_time=time.time() - start_time
            )

    def _build_liveportrait_command(self,
                                  source: str,
                                  driving: str,
                                  output_dir: str,
                                  config: Dict[str, Any]) -> list:
        """Build the LivePortrait inference command"""

        # Convert to absolute paths
        source_abs = str(Path(source).resolve())
        driving_abs = str(Path(driving).resolve())
        output_dir_abs = str(Path(output_dir).resolve())

        cmd = [
            self.python_path, "inference.py",
            "--source", source_abs,
            "--driving", driving_abs,
            "--output-dir", output_dir_abs,
            "--flag-pasteback",  # Paste back to original image space
            "--flag-do-crop",  # Crop source to face space for single-face avatar
            "--flag-stitching",  # Use stitching for small head movements
            "--flag-relative-motion",  # Use relative motion for natural animation
            "--source-max-dim", str(config["source_max_dim"])
        ]

        # Add half precision flag
        if config["flag_use_half_precision"]:
            cmd.append("--flag-use-half-precision")
        else:
            cmd.append("--no-flag-use-half-precision")

        # Add device options
        if config["device_options"]:
            cmd.extend(config["device_options"].split())

        return cmd

    def _find_generated_video(self, output_dir: str) -> Optional[str]:
        """Find the most recently generated video in output directory"""

        try:
            output_path = Path(output_dir)
            video_files = list(output_path.glob("*.mp4"))

            if not video_files:
                return None

            # Return the most recently created video
            latest_video = max(video_files, key=lambda p: p.stat().st_mtime)
            return str(latest_video)

        except Exception as e:
            self.logger.error(f"Error finding generated video: {e}")
            return None

    def extract_audio_from_video(self, video_path: str, output_audio_path: str) -> bool:
        """Extract audio from video for voice cloning"""

        try:
            cmd = [
                "ffmpeg",
                "-i", video_path,
                "-vn",  # No video
                "-acodec", "pcm_s16le",
                "-ar", "22050",  # 22kHz sample rate
                "-ac", "1",  # Mono
                "-y", output_audio_path
            ]

            result = subprocess.run(cmd, capture_output=True, text=True)

            if result.returncode != 0:
                self.logger.error(f"Audio extraction failed: {result.stderr}")
                return False

            return True

        except Exception as e:
            self.logger.error(f"Error extracting audio: {e}")
            return False

    def extract_reference_frame(self, video_path: str, output_image_path: str, frame_number: int = 0) -> bool:
        """Extract a reference frame from video for avatar generation"""

        try:
            cmd = [
                "ffmpeg",
                "-i", video_path,
                "-vf", f"select=eq(n\\,{frame_number})",
                "-q:v", "3",
                "-frames:v", "1",
                "-y", output_image_path
            ]

            result = subprocess.run(cmd, capture_output=True, text=True)

            if result.returncode != 0:
                self.logger.error(f"Frame extraction failed: {result.stderr}")
                return False

            return True

        except Exception as e:
            self.logger.error(f"Error extracting reference frame: {e}")
            return False

    def _convert_audio_to_driving_video(self, audio_path: str, output_dir: str) -> Optional[str]:
        """Convert audio file to video with waveform visualization for LivePortrait driving"""

        try:
            output_dir_path = Path(output_dir)
            output_video_path = output_dir_path / f"driving_video_{uuid.uuid4().hex[:8]}.mp4"

            # Create a simple video with waveform visualization that LivePortrait can process
            # Use a simpler approach that's more compatible with LivePortrait's video processing
            cmd = [
                "ffmpeg",
                "-i", audio_path,
                "-f", "lavfi",
                "-i", "color=black:size=512x512:rate=25",
                "-filter_complex",
                "[0:a]showwaves=s=512x512:mode=line:rate=25:colors=white[waveform];"
                "[1:v][waveform]overlay[v]",
                "-map", "[v]",
                "-map", "0:a",
                "-c:v", "libx264",
                "-preset", "fast",
                "-pix_fmt", "yuv420p",
                "-c:a", "aac",
                "-shortest",
                "-y", str(output_video_path)
            ]

            verbose_log(self.logger, "Starting FFmpeg audio-to-video conversion",
                       input_audio=audio_path,
                       output_video=str(output_video_path),
                       command=" ".join(cmd))

            self.logger.info(f"Converting audio to driving video: {audio_path} -> {output_video_path}")

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)

            if result.returncode != 0:
                self.logger.error(f"Audio to video conversion failed: {result.stderr}")
                verbose_log(self.logger, "FFmpeg conversion error", stderr=result.stderr)
                return None

            if not output_video_path.exists():
                self.logger.error("Converted video file not found after conversion")
                verbose_log(self.logger, "Output file missing after conversion",
                           expected_path=str(output_video_path),
                           working_directory=str(output_dir_path))
                return None

            # Get file size and validate video properties
            file_size = output_video_path.stat().st_size if output_video_path.exists() else 0

            # Validate the video file using ffprobe
            try:
                probe_cmd = [
                    "ffprobe", "-v", "quiet", "-print_format", "json",
                    "-show_streams", str(output_video_path)
                ]
                probe_result = subprocess.run(probe_cmd, capture_output=True, text=True, timeout=30)

                if probe_result.returncode == 0:
                    probe_data = json.loads(probe_result.stdout)
                    video_streams = [s for s in probe_data.get('streams', []) if s.get('codec_type') == 'video']
                    audio_streams = [s for s in probe_data.get('streams', []) if s.get('codec_type') == 'audio']

                    if video_streams:
                        video_info = video_streams[0]
                        verbose_log(self.logger, "Generated video properties",
                                   width=video_info.get('width'),
                                   height=video_info.get('height'),
                                   codec=video_info.get('codec_name'),
                                   duration=video_info.get('duration'),
                                   frame_rate=video_info.get('r_frame_rate'))
                        self.logger.info(f"Video created: {video_info.get('width')}x{video_info.get('height')}, "
                                       f"codec: {video_info.get('codec_name')}, "
                                       f"duration: {video_info.get('duration')}s")
                    else:
                        self.logger.warning("No video stream found in generated file")

                    if not audio_streams:
                        self.logger.warning("No audio stream found in generated file")
                else:
                    verbose_log(self.logger, "ffprobe validation failed", stderr=probe_result.stderr)

            except Exception as probe_error:
                verbose_log(self.logger, "Video validation error", error=str(probe_error))

            verbose_log(self.logger, "Audio-to-video conversion completed",
                       output_path=str(output_video_path),
                       file_size_bytes=file_size,
                       file_size_mb=file_size / (1024*1024))

            self.logger.info(f"Successfully converted audio to driving video: {output_video_path}")
            return str(output_video_path)

        except Exception as e:
            self.logger.error(f"Error converting audio to driving video: {e}")
            return None

    def _create_driving_video_from_image(self, reference_image: str, audio_path: str, output_dir: str) -> Optional[str]:
        """Create a simple driving video from reference image for LivePortrait"""

        try:
            output_dir_path = Path(output_dir)
            output_video_path = output_dir_path / f"driving_video_{uuid.uuid4().hex[:8]}.mp4"

            # Get audio duration for video length
            audio_duration = get_audio_duration(audio_path)
            if not audio_duration:
                self.logger.error("Could not determine audio duration")
                return None

            # Create a simple video from the reference image with slight motion
            # This approach creates a minimal "driving" video that LivePortrait can process
            cmd = [
                "ffmpeg",
                "-loop", "1",
                "-i", reference_image,
                "-i", audio_path,
                "-filter_complex",
                # Add very subtle zoom/pan to create minimal motion for face detection
                "[0:v]scale=512:512,zoompan=z='if(lte(zoom,1.0),1.5,max(1.001,zoom-0.0015))':d=25*{:.2f}:s=512x512[v]".format(audio_duration),
                "-map", "[v]",
                "-map", "1:a",
                "-c:v", "libx264",
                "-preset", "fast",
                "-pix_fmt", "yuv420p",
                "-c:a", "aac",
                "-t", str(audio_duration),
                "-y", str(output_video_path)
            ]

            verbose_log(self.logger, "Creating driving video from reference image",
                       reference_image=reference_image,
                       audio_duration=audio_duration,
                       output_video=str(output_video_path),
                       command=" ".join(cmd))

            self.logger.info(f"📹 Creating driving video from reference image ({audio_duration:.1f}s duration)")
            self.logger.info("⏱️  This step typically takes 30-60 seconds...")

            # Use progress reporting for longer video creation
            estimated_ffmpeg_time = max(30, audio_duration * 2)  # Rough estimate
            result = run_subprocess_with_progress(
                cmd,
                logger=self.logger,
                operation_name="Driving Video Creation",
                estimated_duration=estimated_ffmpeg_time,
                capture_output=True,
                text=True,
                timeout=180
            )

            if result.returncode != 0:
                self.logger.error(f"Driving video creation failed: {result.stderr}")
                verbose_log(self.logger, "FFmpeg driving video creation error", stderr=result.stderr)
                return None

            if not output_video_path.exists():
                self.logger.error("Driving video file not found after creation")
                return None

            # Validate the created video
            file_size = output_video_path.stat().st_size
            verbose_log(self.logger, "Driving video created successfully",
                       output_path=str(output_video_path),
                       file_size_bytes=file_size,
                       file_size_mb=file_size / (1024*1024))

            self.logger.info(f"Successfully created driving video from reference image: {output_video_path}")
            return str(output_video_path)

        except Exception as e:
            self.logger.error(f"Error creating driving video from image: {e}")
            verbose_log(self.logger, "Driving video creation error", error=str(e))
            return None

    def _post_process_avatar_video(self, video_path: str, config: Dict[str, Any]) -> Optional[str]:
        """Post-process video for optimal avatar display"""

        try:
            output_path = video_path.replace('.mp4', '_avatar_optimized.mp4')

            # Create optimized avatar video with face cropping and centering
            cmd = [
                "ffmpeg", "-i", video_path,
                "-vf", "scale=512:512:force_original_aspect_ratio=increase,crop=512:512",
                "-c:v", "libx264",
                "-preset", "fast",
                "-crf", "18",  # High quality
                "-pix_fmt", "yuv420p",
                "-c:a", "aac",
                "-b:a", "128k",
                "-movflags", "+faststart",  # Optimize for streaming
                "-y", output_path
            ]

            result = subprocess.run(cmd, capture_output=True, text=True)

            if result.returncode != 0:
                self.logger.warning(f"Avatar optimization failed, using original: {result.stderr}")
                return None

            self.logger.info(f"Avatar video optimized successfully: {output_path}")
            return output_path

        except Exception as e:
            self.logger.warning(f"Avatar optimization error: {e}")
            return None