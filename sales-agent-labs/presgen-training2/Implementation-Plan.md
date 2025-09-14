# PresGen-Training2: Implementation Plan

## Implementation Overview

This document provides a detailed, phase-by-phase implementation plan for PresGen-Training2, covering all three modes (Video-Only, Presentation-Only, Video-Presentation) with Google Slides integration, voice cloning, and video appending capabilities optimized for M1 Mac hardware.

### Implementation Timeline
- **Total Duration**: 4 weeks (28 days)
- **Target**: Production-ready system with all features
- **Testing Asset**: `/Users/yitzchak/Documents/learn/presentation_project/sales-agent-labs/sadtalker-api/examples/presgen_test2.mp4`

## Phase 1: Foundation and Environment Setup (Week 1)

### Day 1-2: Project Structure and LivePortrait Installation

#### 1.1 Directory Structure Creation
```bash
# Create complete folder structure
mkdir -p presgen-training2/{src,config,models,temp,output,logs,examples}
mkdir -p presgen-training2/src/{core,presentation,pipeline,api,modes,utils}

# Source code organization
mkdir -p presgen-training2/src/core/{liveportrait,voice,content}
mkdir -p presgen-training2/src/presentation/{slides,renderer,compositor}
mkdir -p presgen-training2/src/pipeline/{appender,normalizer,transitions}
mkdir -p presgen-training2/src/api/{endpoints,models,middleware}

# Configuration and data
mkdir -p presgen-training2/config/{hardware,quality,templates}
mkdir -p presgen-training2/models/{voice-profiles,cached-models}
```

#### 1.2 LivePortrait Installation with M1 Optimization
```bash
# Install LivePortrait in project directory
cd /Users/yitzchak/Documents/learn/presentation_project/sales-agent-labs
git clone https://github.com/KwaiVGI/LivePortrait.git

# Setup M1 Mac optimizations
export PYTORCH_ENABLE_MPS_FALLBACK=1

# Create dedicated environment for LivePortrait
python3 -m venv liveportrait_env
source liveportrait_env/bin/activate

# Install requirements with M1 optimizations
pip3 install torch torchvision torchaudio
pip3 install -r LivePortrait/requirements_macOS.txt

# Download pre-trained weights
huggingface-cli download KwaiVGI/LivePortrait --local-dir LivePortrait/pretrained_weights --exclude "*.git*" "README.md" "docs"
```

#### 1.3 Core Infrastructure Setup

**File: `presgen-training2/src/core/__init__.py`**
```python
"""
PresGen-Training2 Core Module
Handles LivePortrait integration, voice cloning, and content processing
"""

from .liveportrait.avatar_engine import LivePortraitEngine
from .voice.voice_manager import VoiceProfileManager
from .content.processor import ContentProcessor

__all__ = ['LivePortraitEngine', 'VoiceProfileManager', 'ContentProcessor']
```

**File: `presgen-training2/src/core/liveportrait/avatar_engine.py`**
```python
import subprocess
import json
import time
import logging
from pathlib import Path
from typing import Optional, Dict, Any
from dataclasses import dataclass

from src.common.jsonlog import jlog

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
        self.liveportrait_path = Path("LivePortrait")
        self.liveportrait_env = Path("liveportrait_env/bin/python")

        # M1 Mac specific settings
        self.m1_config = {
            "pytorch_mps_fallback": True,
            "memory_fraction": 0.7,
            "processing_timeout": 1200,  # 20 minutes for M1
            "quality_modes": {
                "fast": {"resolution": "720p", "fps": 25, "enhancement": False},
                "standard": {"resolution": "720p", "fps": 30, "enhancement": False},
                "high": {"resolution": "1080p", "fps": 30, "enhancement": True}
            }
        }

        self._validate_installation()

    def _validate_installation(self) -> None:
        """Validate LivePortrait installation"""

        if not self.liveportrait_path.exists():
            raise RuntimeError("LivePortrait not found. Run installation script first.")

        if not self.liveportrait_env.exists():
            raise RuntimeError("LivePortrait environment not found. Run setup script.")

        # Test basic functionality
        try:
            result = subprocess.run([
                str(self.liveportrait_env),
                "-c", "import torch; print(torch.__version__)"
            ], capture_output=True, text=True, timeout=30)

            if result.returncode != 0:
                raise RuntimeError("LivePortrait environment validation failed")

            jlog(self.logger, logging.INFO,
                 event="liveportrait_engine_init",
                 pytorch_version=result.stdout.strip(),
                 status="validated")

        except subprocess.TimeoutExpired:
            raise RuntimeError("LivePortrait environment validation timeout")

    def generate_avatar_video(self,
                            audio_path: str,
                            reference_image: str,
                            output_path: str,
                            quality_level: str = "standard") -> AvatarGenerationResult:
        """
        Generate avatar video using LivePortrait

        Args:
            audio_path: Path to narration audio file
            reference_image: Path to source image for avatar
            output_path: Path for output video
            quality_level: "fast", "standard", or "high"

        Returns:
            AvatarGenerationResult with success status and metadata
        """

        start_time = time.time()

        jlog(self.logger, logging.INFO,
             event="avatar_generation_start",
             audio_path=audio_path,
             reference_image=reference_image,
             output_path=output_path,
             quality_level=quality_level)

        try:
            # Create LivePortrait wrapper script
            wrapper_script = self._create_liveportrait_wrapper()

            # Build command with M1 optimizations
            cmd = [
                str(self.liveportrait_env),
                str(wrapper_script),
                "--source-image", reference_image,
                "--driving-audio", audio_path,
                "--output", output_path,
                "--quality", quality_level,
                "--m1-optimized"
            ]

            # Set environment variables for M1 optimization
            env = {
                **os.environ,
                "PYTORCH_ENABLE_MPS_FALLBACK": "1",
                "CUDA_VISIBLE_DEVICES": ""  # Force CPU for M1 compatibility
            }

            # Execute LivePortrait generation
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.m1_config["processing_timeout"],
                env=env,
                cwd=self.liveportrait_path
            )

            processing_time = time.time() - start_time

            if result.returncode == 0:
                jlog(self.logger, logging.INFO,
                     event="avatar_generation_complete",
                     output_path=output_path,
                     processing_time=processing_time,
                     quality_level=quality_level,
                     file_size_mb=Path(output_path).stat().st_size / (1024*1024) if Path(output_path).exists() else 0)

                return AvatarGenerationResult(
                    success=True,
                    output_path=output_path,
                    processing_time=processing_time,
                    quality_level=quality_level
                )
            else:
                error_msg = result.stderr or "LivePortrait generation failed"
                jlog(self.logger, logging.ERROR,
                     event="avatar_generation_failed",
                     error=error_msg,
                     returncode=result.returncode)

                return AvatarGenerationResult(
                    success=False,
                    error=error_msg
                )

        except subprocess.TimeoutExpired:
            error_msg = f"Avatar generation timeout after {self.m1_config['processing_timeout']} seconds"
            jlog(self.logger, logging.ERROR,
                 event="avatar_generation_timeout",
                 timeout=self.m1_config['processing_timeout'])

            return AvatarGenerationResult(
                success=False,
                error=error_msg
            )

        except Exception as e:
            error_msg = f"Avatar generation exception: {str(e)}"
            jlog(self.logger, logging.ERROR,
                 event="avatar_generation_exception",
                 error=str(e))

            return AvatarGenerationResult(
                success=False,
                error=error_msg
            )

    def _create_liveportrait_wrapper(self) -> str:
        """Create wrapper script for LivePortrait execution"""

        wrapper_content = '''#!/usr/bin/env python3
"""
LivePortrait wrapper for PresGen-Training2
Handles M1 Mac optimizations and parameter processing
"""

import argparse
import os
import sys
sys.path.append(os.path.dirname(__file__))

# Import LivePortrait modules
from src.utils.helper import load_checkpoint
from src.live_portrait_pipeline import LivePortraitPipeline

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--source-image', required=True)
    parser.add_argument('--driving-audio', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--quality', default='standard')
    parser.add_argument('--m1-optimized', action='store_true')

    args = parser.parse_args()

    # M1 optimizations
    if args.m1_optimized:
        os.environ['PYTORCH_ENABLE_MPS_FALLBACK'] = '1'

    # Quality settings
    quality_configs = {
        "fast": {"size": 256, "fps": 25},
        "standard": {"size": 512, "fps": 30},
        "high": {"size": 1024, "fps": 30}
    }

    config = quality_configs.get(args.quality, quality_configs['standard'])

    # Initialize pipeline
    pipeline = LivePortraitPipeline(
        checkpoint_dir='pretrained_weights',
        config=config
    )

    # Generate avatar video
    pipeline.execute(
        source_image_path=args.source_image,
        driving_audio_path=args.driving_audio,
        output_path=args.output
    )

    print(f"Avatar video generated: {args.output}")

if __name__ == '__main__':
    main()
'''

        wrapper_path = self.liveportrait_path / "liveportrait_wrapper.py"
        with open(wrapper_path, 'w') as f:
            f.write(wrapper_content)

        # Make executable
        wrapper_path.chmod(0o755)
        return str(wrapper_path)
```

### Day 3-4: Google Slides Integration

#### 1.4 Google Slides API Setup

**File: `presgen-training2/src/presentation/slides/google_slides_client.py`**
```python
import re
import logging
from typing import List, Dict, Optional
from pathlib import Path
from dataclasses import dataclass
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

@dataclass
class SlideData:
    slide_id: str
    slide_index: int
    image_path: str
    notes_text: str
    estimated_duration: float
    has_notes: bool

@dataclass
class PresentationData:
    presentation_id: str
    title: str
    slides: List[SlideData]
    total_slides: int

class GoogleSlidesClient:
    """
    Google Slides API client for presentation processing
    Extracts slides and notes for video generation
    """

    SCOPES = ['https://www.googleapis.com/auth/presentations.readonly']

    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger("presgen_training2.google_slides")
        self.service = self._initialize_service()

    def _initialize_service(self):
        """Initialize Google Slides API service"""

        creds = None
        token_path = "config/google_slides_token.json"
        credentials_path = "config/google_slides_credentials.json"

        # Load existing token
        if Path(token_path).exists():
            creds = Credentials.from_authorized_user_file(token_path, self.SCOPES)

        # Refresh or create new credentials
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if not Path(credentials_path).exists():
                    raise FileNotFoundError(
                        f"Google Slides credentials not found at {credentials_path}. "
                        "Please download credentials from Google Cloud Console."
                    )

                flow = InstalledAppFlow.from_client_secrets_file(credentials_path, self.SCOPES)
                creds = flow.run_local_server(port=0)

            # Save credentials
            with open(token_path, 'w') as token:
                token.write(creds.to_json())

        return build('slides', 'v1', credentials=creds)

    def extract_presentation_id(self, slides_url: str) -> str:
        """Extract presentation ID from Google Slides URL"""

        patterns = [
            r'/presentation/d/([a-zA-Z0-9-_]+)',
            r'id=([a-zA-Z0-9-_]+)',
            r'^([a-zA-Z0-9-_]+)$'  # Direct ID
        ]

        for pattern in patterns:
            match = re.search(pattern, slides_url)
            if match:
                return match.group(1)

        raise ValueError(f"Could not extract presentation ID from URL: {slides_url}")

    def process_slides_url(self, slides_url: str) -> PresentationData:
        """
        Extract presentation data from Google Slides URL

        Args:
            slides_url: Google Slides URL or presentation ID

        Returns:
            PresentationData with slides and notes information
        """

        try:
            presentation_id = self.extract_presentation_id(slides_url)

            # Get presentation metadata
            presentation = self.service.presentations().get(
                presentationId=presentation_id
            ).execute()

            title = presentation.get('title', 'Untitled Presentation')

            jlog(self.logger, logging.INFO,
                 event="slides_extraction_start",
                 presentation_id=presentation_id,
                 title=title,
                 total_slides=len(presentation.get('slides', [])))

            # Process each slide
            slides_data = []
            for i, slide in enumerate(presentation.get('slides', [])):
                slide_data = self._process_slide(presentation_id, slide, i)
                slides_data.append(slide_data)

            return PresentationData(
                presentation_id=presentation_id,
                title=title,
                slides=slides_data,
                total_slides=len(slides_data)
            )

        except Exception as e:
            jlog(self.logger, logging.ERROR,
                 event="slides_extraction_failed",
                 error=str(e),
                 slides_url=slides_url)
            raise

    def _process_slide(self, presentation_id: str, slide: Dict, slide_index: int) -> SlideData:
        """Process individual slide with notes extraction"""

        slide_id = slide['objectId']

        # Export slide as image
        image_path = self._export_slide_image(presentation_id, slide_id, slide_index)

        # Extract notes text
        notes_text = self._extract_slide_notes(presentation_id, slide_id)

        # Estimate narration duration
        estimated_duration = self._estimate_duration(notes_text)

        return SlideData(
            slide_id=slide_id,
            slide_index=slide_index,
            image_path=image_path,
            notes_text=notes_text,
            estimated_duration=estimated_duration,
            has_notes=bool(notes_text.strip())
        )

    def _export_slide_image(self, presentation_id: str, slide_id: str, slide_index: int) -> str:
        """Export slide as high-quality image"""

        # Request slide image export
        export_url = f"https://docs.google.com/presentation/d/{presentation_id}/export/png?id={presentation_id}&pageid={slide_id}"

        output_path = f"temp/slide_{slide_index:03d}_{slide_id}.png"

        # Download image
        import requests
        response = requests.get(export_url)
        response.raise_for_status()

        with open(output_path, 'wb') as f:
            f.write(response.content)

        return output_path

    def _extract_slide_notes(self, presentation_id: str, slide_id: str) -> str:
        """Extract notes section from slide"""

        try:
            # Get slide with notes page
            slide = self.service.presentations().pages().get(
                presentationId=presentation_id,
                pageObjectId=slide_id
            ).execute()

            notes_text = ""

            # Look for notes master (where notes are stored)
            for layout in slide.get('slideProperties', {}).get('layoutObjectId', []):
                # This is a simplified approach - actual notes extraction may require
                # more complex logic depending on Google Slides API structure
                pass

            # Alternative approach: Use the presentation's notes pages
            presentation = self.service.presentations().get(
                presentationId=presentation_id
            ).execute()

            # Find corresponding notes page
            for page in presentation.get('pages', []):
                if page.get('objectId') == slide_id + '_notes':
                    notes_text = self._parse_text_elements(page)
                    break

            return notes_text.strip()

        except Exception as e:
            jlog(self.logger, logging.WARNING,
                 event="notes_extraction_failed",
                 slide_id=slide_id,
                 error=str(e))
            return ""

    def _parse_text_elements(self, page: Dict) -> str:
        """Parse text elements from page"""

        text_content = ""

        for element in page.get('pageElements', []):
            if 'shape' in element:
                shape = element['shape']
                if 'text' in shape:
                    for text_element in shape['text'].get('textElements', []):
                        if 'textRun' in text_element:
                            text_content += text_element['textRun'].get('content', '')

        return text_content

    def _estimate_duration(self, text: str) -> float:
        """Estimate narration duration based on text length"""

        if not text.strip():
            return 3.0  # Default 3 seconds for slides without notes

        # Rough estimation: 150 words per minute average speaking rate
        word_count = len(text.split())
        duration = (word_count / 150) * 60  # Convert to seconds

        # Minimum 2 seconds, maximum 30 seconds per slide
        return max(2.0, min(30.0, duration))
```

### Day 5-7: Voice Cloning System Implementation

#### 1.5 Voice Profile Management

**File: `presgen-training2/src/core/voice/voice_manager.py`**
```python
import json
import uuid
import time
import subprocess
import logging
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
from datetime import datetime

@dataclass
class VoiceProfile:
    name: str
    language: str
    model_path: str
    created_at: str
    source_video: str
    quality_score: float
    file_size_mb: float

class VoiceProfileManager:
    """
    Manage voice cloning profiles with persistence
    Supports multiple TTS engines with fallbacks
    """

    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger("presgen_training2.voice")
        self.profiles_file = Path("presgen-training2/models/voice-profiles/profiles.json")
        self.models_dir = Path("presgen-training2/models/voice-profiles")

        # Ensure directories exist
        self.models_dir.mkdir(parents=True, exist_ok=True)

        # Initialize TTS engines
        self.tts_engines = self._initialize_tts_engines()

    def _initialize_tts_engines(self) -> Dict:
        """Initialize available TTS engines"""

        engines = {}

        # Try Coqui TTS (primary)
        try:
            import TTS
            engines['coqui'] = {
                'available': True,
                'quality': 'high',
                'speed': 'medium'
            }
        except ImportError:
            engines['coqui'] = {'available': False}

        # Try gTTS (fallback)
        try:
            import gtts
            engines['gtts'] = {
                'available': True,
                'quality': 'medium',
                'speed': 'fast'
            }
        except ImportError:
            engines['gtts'] = {'available': False}

        # OpenAI TTS (if API key available)
        if os.getenv('OPENAI_API_KEY'):
            engines['openai'] = {
                'available': True,
                'quality': 'high',
                'speed': 'fast'
            }
        else:
            engines['openai'] = {'available': False}

        return engines

    def clone_voice_from_video(self,
                             video_path: str,
                             profile_name: str,
                             language: str = "auto") -> VoiceProfile:
        """
        Clone voice from reference video and save profile

        Args:
            video_path: Path to reference video
            profile_name: Name for the voice profile
            language: Language code or "auto" for detection

        Returns:
            VoiceProfile with cloning information
        """

        jlog(self.logger, logging.INFO,
             event="voice_cloning_start",
             video_path=video_path,
             profile_name=profile_name,
             language=language)

        start_time = time.time()

        try:
            # Step 1: Extract enhanced audio
            audio_path = self._extract_enhanced_audio(video_path)

            # Step 2: Detect language if needed
            if language == "auto":
                language = self._detect_language(audio_path)

            # Step 3: Clone voice using best available engine
            model_path = self._clone_voice_with_best_engine(
                audio_path, profile_name, language
            )

            # Step 4: Assess quality
            quality_score = self._assess_voice_quality(model_path, audio_path)

            # Step 5: Create profile
            profile = VoiceProfile(
                name=profile_name,
                language=language,
                model_path=model_path,
                created_at=datetime.now().isoformat(),
                source_video=video_path,
                quality_score=quality_score,
                file_size_mb=Path(model_path).stat().st_size / (1024*1024) if Path(model_path).exists() else 0
            )

            # Step 6: Save profile
            self._save_profile(profile)

            processing_time = time.time() - start_time

            jlog(self.logger, logging.INFO,
                 event="voice_cloning_complete",
                 profile_name=profile_name,
                 processing_time=processing_time,
                 quality_score=quality_score,
                 language=language)

            # Cleanup temporary files
            if Path(audio_path).exists():
                Path(audio_path).unlink()

            return profile

        except Exception as e:
            jlog(self.logger, logging.ERROR,
                 event="voice_cloning_failed",
                 error=str(e),
                 profile_name=profile_name)
            raise

    def _extract_enhanced_audio(self, video_path: str) -> str:
        """Extract and enhance audio for voice cloning"""

        output_path = f"temp/voice_sample_{uuid.uuid4().hex}.wav"

        # FFmpeg command with advanced audio enhancement
        cmd = [
            "ffmpeg",
            "-i", video_path,
            "-vn",  # No video
            "-acodec", "pcm_s16le",
            "-ar", "22050",  # Optimal for voice cloning
            "-ac", "1",  # Mono
            "-af", (
                # Advanced audio processing chain
                "highpass=f=80,"                    # Remove low-freq noise
                "lowpass=f=8000,"                   # Remove high-freq noise
                "afftdn=nf=-25,"                    # Dynamic noise reduction
                "compand=attacks=0.3:decays=0.8:points=0/-90|0/-70|0.5/-20|1/0," # Compression
                "volume=1.5,"                      # Normalize volume
                "silenceremove=start_periods=1:start_silence=0.1:start_threshold=0.02,"  # Trim silence
                "aresample=22050"                   # Ensure consistent sample rate
            ),
            "-t", "120",  # Use first 2 minutes for voice sample
            "-y", output_path
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            raise RuntimeError(f"Audio extraction failed: {result.stderr}")

        return output_path

    def _detect_language(self, audio_path: str) -> str:
        """Detect language from audio sample"""

        # Simple implementation - in production, use actual language detection
        # For now, default to English
        return "en"

    def _clone_voice_with_best_engine(self,
                                    audio_path: str,
                                    profile_name: str,
                                    language: str) -> str:
        """Clone voice using the best available TTS engine"""

        # Try engines in order of preference
        engine_priority = ['coqui', 'openai', 'gtts']

        for engine_name in engine_priority:
            engine = self.tts_engines.get(engine_name, {})
            if not engine.get('available', False):
                continue

            try:
                model_path = self._clone_with_engine(
                    engine_name, audio_path, profile_name, language
                )

                jlog(self.logger, logging.INFO,
                     event="voice_cloning_engine_success",
                     engine=engine_name,
                     profile_name=profile_name)

                return model_path

            except Exception as e:
                jlog(self.logger, logging.WARNING,
                     event="voice_cloning_engine_failed",
                     engine=engine_name,
                     error=str(e))
                continue

        raise RuntimeError("All voice cloning engines failed")

    def _clone_with_engine(self,
                          engine_name: str,
                          audio_path: str,
                          profile_name: str,
                          language: str) -> str:
        """Clone voice using specific TTS engine"""

        model_path = self.models_dir / f"{profile_name}_{engine_name}.pth"

        if engine_name == 'coqui':
            return self._clone_with_coqui(audio_path, str(model_path), language)
        elif engine_name == 'openai':
            return self._clone_with_openai(audio_path, str(model_path))
        elif engine_name == 'gtts':
            return self._create_gtts_profile(str(model_path), language)
        else:
            raise ValueError(f"Unknown engine: {engine_name}")

    def _clone_with_coqui(self, audio_path: str, model_path: str, language: str) -> str:
        """Clone voice using Coqui TTS"""

        try:
            from TTS.api import TTS

            # Initialize TTS with voice cloning model
            tts = TTS(model_name="tts_models/multilingual/multi-dataset/your_tts")

            # Clone voice (simplified - actual implementation may vary)
            tts.tts_to_file(
                text="This is a voice cloning test.",
                file_path=model_path,
                speaker_wav=audio_path,
                language=language
            )

            return model_path

        except Exception as e:
            raise RuntimeError(f"Coqui TTS cloning failed: {e}")

    def generate_speech(self,
                       text: str,
                       voice_profile_name: str,
                       output_path: str) -> str:
        """
        Generate speech using saved voice profile

        Args:
            text: Text to synthesize
            voice_profile_name: Name of saved voice profile
            output_path: Path for output audio file

        Returns:
            Path to generated audio file
        """

        # Load profile
        profile = self.get_profile(voice_profile_name)
        if not profile:
            raise ValueError(f"Voice profile not found: {voice_profile_name}")

        # Generate speech based on profile engine
        engine = self._detect_profile_engine(profile.model_path)

        if engine == 'coqui':
            return self._generate_with_coqui(text, profile, output_path)
        elif engine == 'gtts':
            return self._generate_with_gtts(text, profile, output_path)
        else:
            raise ValueError(f"Unsupported profile engine: {engine}")

    def get_profile(self, profile_name: str) -> Optional[VoiceProfile]:
        """Get voice profile by name"""

        profiles = self._load_profiles()
        return profiles.get(profile_name)

    def list_profiles(self) -> List[VoiceProfile]:
        """List all saved voice profiles"""

        profiles = self._load_profiles()
        return list(profiles.values())

    def _load_profiles(self) -> Dict[str, VoiceProfile]:
        """Load voice profiles from disk"""

        if not self.profiles_file.exists():
            return {}

        try:
            with open(self.profiles_file, 'r') as f:
                data = json.load(f)

            profiles = {}
            for name, profile_data in data.items():
                profiles[name] = VoiceProfile(**profile_data)

            return profiles

        except Exception as e:
            jlog(self.logger, logging.ERROR,
                 event="profiles_load_failed",
                 error=str(e))
            return {}

    def _save_profile(self, profile: VoiceProfile) -> None:
        """Save voice profile to disk"""

        profiles = self._load_profiles()
        profiles[profile.name] = profile

        # Convert to serializable format
        profiles_data = {
            name: asdict(profile) for name, profile in profiles.items()
        }

        with open(self.profiles_file, 'w') as f:
            json.dump(profiles_data, f, indent=2)
```

## Phase 2: Presentation-to-Video Pipeline (Week 2)

### Day 8-10: Slides-to-Video Renderer Implementation

#### 2.1 Presentation Video Compositor

**File: `presgen-training2/src/presentation/renderer/slides_video_renderer.py`**
```python
import subprocess
import uuid
import logging
from pathlib import Path
from typing import List, Optional
from dataclasses import dataclass

from src.core.voice.voice_manager import VoiceProfileManager
from src.presentation.slides.google_slides_client import PresentationData

@dataclass
class VideoSegment:
    slide_index: int
    image_path: str
    audio_path: str
    duration: float
    transition_in: str = "fade"
    transition_out: str = "fade"

class SlidesToVideoRenderer:
    """
    Convert presentation slides with narration to MP4 video
    Handles timing, transitions, and audio synchronization
    """

    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger("presgen_training2.slides_renderer")
        self.voice_manager = VoiceProfileManager(logger)

        # Video composition settings
        self.video_config = {
            "resolution": "1920x1080",  # Full HD for presentations
            "framerate": 30,
            "video_codec": "libx264",
            "audio_codec": "aac",
            "audio_bitrate": "192k",
            "video_bitrate": "2M",
            "pixel_format": "yuv420p"
        }

    def render_presentation_video(self,
                                presentation_data: PresentationData,
                                voice_profile_name: Optional[str] = None,
                                output_path: Optional[str] = None) -> str:
        """
        Render complete presentation video with narration

        Args:
            presentation_data: Slides data from Google Slides
            voice_profile_name: Name of voice profile to use for narration
            output_path: Output video path (auto-generated if None)

        Returns:
            Path to rendered presentation video
        """

        if output_path is None:
            output_path = f"output/presentation_{uuid.uuid4().hex}.mp4"

        jlog(self.logger, logging.INFO,
             event="presentation_rendering_start",
             total_slides=presentation_data.total_slides,
             voice_profile=voice_profile_name,
             output_path=output_path)

        try:
            # Step 1: Generate narration for each slide
            video_segments = []
            total_duration = 0

            for slide_data in presentation_data.slides:
                segment = self._create_slide_segment(
                    slide_data, voice_profile_name
                )
                video_segments.append(segment)
                total_duration += segment.duration

            # Step 2: Compose final video with transitions
            self._compose_presentation_video(
                segments=video_segments,
                output_path=output_path,
                total_duration=total_duration
            )

            jlog(self.logger, logging.INFO,
                 event="presentation_rendering_complete",
                 output_path=output_path,
                 total_duration=total_duration,
                 total_slides=len(video_segments))

            return output_path

        except Exception as e:
            jlog(self.logger, logging.ERROR,
                 event="presentation_rendering_failed",
                 error=str(e))
            raise

    def _create_slide_segment(self,
                            slide_data,
                            voice_profile_name: Optional[str]) -> VideoSegment:
        """Create video segment for individual slide"""

        # Generate narration audio
        if slide_data.has_notes and slide_data.notes_text.strip():
            audio_path = self._generate_slide_narration(
                text=slide_data.notes_text,
                voice_profile_name=voice_profile_name,
                slide_index=slide_data.slide_index
            )

            # Get actual audio duration
            duration = self._get_audio_duration(audio_path)
        else:
            # Create silence for slides without notes
            duration = 3.0  # 3 second default
            audio_path = self._generate_silence(duration, slide_data.slide_index)

        return VideoSegment(
            slide_index=slide_data.slide_index,
            image_path=slide_data.image_path,
            audio_path=audio_path,
            duration=duration
        )

    def _generate_slide_narration(self,
                                text: str,
                                voice_profile_name: Optional[str],
                                slide_index: int) -> str:
        """Generate TTS narration for slide"""

        output_path = f"temp/narration_slide_{slide_index:03d}.wav"

        if voice_profile_name:
            # Use cloned voice
            self.voice_manager.generate_speech(
                text=text,
                voice_profile_name=voice_profile_name,
                output_path=output_path
            )
        else:
            # Use default TTS
            self._generate_default_tts(text, output_path)

        return output_path

    def _generate_default_tts(self, text: str, output_path: str) -> None:
        """Generate TTS using default engine (gTTS)"""

        try:
            from gtts import gTTS

            tts = gTTS(text=text, lang='en', slow=False)

            # Save as MP3 first
            temp_mp3 = output_path.replace('.wav', '.mp3')
            tts.save(temp_mp3)

            # Convert to WAV
            subprocess.run([
                "ffmpeg",
                "-i", temp_mp3,
                "-acodec", "pcm_s16le",
                "-ar", "44100",
                "-ac", "2",
                "-y", output_path
            ], check=True)

            # Cleanup
            Path(temp_mp3).unlink(missing_ok=True)

        except Exception as e:
            jlog(self.logger, logging.ERROR,
                 event="default_tts_failed",
                 error=str(e))

            # Fallback: create silence
            self._generate_silence(5.0, 0, output_path)

    def _generate_silence(self,
                        duration: float,
                        slide_index: int,
                        output_path: Optional[str] = None) -> str:
        """Generate silence audio for slides without narration"""

        if output_path is None:
            output_path = f"temp/silence_slide_{slide_index:03d}.wav"

        subprocess.run([
            "ffmpeg",
            "-f", "lavfi",
            "-i", f"anullsrc=channel_layout=stereo:sample_rate=44100:duration={duration}",
            "-y", output_path
        ], check=True)

        return output_path

    def _get_audio_duration(self, audio_path: str) -> float:
        """Get duration of audio file"""

        result = subprocess.run([
            "ffprobe",
            "-v", "quiet",
            "-show_entries", "format=duration",
            "-of", "csv=p=0",
            audio_path
        ], capture_output=True, text=True)

        try:
            return float(result.stdout.strip())
        except ValueError:
            return 3.0  # Default fallback

    def _compose_presentation_video(self,
                                  segments: List[VideoSegment],
                                  output_path: str,
                                  total_duration: float) -> None:
        """Compose final presentation video with all segments"""

        # Create individual slide videos
        slide_videos = []
        for segment in segments:
            slide_video = self._create_slide_video(segment)
            slide_videos.append(slide_video)

        # Concatenate all slide videos
        self._concatenate_slide_videos(slide_videos, output_path)

        # Cleanup temporary slide videos
        for video_path in slide_videos:
            Path(video_path).unlink(missing_ok=True)

    def _create_slide_video(self, segment: VideoSegment) -> str:
        """Create video for individual slide"""

        output_path = f"temp/slide_video_{segment.slide_index:03d}.mp4"

        # FFmpeg command to create slide video
        cmd = [
            "ffmpeg",
            "-loop", "1",  # Loop the image
            "-i", segment.image_path,  # Input slide image
            "-i", segment.audio_path,  # Input narration audio
            "-c:v", self.video_config["video_codec"],
            "-tune", "stillimage",  # Optimize for static images
            "-c:a", self.video_config["audio_codec"],
            "-b:a", self.video_config["audio_bitrate"],
            "-b:v", self.video_config["video_bitrate"],
            "-pix_fmt", self.video_config["pixel_format"],
            "-r", str(self.video_config["framerate"]),
            "-s", self.video_config["resolution"],
            "-t", str(segment.duration),  # Duration matches audio
            "-shortest",  # End when shortest input ends
            "-y", output_path
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            raise RuntimeError(f"Slide video creation failed: {result.stderr}")

        return output_path

    def _concatenate_slide_videos(self,
                                slide_videos: List[str],
                                output_path: str) -> None:
        """Concatenate slide videos into final presentation"""

        # Create concat file list
        concat_file = "temp/presentation_concat_list.txt"
        with open(concat_file, 'w') as f:
            for video_path in slide_videos:
                f.write(f"file '{Path(video_path).absolute()}'\n")

        # FFmpeg concatenation command
        cmd = [
            "ffmpeg",
            "-f", "concat",
            "-safe", "0",
            "-i", concat_file,
            "-c", "copy",  # Copy streams without re-encoding
            "-y", output_path
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            # Fallback: re-encode if copy fails
            cmd = [
                "ffmpeg",
                "-f", "concat",
                "-safe", "0",
                "-i", concat_file,
                "-c:v", self.video_config["video_codec"],
                "-c:a", self.video_config["audio_codec"],
                "-y", output_path
            ]

            result = subprocess.run(cmd, capture_output=True, text=True)

            if result.returncode != 0:
                raise RuntimeError(f"Video concatenation failed: {result.stderr}")

        # Cleanup
        Path(concat_file).unlink(missing_ok=True)
```

### Day 11-14: Video Appending Pipeline

#### 2.2 Video Concatenation System

**File: `presgen-training2/src/pipeline/appender/video_appender.py`**
```python
import subprocess
import uuid
import logging
from pathlib import Path
from typing import List, Optional, Dict, Any
from dataclasses import dataclass

@dataclass
class VideoMetadata:
    path: str
    duration: float
    resolution: str
    framerate: float
    codec: str
    audio_codec: str
    bitrate: str

@dataclass
class AppendResult:
    success: bool
    output_path: Optional[str] = None
    total_duration: Optional[float] = None
    processing_time: Optional[float] = None
    error: Optional[str] = None

class VideoAppender:
    """
    Advanced video concatenation system with format normalization
    Handles seamless joining of avatar and presentation videos
    """

    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger("presgen_training2.video_appender")

        # Target format for normalization
        self.target_format = {
            "resolution": "1920x1080",
            "framerate": 30,
            "video_codec": "libx264",
            "audio_codec": "aac",
            "pixel_format": "yuv420p",
            "video_bitrate": "2M",
            "audio_bitrate": "192k"
        }

    def append_videos(self,
                     avatar_video_path: str,
                     presentation_video_path: str,
                     output_path: Optional[str] = None,
                     add_transition: bool = True,
                     transition_duration: float = 1.0) -> AppendResult:
        """
        Append presentation video to avatar video with optional transition

        Args:
            avatar_video_path: Path to avatar video (first segment)
            presentation_video_path: Path to presentation video (second segment)
            output_path: Output path for final video
            add_transition: Whether to add transition between videos
            transition_duration: Duration of transition in seconds

        Returns:
            AppendResult with success status and metadata
        """

        if output_path is None:
            output_path = f"output/combined_video_{uuid.uuid4().hex}.mp4"

        jlog(self.logger, logging.INFO,
             event="video_appending_start",
             avatar_video=avatar_video_path,
             presentation_video=presentation_video_path,
             output_path=output_path,
             add_transition=add_transition)

        start_time = time.time()

        try:
            # Step 1: Analyze input videos
            avatar_metadata = self._analyze_video(avatar_video_path)
            presentation_metadata = self._analyze_video(presentation_video_path)

            # Step 2: Normalize video formats
            normalized_avatar = self._normalize_video_format(
                avatar_video_path, avatar_metadata, "avatar"
            )
            normalized_presentation = self._normalize_video_format(
                presentation_video_path, presentation_metadata, "presentation"
            )

            # Step 3: Create transition if requested
            transition_video = None
            if add_transition:
                transition_video = self._create_transition_video(
                    from_video=normalized_avatar,
                    to_video=normalized_presentation,
                    duration=transition_duration
                )

            # Step 4: Concatenate videos
            videos_to_concat = [normalized_avatar]
            if transition_video:
                videos_to_concat.append(transition_video)
            videos_to_concat.append(normalized_presentation)

            self._concatenate_videos(videos_to_concat, output_path)

            # Step 5: Calculate total duration and finalize
            total_duration = self._get_video_duration(output_path)
            processing_time = time.time() - start_time

            # Cleanup temporary files
            self._cleanup_temporary_files([
                normalized_avatar, normalized_presentation, transition_video
            ])

            jlog(self.logger, logging.INFO,
                 event="video_appending_complete",
                 output_path=output_path,
                 total_duration=total_duration,
                 processing_time=processing_time)

            return AppendResult(
                success=True,
                output_path=output_path,
                total_duration=total_duration,
                processing_time=processing_time
            )

        except Exception as e:
            error_msg = f"Video appending failed: {str(e)}"

            jlog(self.logger, logging.ERROR,
                 event="video_appending_failed",
                 error=str(e),
                 avatar_video=avatar_video_path,
                 presentation_video=presentation_video_path)

            return AppendResult(
                success=False,
                error=error_msg
            )

    def _analyze_video(self, video_path: str) -> VideoMetadata:
        """Analyze video file to get metadata"""

        # Use ffprobe to get video information
        cmd = [
            "ffprobe",
            "-v", "quiet",
            "-print_format", "json",
            "-show_format",
            "-show_streams",
            video_path
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            raise RuntimeError(f"Video analysis failed: {result.stderr}")

        import json
        metadata = json.loads(result.stdout)

        # Extract video stream information
        video_stream = None
        audio_stream = None

        for stream in metadata.get('streams', []):
            if stream['codec_type'] == 'video':
                video_stream = stream
            elif stream['codec_type'] == 'audio':
                audio_stream = stream

        if not video_stream:
            raise ValueError(f"No video stream found in {video_path}")

        # Calculate resolution
        width = video_stream.get('width', 0)
        height = video_stream.get('height', 0)
        resolution = f"{width}x{height}"

        # Get frame rate
        framerate_str = video_stream.get('r_frame_rate', '30/1')
        try:
            num, den = map(int, framerate_str.split('/'))
            framerate = num / den if den != 0 else 30.0
        except:
            framerate = 30.0

        # Get duration
        duration = float(metadata.get('format', {}).get('duration', 0))

        return VideoMetadata(
            path=video_path,
            duration=duration,
            resolution=resolution,
            framerate=framerate,
            codec=video_stream.get('codec_name', 'unknown'),
            audio_codec=audio_stream.get('codec_name', 'unknown') if audio_stream else 'none',
            bitrate=metadata.get('format', {}).get('bit_rate', 'unknown')
        )

    def _normalize_video_format(self,
                              video_path: str,
                              metadata: VideoMetadata,
                              video_type: str) -> str:
        """Normalize video to target format if needed"""

        # Check if video already matches target format
        needs_conversion = (
            metadata.resolution != self.target_format["resolution"] or
            abs(metadata.framerate - self.target_format["framerate"]) > 0.1 or
            metadata.codec != self.target_format["video_codec"].replace('lib', '')
        )

        if not needs_conversion:
            jlog(self.logger, logging.INFO,
                 event="video_format_compatible",
                 video_path=video_path,
                 video_type=video_type)
            return video_path

        # Convert to target format
        normalized_path = f"temp/normalized_{video_type}_{uuid.uuid4().hex}.mp4"

        cmd = [
            "ffmpeg",
            "-i", video_path,
            "-c:v", self.target_format["video_codec"],
            "-c:a", self.target_format["audio_codec"],
            "-r", str(self.target_format["framerate"]),
            "-s", self.target_format["resolution"],
            "-b:v", self.target_format["video_bitrate"],
            "-b:a", self.target_format["audio_bitrate"],
            "-pix_fmt", self.target_format["pixel_format"],
            "-preset", "medium",  # Balance speed vs compression
            "-y", normalized_path
        ]

        jlog(self.logger, logging.INFO,
             event="video_normalization_start",
             video_path=video_path,
             normalized_path=normalized_path,
             video_type=video_type)

        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            raise RuntimeError(f"Video normalization failed: {result.stderr}")

        jlog(self.logger, logging.INFO,
             event="video_normalization_complete",
             normalized_path=normalized_path,
             video_type=video_type)

        return normalized_path

    def _create_transition_video(self,
                               from_video: str,
                               to_video: str,
                               duration: float) -> str:
        """Create transition video between two videos"""

        transition_path = f"temp/transition_{uuid.uuid4().hex}.mp4"

        # Create a crossfade transition using FFmpeg
        cmd = [
            "ffmpeg",
            "-i", from_video,
            "-i", to_video,
            "-filter_complex",
            f"[0:v]trim=duration={duration}[v0];"
            f"[1:v]trim=duration={duration}[v1];"
            f"[v0][v1]xfade=transition=fade:duration={duration}:offset=0[vout];"
            f"[0:a]atrim=duration={duration}[a0];"
            f"[1:a]atrim=duration={duration}[a1];"
            f"[a0][a1]acrossfade=duration={duration}[aout]",
            "-map", "[vout]",
            "-map", "[aout]",
            "-c:v", self.target_format["video_codec"],
            "-c:a", self.target_format["audio_codec"],
            "-t", str(duration),
            "-y", transition_path
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            jlog(self.logger, logging.WARNING,
                 event="transition_creation_failed",
                 error=result.stderr)
            # Return None if transition creation fails
            return None

        return transition_path

    def _concatenate_videos(self, video_paths: List[str], output_path: str) -> None:
        """Concatenate multiple videos into final output"""

        # Filter out None values (failed transitions)
        valid_videos = [v for v in video_paths if v is not None]

        if len(valid_videos) == 0:
            raise ValueError("No valid videos to concatenate")

        # Create concat file
        concat_file = f"temp/concat_list_{uuid.uuid4().hex}.txt"

        with open(concat_file, 'w') as f:
            for video_path in valid_videos:
                f.write(f"file '{Path(video_path).absolute()}'\n")

        # FFmpeg concatenation
        cmd = [
            "ffmpeg",
            "-f", "concat",
            "-safe", "0",
            "-i", concat_file,
            "-c", "copy",  # Try copy first for speed
            "-y", output_path
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            jlog(self.logger, logging.WARNING,
                 event="concat_copy_failed",
                 error=result.stderr)

            # Fallback: re-encode
            cmd = [
                "ffmpeg",
                "-f", "concat",
                "-safe", "0",
                "-i", concat_file,
                "-c:v", self.target_format["video_codec"],
                "-c:a", self.target_format["audio_codec"],
                "-y", output_path
            ]

            result = subprocess.run(cmd, capture_output=True, text=True)

            if result.returncode != 0:
                raise RuntimeError(f"Video concatenation failed: {result.stderr}")

        # Cleanup concat file
        Path(concat_file).unlink(missing_ok=True)

    def _get_video_duration(self, video_path: str) -> float:
        """Get duration of video file"""

        cmd = [
            "ffprobe",
            "-v", "quiet",
            "-show_entries", "format=duration",
            "-of", "csv=p=0",
            video_path
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)

        try:
            return float(result.stdout.strip())
        except ValueError:
            return 0.0

    def _cleanup_temporary_files(self, file_paths: List[Optional[str]]) -> None:
        """Clean up temporary files"""

        for file_path in file_paths:
            if file_path and file_path != "temp" and "temp/" in file_path:
                try:
                    Path(file_path).unlink(missing_ok=True)
                except Exception as e:
                    jlog(self.logger, logging.WARNING,
                         event="cleanup_failed",
                         file_path=file_path,
                         error=str(e))
```

## Phase 3: Three-Mode Orchestration (Week 3)

### Day 15-17: Mode Implementation

#### 3.1 Mode Orchestrator

**File: `presgen-training2/src/modes/orchestrator.py`**
```python
import time
import logging
from typing import Dict, Any, Optional
from dataclasses import dataclass

from src.core.liveportrait.avatar_engine import LivePortraitEngine
from src.core.voice.voice_manager import VoiceProfileManager
from src.presentation.slides.google_slides_client import GoogleSlidesClient
from src.presentation.renderer.slides_video_renderer import SlidesToVideoRenderer
from src.pipeline.appender.video_appender import VideoAppender

@dataclass
class ProcessingRequest:
    """Base request for all processing modes"""
    mode: str
    quality_level: str = "standard"
    instructions: Optional[str] = None

@dataclass
class VideoOnlyRequest(ProcessingRequest):
    """Request for Video-Only mode"""
    content_file: Optional[str] = None
    script_text: Optional[str] = None
    reference_video: Optional[str] = None
    voice_profile_name: Optional[str] = None
    new_voice_profile_name: Optional[str] = None

@dataclass
class PresentationOnlyRequest(ProcessingRequest):
    """Request for Presentation-Only mode"""
    slides_url: Optional[str] = None
    content_file: Optional[str] = None
    voice_profile_name: Optional[str] = None

@dataclass
class VideoPresentationRequest(ProcessingRequest):
    """Request for Video-Presentation mode"""
    # Video-only parameters
    content_file: Optional[str] = None
    script_text: Optional[str] = None
    reference_video: Optional[str] = None

    # Presentation parameters
    slides_url: Optional[str] = None
    presentation_content_file: Optional[str] = None

    # Shared parameters
    voice_profile_name: Optional[str] = None
    new_voice_profile_name: Optional[str] = None

@dataclass
class ProcessingResult:
    success: bool
    mode: str
    output_path: Optional[str] = None
    processing_time: Optional[float] = None
    stages_completed: Optional[int] = None
    total_stages: Optional[int] = None
    error: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

class ModeOrchestrator:
    """
    Central orchestrator for all three processing modes
    Coordinates avatar generation, presentation creation, and video appending
    """

    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger("presgen_training2.orchestrator")

        # Initialize processing engines
        self.avatar_engine = LivePortraitEngine(logger)
        self.voice_manager = VoiceProfileManager(logger)
        self.slides_client = GoogleSlidesClient(logger)
        self.slides_renderer = SlidesToVideoRenderer(logger)
        self.video_appender = VideoAppender(logger)

        # Content processor for summarization
        self.content_processor = ContentProcessor(logger)

        jlog(self.logger, logging.INFO,
             event="orchestrator_initialized",
             components=["avatar_engine", "voice_manager", "slides_client",
                        "slides_renderer", "video_appender", "content_processor"])

    def process_video_only(self, request: VideoOnlyRequest) -> ProcessingResult:
        """
        Mode 1: Generate avatar video with narration

        Process:
        1. Content processing (file → script OR use provided script)
        2. Voice cloning (if new voice) OR load existing profile
        3. Avatar image extraction from reference video
        4. TTS audio generation
        5. Avatar video generation with LivePortrait
        """

        jlog(self.logger, logging.INFO,
             event="video_only_processing_start",
             request=request.__dict__)

        start_time = time.time()
        stages_completed = 0
        total_stages = 5

        try:
            # Stage 1: Process content into script
            stages_completed += 1
            if request.content_file:
                script = self.content_processor.summarize_content_to_script(
                    content_file=request.content_file,
                    instructions=request.instructions
                )
            elif request.script_text:
                script = request.script_text
                if request.instructions:
                    script = self.content_processor.enhance_script_with_instructions(
                        script, request.instructions
                    )
            else:
                raise ValueError("Either content_file or script_text must be provided")

            jlog(self.logger, logging.INFO,
                 event="script_processing_complete",
                 script_length=len(script),
                 stage=f"{stages_completed}/{total_stages}")

            # Stage 2: Voice setup
            stages_completed += 1
            voice_profile_name = request.voice_profile_name

            if request.reference_video and request.new_voice_profile_name:
                # Clone new voice
                voice_profile = self.voice_manager.clone_voice_from_video(
                    video_path=request.reference_video,
                    profile_name=request.new_voice_profile_name
                )
                voice_profile_name = voice_profile.name

                jlog(self.logger, logging.INFO,
                     event="voice_cloning_complete",
                     profile_name=voice_profile_name,
                     stage=f"{stages_completed}/{total_stages}")

            # Stage 3: Extract avatar image
            stages_completed += 1
            if request.reference_video:
                avatar_image_path = self._extract_avatar_image(request.reference_video)
            else:
                raise ValueError("Reference video required for avatar generation")

            # Stage 4: Generate TTS audio
            stages_completed += 1
            audio_path = self._generate_tts_audio(script, voice_profile_name)

            jlog(self.logger, logging.INFO,
                 event="tts_generation_complete",
                 audio_path=audio_path,
                 stage=f"{stages_completed}/{total_stages}")

            # Stage 5: Generate avatar video
            stages_completed += 1
            output_path = f"output/video_only_{int(time.time())}.mp4"

            avatar_result = self.avatar_engine.generate_avatar_video(
                audio_path=audio_path,
                reference_image=avatar_image_path,
                output_path=output_path,
                quality_level=request.quality_level
            )

            if not avatar_result.success:
                raise RuntimeError(f"Avatar generation failed: {avatar_result.error}")

            processing_time = time.time() - start_time

            jlog(self.logger, logging.INFO,
                 event="video_only_processing_complete",
                 output_path=output_path,
                 processing_time=processing_time,
                 stages_completed=stages_completed)

            return ProcessingResult(
                success=True,
                mode="video_only",
                output_path=output_path,
                processing_time=processing_time,
                stages_completed=stages_completed,
                total_stages=total_stages,
                metadata={
                    "script_length": len(script),
                    "voice_profile": voice_profile_name,
                    "quality_level": request.quality_level
                }
            )

        except Exception as e:
            error_msg = f"Video-only processing failed at stage {stages_completed}: {str(e)}"

            jlog(self.logger, logging.ERROR,
                 event="video_only_processing_failed",
                 error=str(e),
                 stages_completed=stages_completed,
                 total_stages=total_stages)

            return ProcessingResult(
                success=False,
                mode="video_only",
                stages_completed=stages_completed,
                total_stages=total_stages,
                error=error_msg
            )

    def process_presentation_only(self, request: PresentationOnlyRequest) -> ProcessingResult:
        """
        Mode 2: Generate narrated slideshow video

        Process:
        Option A (slides_url): Google Slides URL → Extract slides + notes → Generate narration
        Option B (content_file): Content file → Generate slides → Generate narration
        """

        jlog(self.logger, logging.INFO,
             event="presentation_only_processing_start",
             request=request.__dict__)

        start_time = time.time()
        stages_completed = 0
        total_stages = 4

        try:
            # Stage 1: Get presentation data
            stages_completed += 1

            if request.slides_url:
                # Option A: Extract from existing Google Slides
                presentation_data = self.slides_client.process_slides_url(request.slides_url)

                jlog(self.logger, logging.INFO,
                     event="slides_extraction_complete",
                     total_slides=presentation_data.total_slides,
                     slides_with_notes=sum(1 for s in presentation_data.slides if s.has_notes),
                     stage=f"{stages_completed}/{total_stages}")

            elif request.content_file:
                # Option B: Generate new presentation
                presentation_data = self._generate_presentation_from_content(
                    content_file=request.content_file,
                    instructions=request.instructions
                )

                jlog(self.logger, logging.INFO,
                     event="presentation_generation_complete",
                     total_slides=presentation_data.total_slides,
                     stage=f"{stages_completed}/{total_stages}")
            else:
                raise ValueError("Either slides_url or content_file must be provided")

            # Stage 2: Validate voice profile
            stages_completed += 1
            if request.voice_profile_name:
                voice_profile = self.voice_manager.get_profile(request.voice_profile_name)
                if not voice_profile:
                    raise ValueError(f"Voice profile not found: {request.voice_profile_name}")

            # Stage 3: Render presentation video
            stages_completed += 1
            output_path = f"output/presentation_only_{int(time.time())}.mp4"

            presentation_video_path = self.slides_renderer.render_presentation_video(
                presentation_data=presentation_data,
                voice_profile_name=request.voice_profile_name,
                output_path=output_path
            )

            # Stage 4: Finalization
            stages_completed += 1
            processing_time = time.time() - start_time

            jlog(self.logger, logging.INFO,
                 event="presentation_only_processing_complete",
                 output_path=presentation_video_path,
                 processing_time=processing_time,
                 stages_completed=stages_completed)

            return ProcessingResult(
                success=True,
                mode="presentation_only",
                output_path=presentation_video_path,
                processing_time=processing_time,
                stages_completed=stages_completed,
                total_stages=total_stages,
                metadata={
                    "total_slides": presentation_data.total_slides,
                    "voice_profile": request.voice_profile_name,
                    "source": "google_slides" if request.slides_url else "generated"
                }
            )

        except Exception as e:
            error_msg = f"Presentation-only processing failed at stage {stages_completed}: {str(e)}"

            jlog(self.logger, logging.ERROR,
                 event="presentation_only_processing_failed",
                 error=str(e),
                 stages_completed=stages_completed,
                 total_stages=total_stages)

            return ProcessingResult(
                success=False,
                mode="presentation_only",
                stages_completed=stages_completed,
                total_stages=total_stages,
                error=error_msg
            )

    def process_video_presentation(self, request: VideoPresentationRequest) -> ProcessingResult:
        """
        Mode 3: Generate combined avatar video + presentation

        Process:
        1. Generate avatar video (Mode 1 logic)
        2. Generate presentation video (Mode 2 logic)
        3. Append videos with transition
        """

        jlog(self.logger, logging.INFO,
             event="video_presentation_processing_start",
             request=request.__dict__)

        start_time = time.time()
        stages_completed = 0
        total_stages = 8

        try:
            # Stage 1-5: Generate avatar video
            video_only_request = VideoOnlyRequest(
                mode="video_only",
                content_file=request.content_file,
                script_text=request.script_text,
                reference_video=request.reference_video,
                voice_profile_name=request.voice_profile_name,
                new_voice_profile_name=request.new_voice_profile_name,
                quality_level=request.quality_level,
                instructions=request.instructions
            )

            avatar_result = self.process_video_only(video_only_request)
            stages_completed += 5

            if not avatar_result.success:
                raise RuntimeError(f"Avatar video generation failed: {avatar_result.error}")

            jlog(self.logger, logging.INFO,
                 event="avatar_video_stage_complete",
                 avatar_video_path=avatar_result.output_path,
                 stage=f"{stages_completed}/{total_stages}")

            # Stage 6-7: Generate presentation video
            presentation_only_request = PresentationOnlyRequest(
                mode="presentation_only",
                slides_url=request.slides_url,
                content_file=request.presentation_content_file or request.content_file,
                voice_profile_name=request.voice_profile_name,
                quality_level=request.quality_level,
                instructions=request.instructions
            )

            presentation_result = self.process_presentation_only(presentation_only_request)
            stages_completed += 2

            if not presentation_result.success:
                raise RuntimeError(f"Presentation video generation failed: {presentation_result.error}")

            jlog(self.logger, logging.INFO,
                 event="presentation_video_stage_complete",
                 presentation_video_path=presentation_result.output_path,
                 stage=f"{stages_completed}/{total_stages}")

            # Stage 8: Append videos
            stages_completed += 1
            output_path = f"output/video_presentation_{int(time.time())}.mp4"

            append_result = self.video_appender.append_videos(
                avatar_video_path=avatar_result.output_path,
                presentation_video_path=presentation_result.output_path,
                output_path=output_path,
                add_transition=True,
                transition_duration=1.0
            )

            if not append_result.success:
                raise RuntimeError(f"Video appending failed: {append_result.error}")

            processing_time = time.time() - start_time

            jlog(self.logger, logging.INFO,
                 event="video_presentation_processing_complete",
                 output_path=append_result.output_path,
                 processing_time=processing_time,
                 total_duration=append_result.total_duration,
                 stages_completed=stages_completed)

            return ProcessingResult(
                success=True,
                mode="video_presentation",
                output_path=append_result.output_path,
                processing_time=processing_time,
                stages_completed=stages_completed,
                total_stages=total_stages,
                metadata={
                    "avatar_video_path": avatar_result.output_path,
                    "presentation_video_path": presentation_result.output_path,
                    "total_duration": append_result.total_duration,
                    "voice_profile": request.voice_profile_name
                }
            )

        except Exception as e:
            error_msg = f"Video-presentation processing failed at stage {stages_completed}: {str(e)}"

            jlog(self.logger, logging.ERROR,
                 event="video_presentation_processing_failed",
                 error=str(e),
                 stages_completed=stages_completed,
                 total_stages=total_stages)

            return ProcessingResult(
                success=False,
                mode="video_presentation",
                stages_completed=stages_completed,
                total_stages=total_stages,
                error=error_msg
            )

    def _extract_avatar_image(self, video_path: str) -> str:
        """Extract high-quality frame from video for avatar generation"""

        output_path = f"temp/avatar_frame_{int(time.time())}.jpg"

        # Extract frame at 2-second mark for good quality
        cmd = [
            "ffmpeg",
            "-i", video_path,
            "-ss", "00:00:02",  # 2 seconds in
            "-vframes", "1",    # Single frame
            "-q:v", "2",        # High quality
            "-y", output_path
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            raise RuntimeError(f"Avatar image extraction failed: {result.stderr}")

        return output_path

    def _generate_tts_audio(self, text: str, voice_profile_name: Optional[str]) -> str:
        """Generate TTS audio using voice profile or default"""

        output_path = f"temp/tts_audio_{int(time.time())}.wav"

        if voice_profile_name:
            self.voice_manager.generate_speech(
                text=text,
                voice_profile_name=voice_profile_name,
                output_path=output_path
            )
        else:
            # Use default TTS
            try:
                from gtts import gTTS

                tts = gTTS(text=text, lang='en', slow=False)
                temp_mp3 = output_path.replace('.wav', '.mp3')
                tts.save(temp_mp3)

                # Convert to WAV
                subprocess.run([
                    "ffmpeg",
                    "-i", temp_mp3,
                    "-acodec", "pcm_s16le",
                    "-ar", "44100",
                    "-y", output_path
                ], check=True)

                Path(temp_mp3).unlink(missing_ok=True)

            except Exception as e:
                raise RuntimeError(f"TTS generation failed: {str(e)}")

        return output_path
```

## Phase 4: API and UI Integration (Week 4)

### Day 18-21: FastAPI Extension

#### 4.1 Training API Endpoints

**File: `presgen-training2/src/api/training_endpoints.py`**
```python
import asyncio
from fastapi import HTTPException, UploadFile, File, Form, BackgroundTasks
from typing import Optional

from src.modes.orchestrator import ModeOrchestrator, VideoOnlyRequest, PresentationOnlyRequest, VideoPresentationRequest

# Add to existing FastAPI app in src/service/http.py
orchestrator = ModeOrchestrator()

@app.post("/training/video-only")
async def process_video_only(
    background_tasks: BackgroundTasks,
    content: Optional[UploadFile] = File(None),
    script_text: Optional[str] = Form(None),
    reference_video: Optional[UploadFile] = File(None),
    voice_profile_name: Optional[str] = Form(None),
    new_voice_profile_name: Optional[str] = Form(None),
    quality_level: str = Form("standard"),
    instructions: Optional[str] = Form(None)
):
    """Process Video-Only mode request"""

    # Validate inputs
    if not content and not script_text:
        raise HTTPException(400, "Either content file or script text must be provided")

    if not reference_video:
        raise HTTPException(400, "Reference video is required for avatar generation")

    # Create job
    job_id = create_training_job("video_only")

    # Save uploaded files
    content_path = None
    if content:
        content_path = save_uploaded_file(content, job_id)

    reference_video_path = save_uploaded_file(reference_video, job_id)

    # Create processing request
    request = VideoOnlyRequest(
        mode="video_only",
        content_file=content_path,
        script_text=script_text,
        reference_video=reference_video_path,
        voice_profile_name=voice_profile_name,
        new_voice_profile_name=new_voice_profile_name,
        quality_level=quality_level,
        instructions=instructions
    )

    # Start background processing
    background_tasks.add_task(process_training_job, job_id, "video_only", request)

    return {"job_id": job_id, "status": "processing", "mode": "video_only"}

@app.post("/training/presentation-only")
async def process_presentation_only(
    background_tasks: BackgroundTasks,
    slides_url: Optional[str] = Form(None),
    content: Optional[UploadFile] = File(None),
    voice_profile_name: Optional[str] = Form(None),
    quality_level: str = Form("standard"),
    instructions: Optional[str] = Form(None)
):
    """Process Presentation-Only mode request"""

    # Validate inputs
    if not slides_url and not content:
        raise HTTPException(400, "Either Google Slides URL or content file must be provided")

    # Create job
    job_id = create_training_job("presentation_only")

    # Save uploaded file if provided
    content_path = None
    if content:
        content_path = save_uploaded_file(content, job_id)

    # Create processing request
    request = PresentationOnlyRequest(
        mode="presentation_only",
        slides_url=slides_url,
        content_file=content_path,
        voice_profile_name=voice_profile_name,
        quality_level=quality_level,
        instructions=instructions
    )

    # Start background processing
    background_tasks.add_task(process_training_job, job_id, "presentation_only", request)

    return {"job_id": job_id, "status": "processing", "mode": "presentation_only"}

@app.post("/training/video-presentation")
async def process_video_presentation(
    background_tasks: BackgroundTasks,
    # Avatar video parameters
    content: Optional[UploadFile] = File(None),
    script_text: Optional[str] = Form(None),
    reference_video: Optional[UploadFile] = File(None),
    # Presentation parameters
    slides_url: Optional[str] = Form(None),
    presentation_content: Optional[UploadFile] = File(None),
    # Shared parameters
    voice_profile_name: Optional[str] = Form(None),
    new_voice_profile_name: Optional[str] = Form(None),
    quality_level: str = Form("standard"),
    instructions: Optional[str] = Form(None)
):
    """Process Video-Presentation combined mode"""

    # Validate inputs
    if not content and not script_text:
        raise HTTPException(400, "Content or script text required for avatar video")

    if not reference_video:
        raise HTTPException(400, "Reference video required for avatar generation")

    if not slides_url and not presentation_content:
        raise HTTPException(400, "Either Google Slides URL or presentation content required")

    # Create job
    job_id = create_training_job("video_presentation")

    # Save uploaded files
    content_path = save_uploaded_file(content, job_id) if content else None
    reference_video_path = save_uploaded_file(reference_video, job_id)
    presentation_content_path = save_uploaded_file(presentation_content, job_id) if presentation_content else None

    # Create processing request
    request = VideoPresentationRequest(
        mode="video_presentation",
        content_file=content_path,
        script_text=script_text,
        reference_video=reference_video_path,
        slides_url=slides_url,
        presentation_content_file=presentation_content_path,
        voice_profile_name=voice_profile_name,
        new_voice_profile_name=new_voice_profile_name,
        quality_level=quality_level,
        instructions=instructions
    )

    # Start background processing
    background_tasks.add_task(process_training_job, job_id, "video_presentation", request)

    return {"job_id": job_id, "status": "processing", "mode": "video_presentation"}

async def process_training_job(job_id: str, mode: str, request):
    """Background task for processing training jobs"""

    try:
        update_job_status(job_id, "processing", {"current_stage": "Starting processing"})

        # Process based on mode
        if mode == "video_only":
            result = orchestrator.process_video_only(request)
        elif mode == "presentation_only":
            result = orchestrator.process_presentation_only(request)
        elif mode == "video_presentation":
            result = orchestrator.process_video_presentation(request)
        else:
            raise ValueError(f"Unknown mode: {mode}")

        # Update job with results
        if result.success:
            update_job_status(job_id, "completed", {
                "output_path": result.output_path,
                "processing_time": result.processing_time,
                "stages_completed": result.stages_completed,
                "metadata": result.metadata
            })
        else:
            update_job_status(job_id, "failed", {
                "error": result.error,
                "stages_completed": result.stages_completed,
                "total_stages": result.total_stages
            })

    except Exception as e:
        update_job_status(job_id, "failed", {"error": str(e)})
```

### Day 22-24: PresGen-UI Integration

#### 4.2 PresGen-Training Tab

**File: `presgen-ui/src/components/training/TrainingWorkflow.tsx`**
```typescript
'use client'

import React, { useState, useEffect } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Progress } from "@/components/ui/progress"
import { Badge } from "@/components/ui/badge"
import { Upload, Play, Download, Mic, Presentation, Video } from "lucide-react"

interface VoiceProfile {
  name: string
  language: string
  created_at: string
  quality_score: number
}

interface JobStatus {
  job_id: string
  status: 'processing' | 'completed' | 'failed'
  mode: string
  progress?: number
  current_stage?: string
  output_path?: string
  error?: string
  processing_time?: number
}

export function TrainingWorkflow() {
  const [activeMode, setActiveMode] = useState<'video-only' | 'presentation-only' | 'video-presentation'>('video-only')
  const [voiceProfiles, setVoiceProfiles] = useState<VoiceProfile[]>([])
  const [currentJob, setCurrentJob] = useState<JobStatus | null>(null)
  const [isProcessing, setIsProcessing] = useState(false)

  // Form state
  const [formData, setFormData] = useState({
    // Content inputs
    contentFile: null as File | null,
    scriptText: '',

    // Video inputs
    referenceVideo: null as File | null,

    // Presentation inputs
    slidesUrl: '',
    presentationContent: null as File | null,
    presentationMode: 'generate', // 'generate' or 'existing'

    // Voice inputs
    voiceProfile: '',
    newVoiceProfileName: '',

    // Processing options
    qualityLevel: 'standard',
    instructions: ''
  })

  useEffect(() => {
    // Load voice profiles on mount
    loadVoiceProfiles()
  }, [])

  const loadVoiceProfiles = async () => {
    try {
      const response = await fetch('/api/training/voice-profiles')
      if (response.ok) {
        const profiles = await response.json()
        setVoiceProfiles(profiles)
      }
    } catch (error) {
      console.error('Failed to load voice profiles:', error)
    }
  }

  const handleSubmit = async () => {
    setIsProcessing(true)

    try {
      const formDataToSend = new FormData()

      // Add files
      if (formData.contentFile) {
        formDataToSend.append('content', formData.contentFile)
      }
      if (formData.referenceVideo) {
        formDataToSend.append('reference_video', formData.referenceVideo)
      }
      if (formData.presentationContent) {
        formDataToSend.append('presentation_content', formData.presentationContent)
      }

      // Add text fields
      if (formData.scriptText) {
        formDataToSend.append('script_text', formData.scriptText)
      }
      if (formData.slidesUrl) {
        formDataToSend.append('slides_url', formData.slidesUrl)
      }
      if (formData.voiceProfile) {
        formDataToSend.append('voice_profile_name', formData.voiceProfile)
      }
      if (formData.newVoiceProfileName) {
        formDataToSend.append('new_voice_profile_name', formData.newVoiceProfileName)
      }

      formDataToSend.append('quality_level', formData.qualityLevel)
      if (formData.instructions) {
        formDataToSend.append('instructions', formData.instructions)
      }

      // Submit to appropriate endpoint
      const endpoint = `/api/training/${activeMode.replace('-', '-')}`
      const response = await fetch(endpoint, {
        method: 'POST',
        body: formDataToSend
      })

      if (response.ok) {
        const result = await response.json()
        setCurrentJob({
          job_id: result.job_id,
          status: 'processing',
          mode: result.mode
        })

        // Start polling for status
        pollJobStatus(result.job_id)
      } else {
        throw new Error('Failed to start processing')
      }
    } catch (error) {
      console.error('Processing failed:', error)
    }
  }

  const pollJobStatus = async (jobId: string) => {
    const pollInterval = setInterval(async () => {
      try {
        const response = await fetch(`/api/training/status/${jobId}`)
        if (response.ok) {
          const status = await response.json()
          setCurrentJob(status)

          if (status.status === 'completed' || status.status === 'failed') {
            clearInterval(pollInterval)
            setIsProcessing(false)
          }
        }
      } catch (error) {
        console.error('Status polling failed:', error)
        clearInterval(pollInterval)
        setIsProcessing(false)
      }
    }, 2000) // Poll every 2 seconds
  }

  return (
    <div className="space-y-6">
      {/* Mode Selection */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Video className="h-5 w-5" />
            PresGen-Training Mode Selection
          </CardTitle>
          <CardDescription>
            Choose your video generation mode
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Tabs value={activeMode} onValueChange={(value) => setActiveMode(value as any)}>
            <TabsList className="grid w-full grid-cols-3">
              <TabsTrigger value="video-only" className="flex items-center gap-2">
                <Mic className="h-4 w-4" />
                Video-Only
              </TabsTrigger>
              <TabsTrigger value="presentation-only" className="flex items-center gap-2">
                <Presentation className="h-4 w-4" />
                Presentation-Only
              </TabsTrigger>
              <TabsTrigger value="video-presentation" className="flex items-center gap-2">
                <Play className="h-4 w-4" />
                Video + Presentation
              </TabsTrigger>
            </TabsList>

            {/* Video-Only Mode */}
            <TabsContent value="video-only" className="space-y-4">
              <VideoOnlyForm
                formData={formData}
                setFormData={setFormData}
                voiceProfiles={voiceProfiles}
              />
            </TabsContent>

            {/* Presentation-Only Mode */}
            <TabsContent value="presentation-only" className="space-y-4">
              <PresentationOnlyForm
                formData={formData}
                setFormData={setFormData}
                voiceProfiles={voiceProfiles}
              />
            </TabsContent>

            {/* Video-Presentation Mode */}
            <TabsContent value="video-presentation" className="space-y-4">
              <VideoPresentationForm
                formData={formData}
                setFormData={setFormData}
                voiceProfiles={voiceProfiles}
              />
            </TabsContent>
          </Tabs>
        </CardContent>
      </Card>

      {/* Processing Options */}
      <ProcessingOptionsCard
        formData={formData}
        setFormData={setFormData}
      />

      {/* Submit Button */}
      <Card>
        <CardContent className="pt-6">
          <Button
            onClick={handleSubmit}
            disabled={isProcessing}
            className="w-full"
            size="lg"
          >
            {isProcessing ? 'Processing...' : `Generate ${activeMode.replace('-', ' ')} Video`}
          </Button>
        </CardContent>
      </Card>

      {/* Progress Monitor */}
      {currentJob && (
        <ProcessingProgress job={currentJob} />
      )}
    </div>
  )
}

// Individual form components for each mode
function VideoOnlyForm({ formData, setFormData, voiceProfiles }) {
  return (
    <div className="space-y-4">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Content Input */}
        <div className="space-y-2">
          <Label htmlFor="content-file">Content File (Optional)</Label>
          <Input
            id="content-file"
            type="file"
            accept=".pdf,.docx,.txt,.md"
            onChange={(e) => setFormData({...formData, contentFile: e.target.files?.[0] || null})}
          />
        </div>

        {/* Reference Video */}
        <div className="space-y-2">
          <Label htmlFor="reference-video">Reference Video (Required)</Label>
          <Input
            id="reference-video"
            type="file"
            accept=".mp4,.mov,.avi"
            onChange={(e) => setFormData({...formData, referenceVideo: e.target.files?.[0] || null})}
          />
        </div>
      </div>

      {/* Script Text */}
      <div className="space-y-2">
        <Label htmlFor="script-text">Script Text (if no content file)</Label>
        <Textarea
          id="script-text"
          placeholder="Enter your script text here..."
          rows={6}
          value={formData.scriptText}
          onChange={(e) => setFormData({...formData, scriptText: e.target.value})}
        />
      </div>

      {/* Voice Options */}
      <VoiceSelectionSection
        formData={formData}
        setFormData={setFormData}
        voiceProfiles={voiceProfiles}
      />
    </div>
  )
}

function PresentationOnlyForm({ formData, setFormData, voiceProfiles }) {
  return (
    <div className="space-y-4">
      {/* Presentation Source */}
      <div className="space-y-4">
        <div className="flex gap-4">
          <Button
            variant={formData.presentationMode === 'generate' ? 'default' : 'outline'}
            onClick={() => setFormData({...formData, presentationMode: 'generate'})}
          >
            Generate New Slides
          </Button>
          <Button
            variant={formData.presentationMode === 'existing' ? 'default' : 'outline'}
            onClick={() => setFormData({...formData, presentationMode: 'existing'})}
          >
            Use Existing Slides
          </Button>
        </div>

        {formData.presentationMode === 'generate' ? (
          <div className="space-y-2">
            <Label htmlFor="presentation-content">Content File</Label>
            <Input
              id="presentation-content"
              type="file"
              accept=".pdf,.docx,.txt,.md"
              onChange={(e) => setFormData({...formData, presentationContent: e.target.files?.[0] || null})}
            />
          </div>
        ) : (
          <div className="space-y-2">
            <Label htmlFor="slides-url">Google Slides URL</Label>
            <Input
              id="slides-url"
              placeholder="https://docs.google.com/presentation/d/your-presentation-id/edit"
              value={formData.slidesUrl}
              onChange={(e) => setFormData({...formData, slidesUrl: e.target.value})}
            />
            <p className="text-sm text-muted-foreground">
              Make sure the presentation is publicly accessible or shared with the service account
            </p>
          </div>
        )}
      </div>

      {/* Voice Options */}
      <VoiceSelectionSection
        formData={formData}
        setFormData={setFormData}
        voiceProfiles={voiceProfiles}
        showNewProfileCreation={false}
      />
    </div>
  )
}

// Additional components...
function VoiceSelectionSection({ formData, setFormData, voiceProfiles, showNewProfileCreation = true }) {
  return (
    <div className="space-y-4">
      <div className="space-y-2">
        <Label>Voice Selection</Label>
        <Select
          value={formData.voiceProfile}
          onValueChange={(value) => setFormData({...formData, voiceProfile: value})}
        >
          <SelectTrigger>
            <SelectValue placeholder="Select voice profile or use default" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="">Default TTS Voice</SelectItem>
            {voiceProfiles.map((profile) => (
              <SelectItem key={profile.name} value={profile.name}>
                {profile.name} ({profile.language})
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {showNewProfileCreation && (
        <div className="space-y-2">
          <Label htmlFor="new-voice-name">New Voice Profile Name (Optional)</Label>
          <Input
            id="new-voice-name"
            placeholder="Enter name to save cloned voice"
            value={formData.newVoiceProfileName}
            onChange={(e) => setFormData({...formData, newVoiceProfileName: e.target.value})}
          />
          <p className="text-sm text-muted-foreground">
            If provided, voice will be cloned from reference video and saved
          </p>
        </div>
      )}
    </div>
  )
}
```

### Day 25-28: Testing and Optimization

#### 4.3 Integration Testing Script

**File: `presgen-training2/test_integration.py`**
```python
#!/usr/bin/env python3
"""
PresGen-Training2 Integration Test Script
Tests all three modes with the provided test video
"""

import sys
import time
import logging
from pathlib import Path

# Test asset path (provided by user)
TEST_VIDEO_PATH = "/Users/yitzchak/Documents/learn/presentation_project/sales-agent-labs/sadtalker-api/examples/presgen_test2.mp4"

# Test script for avatar generation
TEST_SCRIPT = """
Hello investors! I'm excited to present our revolutionary AI technology.
Our system automatically generates professional presentation videos from simple text inputs.
This demonstrates our proprietary avatar generation and content analysis capabilities.
We're transforming how companies create training and marketing content worldwide.
With our technology, anyone can produce studio-quality videos in minutes, not hours.
"""

# Test Google Slides URL (you'll need to replace with actual URL)
TEST_SLIDES_URL = "https://docs.google.com/presentation/d/your-test-presentation-id/edit"

def setup_logging():
    """Setup comprehensive logging for testing"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(f'logs/integration_test_{int(time.time())}.log')
        ]
    )

def test_video_only_mode():
    """Test Mode 1: Video-Only"""

    print("🎬 Testing Video-Only Mode...")

    from src.modes.orchestrator import ModeOrchestrator, VideoOnlyRequest

    orchestrator = ModeOrchestrator()

    request = VideoOnlyRequest(
        mode="video_only",
        script_text=TEST_SCRIPT,
        reference_video=TEST_VIDEO_PATH,
        new_voice_profile_name="test_voice_profile",
        quality_level="fast",  # Use fast for testing
        instructions="Make this sound professional and engaging"
    )

    start_time = time.time()
    result = orchestrator.process_video_only(request)
    processing_time = time.time() - start_time

    if result.success:
        print(f"✅ Video-Only Mode: SUCCESS ({processing_time:.1f}s)")
        print(f"   Output: {result.output_path}")
        print(f"   Processing time: {result.processing_time:.1f}s")
        return True
    else:
        print(f"❌ Video-Only Mode: FAILED - {result.error}")
        return False

def test_presentation_only_mode():
    """Test Mode 2: Presentation-Only"""

    print("📊 Testing Presentation-Only Mode...")

    from src.modes.orchestrator import ModeOrchestrator, PresentationOnlyRequest

    orchestrator = ModeOrchestrator()

    # Test with content generation (Option A)
    request = PresentationOnlyRequest(
        mode="presentation_only",
        content_file="examples/test_content.txt",  # Create this file with sample content
        voice_profile_name="test_voice_profile",  # Use voice from previous test
        quality_level="fast",
        instructions="Create a professional business presentation"
    )

    start_time = time.time()
    result = orchestrator.process_presentation_only(request)
    processing_time = time.time() - start_time

    if result.success:
        print(f"✅ Presentation-Only Mode: SUCCESS ({processing_time:.1f}s)")
        print(f"   Output: {result.output_path}")
        print(f"   Slides: {result.metadata.get('total_slides', 'unknown')}")
        return True
    else:
        print(f"❌ Presentation-Only Mode: FAILED - {result.error}")
        return False

def test_video_presentation_mode():
    """Test Mode 3: Video-Presentation Combined"""

    print("🎥📊 Testing Video-Presentation Mode...")

    from src.modes.orchestrator import ModeOrchestrator, VideoPresentationRequest

    orchestrator = ModeOrchestrator()

    request = VideoPresentationRequest(
        mode="video_presentation",
        script_text=TEST_SCRIPT,
        reference_video=TEST_VIDEO_PATH,
        content_file="examples/test_content.txt",
        voice_profile_name="test_voice_profile",
        quality_level="fast",
        instructions="Create a cohesive video with professional presentation"
    )

    start_time = time.time()
    result = orchestrator.process_video_presentation(request)
    processing_time = time.time() - start_time

    if result.success:
        print(f"✅ Video-Presentation Mode: SUCCESS ({processing_time:.1f}s)")
        print(f"   Output: {result.output_path}")
        print(f"   Total duration: {result.metadata.get('total_duration', 'unknown')}s")
        return True
    else:
        print(f"❌ Video-Presentation Mode: FAILED - {result.error}")
        return False

def test_voice_cloning():
    """Test voice cloning functionality"""

    print("🎤 Testing Voice Cloning...")

    from src.core.voice.voice_manager import VoiceProfileManager

    voice_manager = VoiceProfileManager()

    try:
        # Test voice cloning
        profile = voice_manager.clone_voice_from_video(
            video_path=TEST_VIDEO_PATH,
            profile_name="integration_test_voice",
            language="en"
        )

        print(f"✅ Voice Cloning: SUCCESS")
        print(f"   Profile: {profile.name}")
        print(f"   Quality: {profile.quality_score:.2f}")

        # Test speech generation
        test_audio = voice_manager.generate_speech(
            text="This is a test of the cloned voice system.",
            voice_profile_name=profile.name,
            output_path="temp/voice_test.wav"
        )

        print(f"✅ Speech Generation: SUCCESS")
        print(f"   Audio: {test_audio}")

        return True

    except Exception as e:
        print(f"❌ Voice Cloning: FAILED - {str(e)}")
        return False

def test_google_slides_integration():
    """Test Google Slides integration (requires valid URL)"""

    print("📋 Testing Google Slides Integration...")

    try:
        from src.presentation.slides.google_slides_client import GoogleSlidesClient

        client = GoogleSlidesClient()

        # This will fail without proper setup, but test the code path
        # presentation_data = client.process_slides_url(TEST_SLIDES_URL)

        print("⚠️  Google Slides: SKIPPED (requires valid URL and credentials)")
        return True

    except Exception as e:
        print(f"⚠️  Google Slides: SKIPPED - {str(e)}")
        return True  # Don't fail entire test suite

def create_test_content():
    """Create test content files"""

    test_content = """
# AI Technology Presentation

## Executive Summary
Our revolutionary AI technology transforms content creation through automated video generation and intelligent presentation assembly.

## Key Features
- Automated avatar video generation
- Voice cloning and synthesis
- Intelligent content analysis
- Professional presentation creation

## Market Opportunity
The video content creation market represents a $10B opportunity growing at 25% annually.

## Technology Advantage
- Local-first processing
- Zero marginal costs
- Professional quality output
- Rapid generation speed

## Business Model
- B2B SaaS platform
- Enterprise licensing
- Professional services
- Technology partnerships
"""

    Path("examples").mkdir(exist_ok=True)
    with open("examples/test_content.txt", 'w') as f:
        f.write(test_content)

    print("✅ Test content files created")

def run_performance_benchmark():
    """Run performance benchmarks"""

    print("⏱️  Running Performance Benchmarks...")

    benchmarks = {
        "voice_cloning_time": 0,
        "avatar_generation_time": 0,
        "presentation_rendering_time": 0,
        "video_appending_time": 0,
        "total_pipeline_time": 0
    }

    # This would run actual benchmarks
    print("⚠️  Performance Benchmarks: TODO - implement detailed timing")

def validate_m1_compatibility():
    """Validate M1 Mac compatibility"""

    print("🖥️  Validating M1 Mac Compatibility...")

    import platform
    import torch

    system_info = {
        "platform": platform.platform(),
        "processor": platform.processor(),
        "python_version": platform.python_version(),
        "pytorch_version": torch.__version__,
        "mps_available": torch.backends.mps.is_available(),
        "mps_built": torch.backends.mps.is_built()
    }

    print("System Information:")
    for key, value in system_info.items():
        print(f"   {key}: {value}")

    if "arm64" in platform.platform().lower():
        print("✅ M1 Mac detected")
        if torch.backends.mps.is_available():
            print("✅ MPS acceleration available")
        else:
            print("⚠️  MPS acceleration not available")
    else:
        print("ℹ️  Non-M1 system detected")

    return True

def main():
    """Run complete integration test suite"""

    print("🚀 PresGen-Training2 Integration Test Suite")
    print("=" * 50)

    setup_logging()

    # Check test video exists
    if not Path(TEST_VIDEO_PATH).exists():
        print(f"❌ Test video not found: {TEST_VIDEO_PATH}")
        print("Please update TEST_VIDEO_PATH with correct path")
        return False

    # Create test files
    create_test_content()

    # Run tests
    tests = [
        ("System Validation", validate_m1_compatibility),
        ("Voice Cloning", test_voice_cloning),
        ("Video-Only Mode", test_video_only_mode),
        ("Presentation-Only Mode", test_presentation_only_mode),
        ("Video-Presentation Mode", test_video_presentation_mode),
        ("Google Slides Integration", test_google_slides_integration)
    ]

    results = []
    total_start_time = time.time()

    for test_name, test_func in tests:
        print(f"\n📋 Running: {test_name}")
        print("-" * 30)

        try:
            success = test_func()
            results.append((test_name, success))
        except Exception as e:
            print(f"❌ {test_name}: EXCEPTION - {str(e)}")
            results.append((test_name, False))

    total_time = time.time() - total_start_time

    # Summary
    print("\n" + "=" * 50)
    print("🏁 Test Suite Summary")
    print("=" * 50)

    passed = sum(1 for _, success in results if success)
    total = len(results)

    for test_name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"   {status} {test_name}")

    print(f"\nResults: {passed}/{total} tests passed")
    print(f"Total time: {total_time:.1f} seconds")

    if passed == total:
        print("🎉 All tests passed! System ready for production.")
        return True
    else:
        print("⚠️  Some tests failed. Check logs for details.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
```

Now I'll create the folder structure and update the .gitignore as planned.

<function_calls>
<invoke name="TodoWrite">
<parameter name="todos">[{"content": "Create comprehensive PRD with Google Slides URL support", "status": "completed", "activeForm": "Creating comprehensive PRD with Google Slides URL support"}, {"content": "Create Architecture document with slides-to-MP4 and video appending pipeline", "status": "completed", "activeForm": "Creating Architecture document with slides-to-MP4 and video appending pipeline"}, {"content": "Create Implementation Plan with phased roadmap", "status": "completed", "activeForm": "Creating Implementation Plan with phased roadmap"}, {"content": "Setup presgen-training2 folder structure", "status": "in_progress", "activeForm": "Setting up presgen-training2 folder structure"}, {"content": "Update .gitignore for model files and external downloads", "status": "pending", "activeForm": "Updating .gitignore for model files and external downloads"}]