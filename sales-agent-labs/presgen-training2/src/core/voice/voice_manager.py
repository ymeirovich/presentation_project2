import json
import logging
import subprocess
import time
import uuid
import os
from pathlib import Path
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, asdict
from datetime import datetime

import logging
# Use simple logging for now - can integrate with parent project later
def jlog(logger, level, event, **kwargs):
    """Simple logging wrapper"""
    logger.log(level, f"Event: {event}, Data: {kwargs}")

@dataclass
class VoiceProfile:
    name: str
    language: str
    created_at: str
    model_path: str
    source_video: str
    quality: str = "standard"
    sample_rate: int = 22050

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

class VoiceProfileManager:
    """
    Manage voice cloning profiles with persistence
    Supports multiple TTS engines with fallbacks
    """

    def __init__(self,
                 profiles_db_path: str = "presgen-training2/models/voice-profiles/profiles.json",
                 models_dir: str = "presgen-training2/models/voice-profiles",
                 logger: Optional[logging.Logger] = None):

        self.logger = logger or logging.getLogger("presgen_training2.voice")
        self.profiles_db_path = Path(profiles_db_path)
        self.models_dir = Path(models_dir)

        # Create directories
        self.profiles_db_path.parent.mkdir(parents=True, exist_ok=True)
        self.models_dir.mkdir(parents=True, exist_ok=True)

        # Load existing profiles
        self.profiles = self._load_profiles()

        # TTS engine priority (will implement Coqui TTS first, then fallbacks)
        self.tts_engines = {
            "coqui": {
                "available": self._check_coqui_availability(),
                "priority": 1
            },
            "piper": {
                "available": self._check_piper_availability(),
                "priority": 2
            },
            "builtin": {
                "available": True,  # Always available as fallback
                "priority": 3
            }
        }

    def _load_profiles(self) -> Dict[str, VoiceProfile]:
        """Load voice profiles from disk"""

        if not self.profiles_db_path.exists():
            return {}

        try:
            with open(self.profiles_db_path, 'r') as f:
                profiles_data = json.load(f)

            profiles = {}
            for name, data in profiles_data.items():
                profiles[name] = VoiceProfile(**data)

            self.logger.info(f"Loaded {len(profiles)} voice profiles")
            return profiles

        except Exception as e:
            self.logger.error(f"Error loading voice profiles: {e}")
            return {}

    def _save_profiles(self):
        """Save voice profiles to disk"""

        try:
            profiles_data = {
                name: profile.to_dict()
                for name, profile in self.profiles.items()
            }

            with open(self.profiles_db_path, 'w') as f:
                json.dump(profiles_data, f, indent=2)

            self.logger.info(f"Saved {len(self.profiles)} voice profiles")

        except Exception as e:
            self.logger.error(f"Error saving voice profiles: {e}")

    def _check_coqui_availability(self) -> bool:
        """Check if Coqui TTS is available"""
        try:
            import TTS
            return True
        except ImportError:
            return False

    def _check_piper_availability(self) -> bool:
        """Check if Piper TTS is available"""
        try:
            result = subprocess.run(['piper', '--help'], capture_output=True)
            return result.returncode == 0
        except:
            return False

    def clone_voice_from_video(self,
                             video_path: str,
                             profile_name: str,
                             language: str = "auto") -> Optional[VoiceProfile]:
        """
        Extract and clone voice from reference video

        Process:
        1. Extract clean audio from video
        2. Enhance audio quality (noise reduction, normalization)
        3. Train voice cloning model
        4. Save profile with metadata

        Returns:
            VoiceProfile object with cloning model
        """

        try:
            self.logger.info(f"Starting voice cloning for profile: {profile_name}")

            # Step 1: Extract enhanced audio
            temp_audio_path = self._extract_enhanced_audio(video_path)
            if not temp_audio_path:
                return None

            # Step 2: Language detection
            if language == "auto":
                detected_language = self._detect_language(temp_audio_path)
            else:
                detected_language = language

            # Step 3: Create voice cloning model
            model_path = self._train_voice_model(
                audio_path=temp_audio_path,
                profile_name=profile_name,
                language=detected_language
            )

            if not model_path:
                return None

            # Step 4: Save profile
            profile = VoiceProfile(
                name=profile_name,
                language=detected_language,
                created_at=datetime.now().isoformat(),
                model_path=model_path,
                source_video=video_path,
                quality="standard"
            )

            self.profiles[profile_name] = profile
            self._save_profiles()

            # Cleanup temporary files
            if Path(temp_audio_path).exists():
                os.unlink(temp_audio_path)

            jlog(self.logger, logging.INFO,
                event="voice_profile_created",
                profile_name=profile_name,
                language=detected_language,
                source_video=video_path)

            return profile

        except Exception as e:
            self.logger.error(f"Voice cloning failed: {e}")
            return None

    def _extract_enhanced_audio(self, video_path: str) -> Optional[str]:
        """Extract and enhance audio for voice cloning"""

        try:
            output_path = f"temp/enhanced_audio_{uuid.uuid4().hex}.wav"
            os.makedirs("temp", exist_ok=True)

            # FFmpeg command for enhanced audio extraction
            enhancement_cmd = [
                "ffmpeg", "-i", video_path,
                "-vn",  # No video
                "-acodec", "pcm_s16le",
                "-ar", "22050",  # Optimal sample rate for voice cloning
                "-ac", "1",  # Mono
                "-af", (
                    # Audio enhancement filter chain
                    "highpass=f=80,"              # Remove low-frequency noise
                    "lowpass=f=8000,"             # Remove high-frequency noise
                    "afftdn=nf=-25,"              # Dynamic noise reduction
                    "compand=attacks=0.3:decays=0.8:points=0/-90|0/-70|0.5/-20|1/0,"  # Compression
                    "volume=1.5,"                 # Normalize volume
                    "silenceremove=start_periods=1:start_silence=0.1:start_threshold=0.02"  # Trim silence
                ),
                "-t", "60",  # Use first 60 seconds for voice sample
                "-y", output_path
            ]

            result = subprocess.run(enhancement_cmd, capture_output=True, text=True)

            if result.returncode != 0:
                self.logger.error(f"Audio enhancement failed: {result.stderr}")
                return None

            return output_path

        except Exception as e:
            self.logger.error(f"Error extracting enhanced audio: {e}")
            return None

    def _detect_language(self, audio_path: str) -> str:
        """Detect language from audio (simplified implementation)"""

        # For now, return English as default
        # TODO: Implement proper language detection using whisper or similar
        return "en"

    def _train_voice_model(self, audio_path: str, profile_name: str, language: str) -> Optional[str]:
        """Train voice cloning model using available TTS engine"""

        # Get the best available TTS engine
        best_engine = self._get_best_tts_engine()

        if best_engine == "coqui":
            return self._train_coqui_model(audio_path, profile_name, language)
        elif best_engine == "piper":
            return self._train_piper_model(audio_path, profile_name, language)
        else:
            return self._create_builtin_model(audio_path, profile_name, language)

    def _get_best_tts_engine(self) -> str:
        """Get the best available TTS engine"""

        available_engines = [
            (name, config) for name, config in self.tts_engines.items()
            if config["available"]
        ]

        if not available_engines:
            return "builtin"

        # Sort by priority and return the best one
        best_engine = min(available_engines, key=lambda x: x[1]["priority"])
        return best_engine[0]

    def _train_coqui_model(self, audio_path: str, profile_name: str, language: str) -> Optional[str]:
        """Train voice model using Coqui TTS"""

        try:
            # For now, return a placeholder path
            # TODO: Implement actual Coqui TTS voice cloning
            model_path = self.models_dir / f"{profile_name}_coqui.pth"

            # Create a dummy model file for now
            model_path.write_text(json.dumps({
                "engine": "coqui",
                "profile_name": profile_name,
                "language": language,
                "audio_path": audio_path,
                "created_at": datetime.now().isoformat()
            }))

            return str(model_path)

        except Exception as e:
            self.logger.error(f"Coqui model training failed: {e}")
            return None

    def _train_piper_model(self, audio_path: str, profile_name: str, language: str) -> Optional[str]:
        """Train voice model using Piper TTS"""

        try:
            # For now, return a placeholder path
            # TODO: Implement actual Piper TTS voice cloning
            model_path = self.models_dir / f"{profile_name}_piper.onnx"

            # Create a dummy model file for now
            model_path.write_text(json.dumps({
                "engine": "piper",
                "profile_name": profile_name,
                "language": language,
                "audio_path": audio_path,
                "created_at": datetime.now().isoformat()
            }))

            return str(model_path)

        except Exception as e:
            self.logger.error(f"Piper model training failed: {e}")
            return None

    def _create_builtin_model(self, audio_path: str, profile_name: str, language: str) -> Optional[str]:
        """Create builtin TTS model profile (fallback)"""

        try:
            model_path = self.models_dir / f"{profile_name}_builtin.json"

            # Create a model configuration for builtin TTS
            model_config = {
                "engine": "builtin",
                "profile_name": profile_name,
                "language": language,
                "audio_path": audio_path,
                "voice_settings": {
                    "speed": 1.0,
                    "pitch": 0.0,
                    "voice_id": "default"
                },
                "created_at": datetime.now().isoformat()
            }

            with open(model_path, 'w') as f:
                json.dump(model_config, f, indent=2)

            return str(model_path)

        except Exception as e:
            self.logger.error(f"Builtin model creation failed: {e}")
            return None

    def generate_speech(self, text: str, voice_profile_name: str, output_path: str) -> bool:
        """Generate speech using specified voice profile"""

        if voice_profile_name not in self.profiles:
            self.logger.error(f"Voice profile not found: {voice_profile_name}")
            return False

        profile = self.profiles[voice_profile_name]

        try:
            # Determine engine from model path
            if "coqui" in profile.model_path:
                return self._generate_coqui_speech(text, profile, output_path)
            elif "piper" in profile.model_path:
                return self._generate_piper_speech(text, profile, output_path)
            else:
                return self._generate_builtin_speech(text, profile, output_path)

        except Exception as e:
            self.logger.error(f"Speech generation failed: {e}")
            return False

    def _generate_coqui_speech(self, text: str, profile: VoiceProfile, output_path: str) -> bool:
        """Generate speech using Coqui TTS"""

        # TODO: Implement actual Coqui TTS speech generation
        # For now, use system TTS as fallback
        return self._generate_builtin_speech(text, profile, output_path)

    def _generate_piper_speech(self, text: str, profile: VoiceProfile, output_path: str) -> bool:
        """Generate speech using Piper TTS"""

        # TODO: Implement actual Piper TTS speech generation
        # For now, use system TTS as fallback
        return self._generate_builtin_speech(text, profile, output_path)

    def _generate_builtin_speech(self, text: str, profile: VoiceProfile, output_path: str) -> bool:
        """Generate speech using system TTS (macOS say command)"""

        try:
            # Use macOS built-in TTS
            cmd = ["say", "-o", output_path.replace('.wav', '.aiff'), text]
            result = subprocess.run(cmd, capture_output=True, text=True)

            if result.returncode != 0:
                self.logger.error(f"System TTS failed: {result.stderr}")
                return False

            # Convert AIFF to WAV
            if output_path.endswith('.wav'):
                aiff_path = output_path.replace('.wav', '.aiff')
                convert_cmd = ["ffmpeg", "-i", aiff_path, "-y", output_path]
                result = subprocess.run(convert_cmd, capture_output=True)

                # Clean up AIFF file
                if Path(aiff_path).exists():
                    os.unlink(aiff_path)

                return result.returncode == 0

            return True

        except Exception as e:
            self.logger.error(f"Builtin speech generation failed: {e}")
            return False

    def list_profiles(self) -> List[Dict[str, Any]]:
        """List all available voice profiles"""

        return [profile.to_dict() for profile in self.profiles.values()]

    def get_profile(self, name: str) -> Optional[VoiceProfile]:
        """Get a specific voice profile"""

        return self.profiles.get(name)

    def delete_profile(self, name: str) -> bool:
        """Delete a voice profile"""

        if name not in self.profiles:
            return False

        try:
            profile = self.profiles[name]

            # Delete model file
            if Path(profile.model_path).exists():
                os.unlink(profile.model_path)

            # Remove from profiles
            del self.profiles[name]
            self._save_profiles()

            jlog(self.logger, logging.INFO, event="voice_profile_deleted", profile_name=name)
            return True

        except Exception as e:
            self.logger.error(f"Error deleting profile {name}: {e}")
            return False