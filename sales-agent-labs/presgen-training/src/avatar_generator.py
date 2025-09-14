"""
Avatar Generation System

SadTalker integration for creating avatar videos from audio and presenter images.
Includes TTS generation and quality-adaptive processing.
"""

import logging
import subprocess
import time
from pathlib import Path
from typing import Optional, Dict, Any
import sys
import os
import shutil

# Add project root for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.common.jsonlog import jlog


class AvatarGenerator:
    """
    Avatar video generation using SadTalker technology.
    
    Handles TTS audio generation and avatar video synthesis with quality controls.
    """
    
    def __init__(self, quality: str = "standard", logger: Optional[logging.Logger] = None):
        self.quality = quality
        self.logger = logger or logging.getLogger("presgen_training.avatar_generator")
        
        # Quality-specific settings
        self.quality_settings = {
            "fast": {
                "size": 256,
                "enhancer": None,
                "preprocess": "crop",
                "still": True
            },
            "standard": {
                "size": 512, 
                "enhancer": "gfpgan",
                "preprocess": "resize",
                "still": False
            },
            "high": {
                "size": 1024,
                "enhancer": "RestoreFormer",
                "preprocess": "full",
                "still": False
            }
        }
        
        # SadTalker installation paths
        self.sadtalker_path = None
        self._detect_sadtalker_installation()
        
        jlog(self.logger, logging.INFO,
             event="avatar_generator_init",
             quality=quality,
             sadtalker_available=self.sadtalker_path is not None)

    def _detect_sadtalker_installation(self) -> None:
        """Detect SadTalker installation or provide installation guidance"""
        
        # Common installation paths
        potential_paths = [
            Path.home() / "SadTalker",
            Path("/opt/SadTalker"),
            Path("./SadTalker"),
            Path("../SadTalker")
        ]
        
        for path in potential_paths:
            if path.exists() and (path / "inference.py").exists():
                self.sadtalker_path = path
                jlog(self.logger, logging.INFO,
                     event="sadtalker_detected",
                     path=str(path))
                return
        
        # SadTalker not found - log installation instructions
        jlog(self.logger, logging.WARNING,
             event="sadtalker_not_found",
             installation_guide="Run: git clone https://github.com/OpenTalker/SadTalker.git && cd SadTalker && pip install -r requirements.txt")

    def generate_tts_audio(self, text: str, output_path: Path) -> Optional[Path]:
        """Generate TTS audio from text using gTTS"""
        jlog(self.logger, logging.INFO,
             event="tts_generation_start",
             text_length=len(text),
             output_path=str(output_path))
        
        start_time = time.time()
        
        try:
            # Use gTTS for text-to-speech
            import gtts
            
            # Generate TTS
            tts = gtts.gTTS(text=text, lang='en', slow=False)
            
            # Save to temporary file first
            temp_path = output_path.with_suffix('.temp.mp3')
            tts.save(str(temp_path))
            
            # Convert MP3 to WAV using ffmpeg for better SadTalker compatibility
            ffmpeg_cmd = [
                "ffmpeg", "-i", str(temp_path),
                "-acodec", "pcm_s16le", 
                "-ar", "16000",  # 16kHz sample rate
                "-ac", "1",      # Mono
                "-y",            # Overwrite
                str(output_path)
            ]
            
            result = subprocess.run(
                ffmpeg_cmd,
                capture_output=True,
                text=True,
                timeout=60
            )
            
            # Clean up temp file
            temp_path.unlink(missing_ok=True)
            
            if result.returncode == 0:
                duration = time.time() - start_time
                
                jlog(self.logger, logging.INFO,
                     event="tts_generation_complete",
                     output_path=str(output_path),
                     duration_seconds=duration,
                     file_size_bytes=output_path.stat().st_size)
                
                return output_path
            else:
                jlog(self.logger, logging.ERROR,
                     event="tts_ffmpeg_conversion_failed",
                     error=result.stderr)
                
        except ImportError:
            jlog(self.logger, logging.ERROR,
                 event="tts_import_failed",
                 solution="Install with: pip3 install gtts")
                 
        except subprocess.TimeoutExpired:
            jlog(self.logger, logging.ERROR,
                 event="tts_conversion_timeout")
                 
        except Exception as e:
            jlog(self.logger, logging.ERROR,
                 event="tts_generation_failed",
                 error=str(e))
        
        return None

    def generate_avatar_video(
        self, 
        audio_path: Path, 
        image_path: Path, 
        output_path: Path
    ) -> bool:
        """Generate avatar video using SadTalker"""
        
        jlog(self.logger, logging.INFO,
             event="avatar_video_generation_start",
             audio_path=str(audio_path),
             image_path=str(image_path),
             output_path=str(output_path),
             quality=self.quality)
        
        if not self.sadtalker_path:
            # Fallback: create a simple video with static image and audio
            return self._create_static_video_fallback(audio_path, image_path, output_path)
        
        start_time = time.time()
        
        try:
            # Prepare SadTalker command
            settings = self.quality_settings[self.quality]
            
            # Build SadTalker command
            cmd = [
                "python3", str(self.sadtalker_path / "inference.py"),
                "--driven_audio", str(audio_path),
                "--source_image", str(image_path),
                "--result_dir", str(output_path.parent),
                "--size", str(settings["size"]),
                "--preprocess", settings["preprocess"]
            ]
            
            # Add optional enhancer
            if settings["enhancer"]:
                cmd.extend(["--enhancer", settings["enhancer"]])
                
            # Add still mode for fast quality
            if settings["still"]:
                cmd.append("--still")
            
            jlog(self.logger, logging.INFO,
                 event="sadtalker_command_prepared",
                 command=" ".join(cmd))
            
            # Execute SadTalker
            result = subprocess.run(
                cmd,
                cwd=str(self.sadtalker_path),
                capture_output=True,
                text=True,
                timeout=600  # 10 minute timeout
            )
            
            if result.returncode == 0:
                # SadTalker creates output in a subdirectory - find the generated video
                generated_video = self._find_sadtalker_output(output_path.parent)
                
                if generated_video and generated_video.exists():
                    # Move to desired output path
                    shutil.move(str(generated_video), str(output_path))
                    
                    duration = time.time() - start_time
                    
                    jlog(self.logger, logging.INFO,
                         event="avatar_video_generation_complete",
                         output_path=str(output_path),
                         duration_seconds=duration,
                         file_size_mb=round(output_path.stat().st_size / (1024*1024), 2))
                    
                    return True
                else:
                    jlog(self.logger, logging.ERROR,
                         event="sadtalker_output_not_found",
                         expected_dir=str(output_path.parent))
            else:
                jlog(self.logger, logging.ERROR,
                     event="sadtalker_execution_failed",
                     returncode=result.returncode,
                     stderr=result.stderr[:1000])  # First 1000 chars of error
                     
        except subprocess.TimeoutExpired:
            jlog(self.logger, logging.ERROR,
                 event="sadtalker_timeout")
                 
        except Exception as e:
            jlog(self.logger, logging.ERROR,
                 event="avatar_video_generation_exception",
                 error=str(e))
        
        # Fallback on any failure
        return self._create_static_video_fallback(audio_path, image_path, output_path)

    def _find_sadtalker_output(self, result_dir: Path) -> Optional[Path]:
        """Find SadTalker output video file"""
        
        # SadTalker typically creates subdirectories with timestamps
        for subdir in result_dir.iterdir():
            if subdir.is_dir():
                for video_file in subdir.glob("*.mp4"):
                    return video_file
                    
        # Also check direct output
        for video_file in result_dir.glob("*.mp4"):
            return video_file
            
        return None

    def _create_static_video_fallback(
        self, 
        audio_path: Path, 
        image_path: Path, 
        output_path: Path
    ) -> bool:
        """Create static video fallback when SadTalker unavailable"""
        
        jlog(self.logger, logging.WARNING,
             event="using_static_video_fallback",
             reason="SadTalker unavailable or failed")
        
        try:
            # Create simple video with static image and audio using ffmpeg
            cmd = [
                "ffmpeg",
                "-loop", "1", "-i", str(image_path),  # Static image
                "-i", str(audio_path),                 # Audio track
                "-c:v", "libx264",
                "-tune", "stillimage", 
                "-c:a", "aac",
                "-b:a", "192k",
                "-pix_fmt", "yuv420p",
                "-shortest",  # End when audio ends
                "-y",         # Overwrite
                str(output_path)
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=120
            )
            
            if result.returncode == 0:
                jlog(self.logger, logging.INFO,
                     event="static_video_fallback_success",
                     output_path=str(output_path),
                     file_size_mb=round(output_path.stat().st_size / (1024*1024), 2))
                return True
            else:
                jlog(self.logger, logging.ERROR,
                     event="static_video_fallback_failed",
                     error=result.stderr)
                     
        except subprocess.TimeoutExpired:
            jlog(self.logger, logging.ERROR,
                 event="static_video_timeout")
                 
        except Exception as e:
            jlog(self.logger, logging.ERROR,
                 event="static_video_exception",
                 error=str(e))
        
        return False

    def check_dependencies(self) -> Dict[str, Any]:
        """Check required dependencies for avatar generation"""
        
        dependencies = {
            "gtts": False,
            "ffmpeg": False, 
            "sadtalker": self.sadtalker_path is not None
        }
        
        # Check gTTS
        try:
            import gtts
            dependencies["gtts"] = True
        except ImportError:
            pass
        
        # Check FFmpeg
        try:
            result = subprocess.run(
                ["ffmpeg", "-version"],
                capture_output=True,
                timeout=5
            )
            dependencies["ffmpeg"] = result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass
        
        jlog(self.logger, logging.INFO,
             event="dependency_check",
             dependencies=dependencies)
        
        return dependencies

    def install_dependencies(self) -> Dict[str, bool]:
        """Attempt to install missing dependencies"""
        
        installation_results = {}
        
        # Install gTTS
        try:
            result = subprocess.run(
                ["pip3", "install", "gtts"],
                capture_output=True,
                text=True,
                timeout=60
            )
            installation_results["gtts"] = result.returncode == 0
            
            if result.returncode == 0:
                jlog(self.logger, logging.INFO, event="gtts_installation_success")
            else:
                jlog(self.logger, logging.ERROR,
                     event="gtts_installation_failed",
                     error=result.stderr)
                     
        except Exception as e:
            jlog(self.logger, logging.ERROR,
                 event="gtts_installation_exception",
                 error=str(e))
            installation_results["gtts"] = False
        
        return installation_results