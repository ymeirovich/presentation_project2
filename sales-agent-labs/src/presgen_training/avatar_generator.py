"""
Avatar Generation System

MuseTalk integration for creating avatar videos from audio and presenter images.
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
import json

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
        self.musetalk_path = None
        self._detect_musetalk_installation()
        
        jlog(self.logger, logging.INFO,
             event="avatar_generator_init",
             quality=quality,
             musetalk_available=self.musetalk_path is not None)

    def _detect_musetalk_installation(self) -> None:
        """Detect MuseTalk installation or provide installation guidance"""
        
        # Common installation paths
        potential_paths = [
            Path("./MuseTalk"),
            Path("../MuseTalk"),
            Path.home() / "MuseTalk",
            Path("/opt/MuseTalk")
        ]
        
        for path in potential_paths:
            if path.exists() and (path / "app.py").exists():
                self.musetalk_path = path
                jlog(self.logger, logging.INFO,
                     event="musetalk_detected",
                     path=str(path))
                return
        
        # MuseTalk not found - log installation instructions
        jlog(self.logger, logging.WARNING,
             event="musetalk_not_found",
             installation_guide="MuseTalk not found. Please run installation script.")

    def generate_tts_audio(self, text: str, output_path: Path, reference_video_path: Optional[Path] = None) -> Optional[Path]:
        """Generate TTS audio from text, optionally using voice cloning from reference video"""
        jlog(self.logger, logging.INFO,
             event="tts_generation_start",
             text_length=len(text),
             output_path=str(output_path),
             voice_cloning_enabled=reference_video_path is not None)
        
        start_time = time.time()
        
        # Attempt voice cloning if reference video provided
        if reference_video_path:
            cloned_audio = self._generate_cloned_voice_audio(text, output_path, reference_video_path)
            if cloned_audio:
                return cloned_audio
            
            # If voice cloning fails, fall back to TTS
            jlog(self.logger, logging.WARNING,
                 event="voice_cloning_fallback_to_tts",
                 reason="Voice cloning failed, using TTS")
        
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
                     file_size_bytes=output_path.stat().st_size,
                     method="gtts")
                
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

    def _generate_cloned_voice_audio(self, text: str, output_path: Path, reference_video_path: Path) -> Optional[Path]:
        """Generate voice-cloned audio using reference video as voice sample"""
        jlog(self.logger, logging.INFO,
             event="voice_cloning_start",
             text_length=len(text),
             reference_video=str(reference_video_path))
        
        try:
            # Step 1: Extract clean audio from reference video with enhanced processing
            reference_audio_path = output_path.with_suffix('.reference.wav')
            
            # Enhanced audio extraction with noise reduction, normalization, and voice isolation
            extract_cmd = [
                "ffmpeg", "-i", str(reference_video_path),
                "-vn",  # No video
                "-acodec", "pcm_s16le",
                "-ar", "22050",  # Higher sample rate for better voice cloning quality
                "-ac", "1",  # Mono
                "-af", (
                    "highpass=f=80,"           # Remove low-frequency noise
                    "lowpass=f=8000,"          # Remove high-frequency noise  
                    "afftdn=nf=-25,"           # Noise reduction
                    "compand=attacks=0.3:decays=0.8:points=0/-90|0/-70|0.5/-20|1/0,"  # Dynamic range compression
                    "volume=2.0,"              # Amplify voice
                    "silenceremove=start_periods=1:start_silence=0.1:start_threshold=0.02"  # Remove initial silence
                ),
                "-t", "30",  # Limit to first 30 seconds for voice sample
                "-y",
                str(reference_audio_path)
            ]
            
            result = subprocess.run(extract_cmd, capture_output=True, text=True, timeout=30)
            if result.returncode != 0:
                jlog(self.logger, logging.ERROR,
                     event="voice_reference_extraction_failed",
                     error=result.stderr)
                return None
            
            # Step 2: Check for voice cloning libraries
            voice_cloned_audio = None
            
            # Try TortoiseTS voice cloning if available
            try:
                voice_cloned_audio = self._tortoise_voice_clone(text, output_path, reference_audio_path)
            except Exception as e:
                jlog(self.logger, logging.WARNING,
                     event="tortoise_voice_cloning_failed",
                     error=str(e))
            
            # Try RVC voice cloning if TortoiseTS failed
            if not voice_cloned_audio:
                try:
                    voice_cloned_audio = self._rvc_voice_clone(text, output_path, reference_audio_path)
                except Exception as e:
                    jlog(self.logger, logging.WARNING,
                         event="rvc_voice_cloning_failed", 
                         error=str(e))
            
            # Try Coqui TTS voice cloning as fallback
            if not voice_cloned_audio:
                try:
                    voice_cloned_audio = self._coqui_voice_clone(text, output_path, reference_audio_path)
                except Exception as e:
                    jlog(self.logger, logging.WARNING,
                         event="coqui_voice_cloning_failed",
                         error=str(e))
            
            # Clean up reference audio
            reference_audio_path.unlink(missing_ok=True)
            
            if voice_cloned_audio:
                jlog(self.logger, logging.INFO,
                     event="voice_cloning_success",
                     output_path=str(voice_cloned_audio))
                return voice_cloned_audio
            
        except Exception as e:
            jlog(self.logger, logging.ERROR,
                 event="voice_cloning_exception",
                 error=str(e))
        
        return None
    
    def _coqui_voice_clone(self, text: str, output_path: Path, reference_audio_path: Path) -> Optional[Path]:
        """Voice cloning using Coqui TTS via MuseTalk Python 3.10 environment"""
        try:
            # Use voice cloning wrapper script with MuseTalk Python 3.10 environment
            script_dir = Path(__file__).parent.parent.parent
            wrapper_path = script_dir / "voice_clone_wrapper.py"
            musetalk_python = script_dir / "musetalk_env" / "bin" / "python"
            
            if not wrapper_path.exists():
                jlog(self.logger, logging.ERROR,
                     event="voice_clone_wrapper_not_found",
                     path=str(wrapper_path))
                return None
                
            if not musetalk_python.exists():
                jlog(self.logger, logging.ERROR,
                     event="musetalk_python_not_found", 
                     path=str(musetalk_python))
                return None
            
            # Build voice cloning command
            cmd = [
                str(musetalk_python),
                str(wrapper_path),
                "--text", text,
                "--reference", str(reference_audio_path),
                "--output", str(output_path),
                "--json-output"
            ]
            
            jlog(self.logger, logging.INFO,
                 event="voice_cloning_start",
                 command=" ".join([str(c) for c in cmd[:4]]) + "...")  # Log command without full text
            
            # Execute voice cloning with extended timeout (TTS model loading takes time)
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300  # 5 minutes for voice cloning
            )
            
            if result.returncode == 0:
                try:
                    # Parse JSON response from voice cloning wrapper
                    response = json.loads(result.stdout)
                    if response.get("success", False):
                        jlog(self.logger, logging.INFO,
                             event="coqui_voice_cloning_success",
                             method=response.get("method", "YourTTS"),
                             file_size_mb=response.get("file_size_mb", 0))
                        return output_path
                    else:
                        jlog(self.logger, logging.ERROR,
                             event="voice_cloning_failed",
                             error=response.get("error", "Unknown error"))
                except json.JSONDecodeError:
                    jlog(self.logger, logging.ERROR,
                         event="voice_cloning_json_parse_failed",
                         stdout=result.stdout[:500])  # First 500 chars
            else:
                jlog(self.logger, logging.ERROR,
                     event="voice_cloning_process_failed",
                     returncode=result.returncode,
                     stderr=result.stderr[:500])  # First 500 chars
                     
        except subprocess.TimeoutExpired:
            jlog(self.logger, logging.ERROR,
                 event="voice_cloning_timeout")
        except Exception as e:
            jlog(self.logger, logging.ERROR,
                 event="coqui_voice_cloning_error",
                 error=str(e))
        
        return None
    
    def _tortoise_voice_clone(self, text: str, output_path: Path, reference_audio_path: Path) -> Optional[Path]:
        """Voice cloning using TortoiseTS (if available)"""
        try:
            # Import TortoiseTS if available
            from tortoise.api import TextToSpeech
            from tortoise.utils.audio import load_audio, save_audio
            import torch
            
            # Load TortoiseTS model
            tts = TextToSpeech()
            
            # Load reference audio
            reference_audio = load_audio(str(reference_audio_path), 22050)
            
            # Generate cloned voice
            gen = tts.tts_with_preset(
                text, 
                voice_samples=[reference_audio], 
                preset='fast'  # Use fast preset for speed
            )
            
            # Save cloned audio
            save_audio(gen.squeeze(0).cpu(), str(output_path), 16000)
            
            if output_path.exists():
                jlog(self.logger, logging.INFO,
                     event="tortoise_voice_cloning_success")
                return output_path
                
        except ImportError:
            jlog(self.logger, logging.INFO,
                 event="tortoise_not_available",
                 solution="TortoiseTS not installed")
        except Exception as e:
            jlog(self.logger, logging.ERROR,
                 event="tortoise_voice_cloning_error",
                 error=str(e))
        
        return None
    
    def _rvc_voice_clone(self, text: str, output_path: Path, reference_audio_path: Path) -> Optional[Path]:
        """Voice cloning using RVC (Retrieval-based Voice Conversion)"""
        # RVC is more complex to integrate, placeholder for future implementation
        jlog(self.logger, logging.INFO,
             event="rvc_voice_cloning_not_implemented",
             note="RVC integration planned for future release")
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
        
        if not self.musetalk_path:
            jlog(self.logger, logging.ERROR, event="musetalk_not_found")
            return False
        
        start_time = time.time()
        
        # Use MuseTalk via wrapper script
        wrapper_path = Path(__file__).parent.parent.parent / "musetalk_wrapper.py"
        musetalk_env_path = Path(__file__).parent.parent.parent / "musetalk_env" / "bin" / "python"
        
        # Build MuseTalk command with absolute paths
        cmd = [
            str(musetalk_env_path),
            str(wrapper_path),
            "--audio", str(audio_path.resolve()),
            "--image", str(image_path.resolve()),
            "--output", str(output_path.resolve()),
            "--json-output"
        ]
            
        jlog(self.logger, logging.INFO,
             event="musetalk_command_prepared",
             command=" ".join(cmd))
        
        # Execute MuseTalk wrapper
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=3700  # 61+ minute timeout (longer than wrapper's 60 minutes)
        )
        
        if result.returncode == 0:
            try:
                response = json.loads(result.stdout)
                if response.get("success", False):
                    duration = time.time() - start_time
                    jlog(self.logger, logging.INFO,
                         event="avatar_video_generation_complete",
                         output_path=str(output_path),
                         duration_seconds=duration,
                         file_size_mb=round(output_path.stat().st_size / (1024*1024), 2))
                    return True
                else:
                    jlog(self.logger, logging.ERROR,
                         event="musetalk_wrapper_failed",
                         error=response.get("error", "Unknown error"),
                         stderr=response.get("stderr"))
                    return False
            except json.JSONDecodeError:
                jlog(self.logger, logging.ERROR,
                     event="musetalk_json_parse_failed",
                     stdout=result.stdout)
                return False
        else:
            jlog(self.logger, logging.ERROR,
                 event="musetalk_execution_failed",
                 returncode=result.returncode,
                 stderr=result.stderr[:1000])
            return False


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
            "musetalk": self.musetalk_path is not None
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