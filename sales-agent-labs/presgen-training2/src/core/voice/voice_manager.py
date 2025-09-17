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
import tempfile
import base64
from pydub import AudioSegment

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

        # TTS engine priority (OpenAI > ElevenLabs > built-in fallback)
        self.tts_engines = {
            "openai": {
                "available": self._check_openai_availability(),
                "priority": 1
            },
            "elevenlabs": {
                "available": self._check_elevenlabs_availability(),
                "priority": 2
            },
            "coqui": {
                "available": False,  # Disabled due to Python 3.13 incompatibility
                "priority": 3
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

    def _check_elevenlabs_availability(self) -> bool:
        """Check if ElevenLabs API is available"""
        try:
            from elevenlabs.client import ElevenLabs
            # Check if API key is available
            return bool(os.getenv("ELEVENLABS_API_KEY"))
        except ImportError:
            return False

    def _check_openai_availability(self) -> bool:
        """Check if OpenAI TTS API is available"""
        try:
            import openai
            # Check if API key is available
            return bool(os.getenv("OPENAI_API_KEY"))
        except ImportError:
            return False

    def _test_openai_quota(self) -> bool:
        """Test if OpenAI API has sufficient quota with comprehensive error handling"""
        try:
            import openai

            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                return False

            client = openai.OpenAI(api_key=api_key)

            # Test with minimal TTS request to check quota
            response = client.audio.speech.create(
                model="tts-1",
                voice="alloy",
                input="Test"  # Minimal 4-character test (~$0.00006)
            )

            # If we got here, quota is available
            self.logger.info("OpenAI API quota check passed")
            return True

        except openai.RateLimitError as e:
            self.logger.error(f"OpenAI rate limit exceeded: {e}")
            return False
        except openai.AuthenticationError as e:
            self.logger.error(f"OpenAI authentication failed: {e}")
            return False
        except Exception as e:
            if "insufficient_quota" in str(e).lower():
                self.logger.error(f"OpenAI quota exhausted: {e}")
                self.logger.error("💡 Please add credits to your OpenAI account - manual recharge required")
                return False
            else:
                self.logger.error(f"OpenAI API test failed: {e}")
                return False

    def _check_coqui_availability(self) -> bool:
        """Check if Coqui TTS is available"""
        # Disabled due to Python 3.13 incompatibility
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
            temp_audio_path = tempfile.mktemp(suffix=".wav")
            if not self._extract_audio_from_video(video_path, temp_audio_path):
                return None

            # Validate audio for cloning
            if not self._validate_audio_for_cloning(temp_audio_path):
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

    def clone_voice_from_audio(self,
                             audio_path: str,
                             profile_name: str,
                             language: str = "auto") -> Optional[VoiceProfile]:
        """
        Clone voice directly from audio file (bypasses video extraction)

        Process:
        1. Validate existing audio file
        2. Detect language if needed
        3. Train voice cloning model
        4. Save profile with metadata

        Args:
            audio_path: Path to existing .wav audio file
            profile_name: Name for the voice profile
            language: Language code or "auto" for detection

        Returns:
            VoiceProfile object with cloning model
        """

        try:
            self.logger.info(f"Starting direct audio voice cloning for profile: {profile_name}")

            # Validate that audio file exists
            if not Path(audio_path).exists():
                self.logger.error(f"Audio file not found: {audio_path}")
                return None

            # Validate audio for cloning
            if not self._validate_audio_for_cloning(audio_path):
                return None

            # Step 1: Language detection
            if language == "auto":
                detected_language = self._detect_language(audio_path)
            else:
                detected_language = language

            # Step 2: Create voice cloning model
            model_path = self._train_voice_model(
                audio_path=audio_path,
                profile_name=profile_name,
                language=detected_language
            )

            if not model_path:
                return None

            # Step 3: Save profile
            profile = VoiceProfile(
                name=profile_name,
                language=detected_language,
                created_at=datetime.now().isoformat(),
                model_path=model_path,
                source_video="direct_audio",  # Mark as direct audio source
                quality="standard"
            )

            self.profiles[profile_name] = profile
            self._save_profiles()

            jlog(self.logger, logging.INFO,
                event="voice_profile_created_from_audio",
                profile_name=profile_name,
                language=detected_language,
                audio_path=audio_path)

            return profile

        except Exception as e:
            self.logger.error(f"Direct audio voice cloning failed: {e}")
            return None

    def _extract_enhanced_audio(self, video_path: str) -> Optional[str]:
        """Extract and enhance audio for voice cloning - permanent storage"""

        try:
            # Create permanent storage directory for enhanced audio
            audio_storage_dir = Path("presgen-training2/temp")
            audio_storage_dir.mkdir(parents=True, exist_ok=True)

            # Generate filename based on source video for potential reuse
            import hashlib
            video_hash = hashlib.md5(video_path.encode()).hexdigest()[:12]
            output_path = audio_storage_dir / f"enhanced_audio_{video_hash}.wav"

            # Check if we already have this audio file (reuse existing)
            if output_path.exists():
                self.logger.info(f"Reusing existing enhanced audio: {output_path}")
                return str(output_path)

            # FFmpeg command for enhanced audio extraction (simplified to avoid empty output)
            enhancement_cmd = [
                "ffmpeg", "-i", video_path,
                "-vn",  # No video
                "-acodec", "pcm_s16le",
                "-ar", "22050",  # Optimal sample rate for voice cloning
                "-ac", "1",  # Mono
                "-af", "volume=1.2",  # Light volume boost only
                "-t", "60",  # Use first 60 seconds for voice sample
                "-y", str(output_path)  # Convert Path object to string
            ]

            result = subprocess.run(enhancement_cmd, capture_output=True, text=True)

            if result.returncode != 0:
                self.logger.error(f"Audio enhancement failed: {result.stderr}")
                return None

            self.logger.info(f"Enhanced audio saved permanently: {output_path}")
            return str(output_path)  # Return string path

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

        if best_engine == "elevenlabs":
            return self._train_elevenlabs_model(audio_path, profile_name, language)
        elif best_engine == "openai":
            return self._train_openai_model(audio_path, profile_name, language)
        elif best_engine == "coqui":
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

    def _train_elevenlabs_model(self, audio_path: str, profile_name: str, language: str) -> Optional[str]:
        """Train voice model using ElevenLabs voice cloning"""

        try:
            from elevenlabs.client import ElevenLabs

            # Initialize ElevenLabs client
            client = ElevenLabs(api_key=os.getenv("ELEVENLABS_API_KEY"))

            # Read audio file
            with open(audio_path, "rb") as audio_file:
                audio_data = audio_file.read()

            # Create voice clone on ElevenLabs
            voice = client.clone(
                name=profile_name,
                description=f"Cloned voice for {profile_name}",
                files=[audio_data]
            )

            # Save voice ID as our model reference
            model_path = self.models_dir / f"{profile_name}_elevenlabs.json"
            model_data = {
                "engine": "elevenlabs",
                "profile_name": profile_name,
                "language": language,
                "voice_id": voice.voice_id,
                "audio_path": audio_path,
                "created_at": datetime.now().isoformat()
            }

            model_path.write_text(json.dumps(model_data, indent=2))

            self.logger.info(f"ElevenLabs voice cloned successfully: {voice.voice_id}")
            return str(model_path)

        except Exception as e:
            self.logger.error(f"ElevenLabs voice cloning failed: {e}")
            return None

    def _train_openai_model(self, audio_path: str, profile_name: str, language: str) -> Optional[str]:
        """Train voice model using OpenAI (Note: OpenAI TTS doesn't support custom voice cloning)"""

        try:
            import openai

            # Test OpenAI API availability with quota monitoring
            if not self._test_openai_quota():
                self.logger.error("OpenAI API quota insufficient - please add credits to your account")
                return None

            # OpenAI TTS doesn't support voice cloning, so we'll create a profile
            # that uses the closest available voice and save the audio sample for reference
            model_path = self.models_dir / f"{profile_name}_openai.json"

            # Analyze audio to suggest closest OpenAI voice
            closest_voice = self._analyze_voice_for_openai_match(audio_path)

            model_data = {
                "engine": "openai",
                "profile_name": profile_name,
                "language": language,
                "voice_name": closest_voice,
                "audio_path": audio_path,
                "created_at": datetime.now().isoformat(),
                "note": "OpenAI TTS doesn't support custom voice cloning - using closest available voice"
            }

            model_path.write_text(json.dumps(model_data, indent=2))

            self.logger.info(f"OpenAI voice profile created with voice: {closest_voice}")
            return str(model_path)

        except Exception as e:
            self.logger.error(f"OpenAI voice profile creation failed: {e}")
            return None

    def _analyze_voice_for_openai_match(self, audio_path: str) -> str:
        """Analyze audio to suggest closest OpenAI voice"""
        # Simple voice matching - could be enhanced with audio analysis
        openai_voices = ["alloy", "echo", "fable", "onyx", "nova", "shimmer"]
        # For now, return a default - could analyze pitch, gender, etc.
        return "alloy"

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
            if "elevenlabs" in profile.model_path:
                return self._generate_elevenlabs_speech(text, profile, output_path)
            elif "openai" in profile.model_path:
                return self._generate_openai_speech(text, profile, output_path)
            elif "coqui" in profile.model_path:
                return self._generate_coqui_speech(text, profile, output_path)
            elif "piper" in profile.model_path:
                return self._generate_piper_speech(text, profile, output_path)
            else:
                return self._generate_builtin_speech(text, profile, output_path)

        except Exception as e:
            self.logger.error(f"Speech generation failed: {e}")
            return False

    def _generate_elevenlabs_speech(self, text: str, profile: VoiceProfile, output_path: str) -> bool:
        """Generate speech using ElevenLabs voice cloning"""

        try:
            from elevenlabs.client import ElevenLabs

            # Load model data to get voice ID
            model_data = json.loads(Path(profile.model_path).read_text())
            voice_id = model_data["voice_id"]

            # Initialize ElevenLabs client
            client = ElevenLabs(api_key=os.getenv("ELEVENLABS_API_KEY"))

            # Generate speech with cloned voice
            audio = client.generate(
                text=text,
                voice=voice_id,
                model="eleven_multilingual_v2"
            )

            # Save audio to file
            with open(output_path, "wb") as f:
                for chunk in audio:
                    f.write(chunk)

            self.logger.info(f"ElevenLabs speech generated successfully: {output_path}")
            return True

        except Exception as e:
            self.logger.error(f"ElevenLabs speech generation failed: {e}")
            return False

    def _generate_openai_speech(self, text: str, profile: VoiceProfile, output_path: str) -> bool:
        """Generate speech using OpenAI TTS"""

        try:
            import openai

            # Load model data to get voice name
            model_data = json.loads(Path(profile.model_path).read_text())
            voice_name = model_data["voice_name"]

            # Initialize OpenAI client
            client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

            # Generate speech
            response = client.audio.speech.create(
                model="tts-1",
                voice=voice_name,
                input=text
            )

            # Save audio to file
            response.stream_to_file(output_path)

            self.logger.info(f"OpenAI speech generated successfully: {output_path}")
            return True

        except Exception as e:
            self.logger.error(f"OpenAI speech generation failed: {e}")
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

    def synthesize_speech(self, text: str, profile_name: str, output_path: str) -> bool:
        """Synthesize speech using a voice profile with quota monitoring"""

        try:
            profile = self.get_profile(profile_name)
            if not profile:
                self.logger.error(f"Voice profile not found: {profile_name}")
                return False

            # Read model configuration
            model_path = Path(profile.model_path)
            if not model_path.exists():
                self.logger.error(f"Model file not found: {profile.model_path}")
                return False

            with open(model_path, 'r') as f:
                model_data = json.load(f)

            engine = model_data.get('engine', 'builtin')

            if engine == "openai":
                return self._synthesize_openai_speech(text, model_data, output_path)
            elif engine == "elevenlabs":
                return self._synthesize_elevenlabs_speech(text, model_data, output_path)
            else:
                return self._synthesize_builtin_speech(text, model_data, output_path)

        except Exception as e:
            self.logger.error(f"Speech synthesis failed: {e}")
            return False

    def _synthesize_openai_speech(self, text: str, model_data: dict, output_path: str) -> bool:
        """Synthesize speech using OpenAI TTS with quota monitoring"""

        try:
            import openai

            # Test quota before synthesis
            if not self._test_openai_quota():
                self.logger.error("OpenAI API quota insufficient for speech synthesis")
                return False

            api_key = os.getenv("OPENAI_API_KEY")
            client = openai.OpenAI(api_key=api_key)

            voice_name = model_data.get('voice_name', 'alloy')

            self.logger.info(f"Synthesizing speech with OpenAI voice: {voice_name}")
            self.logger.info(f"Text length: {len(text)} characters (~${len(text) * 0.000015:.5f})")

            response = client.audio.speech.create(
                model="tts-1",  # Use cheaper model for demo
                voice=voice_name,
                input=text
            )

            # Ensure output directory exists
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)

            # Save audio file
            with open(output_path, "wb") as f:
                f.write(response.content)

            file_size = Path(output_path).stat().st_size
            self.logger.info(f"OpenAI TTS synthesis completed: {output_path} ({file_size} bytes)")

            return True

        except openai.RateLimitError as e:
            self.logger.error(f"OpenAI rate limit exceeded: {e}")
            return False
        except Exception as e:
            if "insufficient_quota" in str(e).lower():
                self.logger.error(f"OpenAI quota exhausted: {e}")
                self.logger.error("💡 Please add credits to your OpenAI account")
            else:
                self.logger.error(f"OpenAI TTS synthesis failed: {e}")
            return False

    def _synthesize_elevenlabs_speech(self, text: str, model_data: dict, output_path: str) -> bool:
        """Synthesize speech using ElevenLabs voice cloning"""

        try:
            from elevenlabs.client import ElevenLabs

            client = ElevenLabs(api_key=os.getenv("ELEVENLABS_API_KEY"))
            voice_id = model_data.get('voice_id')

            if not voice_id:
                self.logger.error("ElevenLabs voice ID not found in profile")
                return False

            audio = client.generate(
                text=text,
                voice=voice_id,
                model="eleven_monolingual_v1"
            )

            # Ensure output directory exists
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)

            with open(output_path, "wb") as f:
                f.write(audio)

            self.logger.info(f"ElevenLabs TTS synthesis completed: {output_path}")
            return True

        except Exception as e:
            self.logger.error(f"ElevenLabs TTS synthesis failed: {e}")
            return False

    def _synthesize_builtin_speech(self, text: str, model_data: dict, output_path: str) -> bool:
        """Synthesize speech using built-in Mac 'say' command"""

        try:
            # Ensure output directory exists
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)

            # Use Mac 'say' command to generate audio
            cmd = ["say", "-o", output_path, text]
            result = subprocess.run(cmd, capture_output=True, text=True)

            if result.returncode == 0:
                self.logger.info(f"Builtin TTS synthesis completed: {output_path}")
                return True
            else:
                self.logger.error(f"Builtin TTS failed: {result.stderr}")
                return False

        except Exception as e:
            self.logger.error(f"Builtin TTS synthesis failed: {e}")
            return False

    def _extract_audio_from_video(self, video_path: str, output_audio_path: str) -> bool:
        """Extract audio from video file for voice cloning"""

        try:
            # Use FFmpeg to extract audio
            cmd = [
                "ffmpeg", "-i", video_path,
                "-vn",  # No video
                "-acodec", "pcm_s16le",  # Uncompressed audio
                "-ar", "22050",  # Sample rate
                "-ac", "1",  # Mono
                "-y",  # Overwrite output
                output_audio_path
            ]

            result = subprocess.run(cmd, capture_output=True, text=True)

            if result.returncode != 0:
                self.logger.error(f"Audio extraction failed: {result.stderr}")
                return False

            self.logger.info(f"Audio extracted successfully: {output_audio_path}")
            return True

        except Exception as e:
            self.logger.error(f"Audio extraction error: {e}")
            return False

    def _validate_audio_for_cloning(self, audio_path: str) -> bool:
        """Validate audio file for voice cloning requirements"""

        try:
            # Load audio with pydub
            audio = AudioSegment.from_file(audio_path)

            # Check duration (need at least 10 seconds for good cloning)
            duration_seconds = len(audio) / 1000.0
            if duration_seconds < 10:
                self.logger.warning(f"Audio too short for cloning: {duration_seconds}s (minimum 10s)")
                return False

            # Check if too long (some services have limits)
            if duration_seconds > 300:  # 5 minutes
                self.logger.warning(f"Audio too long: {duration_seconds}s (maximum 300s)")
                return False

            self.logger.info(f"Audio validation passed: {duration_seconds}s")
            return True

        except Exception as e:
            self.logger.error(f"Audio validation failed: {e}")
            return False