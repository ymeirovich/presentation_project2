# PresGen-Training2: Technical Architecture

## System Overview

**PresGen-Training2** implements a modular, pipeline-based architecture for AI avatar video generation with advanced presentation integration. The system is designed for local-first processing on M1 Mac hardware while maintaining extensibility for cloud deployment.

### Core Architecture Principles

1. **Modular Pipeline Design**: Composable processing stages for flexibility
2. **Local-First Processing**: Zero cloud dependencies, complete privacy control
3. **Hardware Adaptive**: Automatic optimization based on available resources
4. **Fallback Systems**: Graceful degradation with multiple quality levels
5. **Integration Friendly**: Seamless compatibility with existing PresGen infrastructure

## System Architecture Overview

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   PresGen-UI    │    │   FastAPI       │    │  Processing     │
│   Training Tab  │────│   Extensions    │────│   Pipeline      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         │                       │                       ▼
         │                       │              ┌─────────────────┐
         │                       │              │  Mode           │
         │                       │              │  Orchestrator   │
         │                       │              └─────────────────┘
         │                       │                       │
         │                       │                       ▼
         │                       │              ┌─────────────────┐
         │                       │              │  Video-Only     │
         │                       │              │  Presentation   │
         │                       │              │  Combined       │
         │                       │              └─────────────────┘
         │                       │                       │
         │                       │                       ▼
         │                       │              ┌─────────────────┐
         │                       │              │  Output         │
         │                       └──────────────│  Management     │
         └────────────────────────────────────────│  & Download     │
                                                └─────────────────┘
```

## Core Components Architecture

### 1. LivePortrait Integration Layer

#### Avatar Generation Engine
```python
class LivePortraitEngine:
    """Main LivePortrait integration with M1 Mac optimizations"""

    def __init__(self, hardware_profile: HardwareProfile):
        self.config = self._load_m1_optimized_config()
        self.model_cache = ModelCache()
        self.resource_monitor = ResourceMonitor()

    def generate_avatar_video(self,
                            audio_path: str,
                            reference_image: str,
                            quality_level: str = "standard") -> AvatarResult:
        """
        Generate avatar video with hardware-adaptive settings

        Args:
            audio_path: Path to narration audio file
            reference_image: Path to source image for avatar
            quality_level: "fast", "standard", or "high"

        Returns:
            AvatarResult with video path and metadata
        """

        # Hardware-specific configuration
        processing_config = self._get_processing_config(quality_level)

        with self.resource_monitor.track_usage():
            # Motion preprocessing
            motion_data = self._preprocess_motion(audio_path, processing_config)

            # Avatar rendering
            avatar_video = self._render_avatar(
                reference_image=reference_image,
                motion_data=motion_data,
                config=processing_config
            )

            return AvatarResult(
                success=True,
                output_path=avatar_video,
                processing_time=self.resource_monitor.get_elapsed_time(),
                quality_level=quality_level
            )
```

#### M1 Mac Optimization Configuration
```yaml
# config/m1_mac_config.yaml
hardware_profiles:
  m1_8gb:
    memory_fraction: 0.6
    batch_size: 1
    resolution_limit: "720p"
    processing_timeout: 900  # 15 minutes

  m1_16gb:
    memory_fraction: 0.7
    batch_size: 2
    resolution_limit: "1080p"
    processing_timeout: 1200  # 20 minutes

liveportrait_settings:
  pytorch_mps_fallback: true
  model_precision: "fp16"
  memory_efficient: true
  cache_models: true
```

### 2. Voice Cloning System Architecture

#### Voice Profile Management
```python
class VoiceProfileManager:
    """Manage voice cloning profiles with persistence"""

    def __init__(self):
        self.profiles_db = ProfileDatabase("voice_profiles.json")
        self.model_storage = ModelStorage("voice-models/")

    def clone_voice_from_video(self,
                             video_path: str,
                             profile_name: str,
                             language: str = "auto") -> VoiceProfile:
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

        # Step 1: Extract enhanced audio
        clean_audio = self._extract_enhanced_audio(video_path)

        # Step 2: Language detection
        detected_language = self._detect_language(clean_audio) if language == "auto" else language

        # Step 3: Voice cloning model training
        cloning_model = self._train_voice_model(
            audio_path=clean_audio,
            language=detected_language,
            profile_name=profile_name
        )

        # Step 4: Save profile
        profile = VoiceProfile(
            name=profile_name,
            language=detected_language,
            model_path=self.model_storage.save_model(cloning_model),
            created_at=datetime.now(),
            source_video=video_path,
            quality_metrics=self._assess_quality(cloning_model)
        )

        self.profiles_db.save_profile(profile)
        return profile

    def _extract_enhanced_audio(self, video_path: str) -> str:
        """Extract and enhance audio for voice cloning"""

        output_path = f"temp/enhanced_audio_{uuid.uuid4().hex}.wav"

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

        subprocess.run(enhancement_cmd, check=True)
        return output_path
```

### 3. Google Slides Integration System

#### Slides Processing Architecture
```python
class GoogleSlidesProcessor:
    """Handle Google Slides URL processing and content extraction"""

    def __init__(self):
        self.slides_service = self._initialize_slides_api()
        self.image_exporter = SlideImageExporter()

    def process_slides_url(self, slides_url: str) -> PresentationData:
        """
        Extract presentation data from Google Slides URL

        Process:
        1. Parse URL and extract presentation ID
        2. Access presentation via Google Slides API
        3. Extract slide content and notes
        4. Export slides as high-quality images
        5. Process notes for narration timing

        Returns:
            PresentationData with slides and narration info
        """

        presentation_id = self._extract_presentation_id(slides_url)

        # Get presentation structure
        presentation = self.slides_service.presentations().get(
            presentationId=presentation_id
        ).execute()

        slides_data = []
        for i, slide in enumerate(presentation.get('slides', [])):
            slide_data = self._process_individual_slide(
                presentation_id=presentation_id,
                slide=slide,
                slide_index=i
            )
            slides_data.append(slide_data)

        return PresentationData(
            presentation_id=presentation_id,
            title=presentation.get('title', 'Untitled Presentation'),
            slides=slides_data,
            total_slides=len(slides_data)
        )

    def _process_individual_slide(self, presentation_id: str, slide: dict, slide_index: int) -> SlideData:
        """Process individual slide with notes extraction"""

        slide_id = slide['objectId']

        # Export slide as high-quality image
        slide_image_path = self.image_exporter.export_slide(
            presentation_id=presentation_id,
            slide_id=slide_id,
            slide_index=slide_index
        )

        # Extract notes for narration
        notes_text = self._extract_slide_notes(presentation_id, slide_id)

        # Calculate narration timing
        estimated_duration = self._estimate_narration_duration(notes_text)

        return SlideData(
            slide_id=slide_id,
            slide_index=slide_index,
            image_path=slide_image_path,
            notes_text=notes_text,
            estimated_duration=estimated_duration,
            has_notes=bool(notes_text.strip())
        )

    def _extract_slide_notes(self, presentation_id: str, slide_id: str) -> str:
        """Extract notes section text from slide"""

        try:
            # Get slide with notes page
            slide_response = self.slides_service.presentations().pages().get(
                presentationId=presentation_id,
                pageObjectId=slide_id
            ).execute()

            notes_text = ""
            if 'notesPage' in slide_response:
                # Parse notes page elements
                notes_page = slide_response['notesPage']
                notes_text = self._parse_notes_elements(notes_page)

            return notes_text

        except Exception as e:
            logging.warning(f"Could not extract notes for slide {slide_id}: {e}")
            return ""

    def _parse_notes_elements(self, notes_page: dict) -> str:
        """Parse text elements from notes page"""

        notes_text = ""

        for page_element in notes_page.get('pageElements', []):
            if 'shape' in page_element and 'text' in page_element['shape']:
                text_content = page_element['shape']['text']
                for text_element in text_content.get('textElements', []):
                    if 'textRun' in text_element:
                        notes_text += text_element['textRun'].get('content', '')

        return notes_text.strip()
```

### 4. Presentation-to-Video Conversion Pipeline

#### Slides Video Renderer
```python
class SlidesToVideoRenderer:
    """Convert slides with narration to MP4 video"""

    def __init__(self):
        self.tts_engine = TTSEngine()
        self.video_composer = VideoComposer()

    def render_presentation_video(self,
                                presentation_data: PresentationData,
                                voice_profile: str = None) -> str:
        """
        Convert presentation slides to narrated video

        Process:
        1. Generate narration audio for each slide
        2. Calculate slide timings based on audio duration
        3. Create video segments for each slide
        4. Add transitions between slides
        5. Compose final presentation video

        Returns:
            Path to rendered presentation MP4
        """

        video_segments = []
        total_duration = 0

        for slide_data in presentation_data.slides:
            # Generate narration audio
            if slide_data.has_notes:
                narration_audio = self.tts_engine.generate_speech(
                    text=slide_data.notes_text,
                    voice_profile=voice_profile
                )
                slide_duration = self._get_audio_duration(narration_audio)
            else:
                # Default 3-second display for slides without notes
                narration_audio = self.tts_engine.generate_silence(duration=3.0)
                slide_duration = 3.0

            # Create video segment for this slide
            slide_video_segment = self._create_slide_video_segment(
                image_path=slide_data.image_path,
                audio_path=narration_audio,
                duration=slide_duration,
                slide_index=slide_data.slide_index
            )

            video_segments.append(slide_video_segment)
            total_duration += slide_duration

        # Compose final presentation video with transitions
        final_video_path = self.video_composer.compose_presentation(
            segments=video_segments,
            total_duration=total_duration,
            transition_style="professional"
        )

        return final_video_path

    def _create_slide_video_segment(self,
                                  image_path: str,
                                  audio_path: str,
                                  duration: float,
                                  slide_index: int) -> str:
        """Create individual slide video segment"""

        output_path = f"temp/slide_{slide_index:03d}.mp4"

        # FFmpeg command to create slide video with audio
        ffmpeg_cmd = [
            "ffmpeg",
            "-loop", "1",              # Loop static image
            "-i", image_path,          # Input slide image
            "-i", audio_path,          # Input narration audio
            "-c:v", "libx264",
            "-tune", "stillimage",
            "-c:a", "aac",
            "-b:a", "192k",
            "-pix_fmt", "yuv420p",
            "-t", str(duration),       # Video duration matches audio
            "-shortest",
            "-y", output_path
        ]

        subprocess.run(ffmpeg_cmd, check=True)
        return output_path
```

### 5. Video Appending System Architecture

#### Video Concatenation Engine
```python
class VideoAppendingEngine:
    """Handle seamless video concatenation with transitions"""

    def __init__(self):
        self.format_normalizer = VideoFormatNormalizer()
        self.transition_generator = TransitionGenerator()

    def append_videos(self,
                     avatar_video_path: str,
                     presentation_video_path: str,
                     transition_type: str = "fade") -> str:
        """
        Concatenate avatar video with presentation video

        Process:
        1. Normalize video formats and quality
        2. Generate transition segment
        3. Concatenate videos with FFmpeg
        4. Verify output quality and synchronization

        Returns:
            Path to final concatenated MP4
        """

        # Step 1: Normalize formats
        normalized_avatar = self.format_normalizer.normalize_video(
            video_path=avatar_video_path,
            target_format=VideoFormat.STANDARD_MP4
        )

        normalized_presentation = self.format_normalizer.normalize_video(
            video_path=presentation_video_path,
            target_format=VideoFormat.STANDARD_MP4
        )

        # Step 2: Generate transition
        transition_segment = self.transition_generator.create_transition(
            from_video=normalized_avatar,
            to_video=normalized_presentation,
            transition_type=transition_type,
            duration=1.0  # 1-second transition
        )

        # Step 3: Concatenate videos
        final_video_path = self._concatenate_with_ffmpeg([
            normalized_avatar,
            transition_segment,
            normalized_presentation
        ])

        # Step 4: Verify output
        self._verify_concatenation_quality(final_video_path)

        return final_video_path

    def _concatenate_with_ffmpeg(self, video_segments: List[str]) -> str:
        """Use FFmpeg to concatenate video segments"""

        output_path = f"output/final_video_{uuid.uuid4().hex}.mp4"

        # Create concat list file
        concat_list_path = "temp/concat_list.txt"
        with open(concat_list_path, 'w') as f:
            for segment in video_segments:
                f.write(f"file '{os.path.abspath(segment)}'\n")

        # FFmpeg concatenation command
        concat_cmd = [
            "ffmpeg",
            "-f", "concat",
            "-safe", "0",
            "-i", concat_list_path,
            "-c", "copy",              # Copy streams without re-encoding
            "-y", output_path
        ]

        subprocess.run(concat_cmd, check=True)

        # Cleanup temporary files
        os.unlink(concat_list_path)
        for segment in video_segments:
            if "temp/" in segment:
                os.unlink(segment)

        return output_path
```

#### Format Normalization System
```python
class VideoFormatNormalizer:
    """Ensure consistent video formats for concatenation"""

    def normalize_video(self, video_path: str, target_format: VideoFormat) -> str:
        """
        Normalize video to target format specifications

        Ensures:
        - Consistent resolution
        - Matching frame rate
        - Compatible codec
        - Synchronized audio
        """

        # Analyze input video
        video_info = self._analyze_video(video_path)

        if self._is_format_compatible(video_info, target_format):
            return video_path  # No conversion needed

        # Convert to target format
        normalized_path = f"temp/normalized_{uuid.uuid4().hex}.mp4"

        conversion_cmd = [
            "ffmpeg",
            "-i", video_path,
            "-c:v", target_format.video_codec,
            "-c:a", target_format.audio_codec,
            "-r", str(target_format.frame_rate),
            "-s", target_format.resolution,
            "-b:v", target_format.video_bitrate,
            "-b:a", target_format.audio_bitrate,
            "-y", normalized_path
        ]

        subprocess.run(conversion_cmd, check=True)
        return normalized_path
```

### 6. Mode Orchestration Architecture

#### Three-Mode Processing Engine
```python
class ModeOrchestrator:
    """Central orchestrator for three processing modes"""

    def __init__(self):
        self.avatar_engine = LivePortraitEngine()
        self.slides_processor = GoogleSlidesProcessor()
        self.slides_renderer = SlidesToVideoRenderer()
        self.video_appender = VideoAppendingEngine()
        self.voice_manager = VoiceProfileManager()

    def process_video_only(self, request: VideoOnlyRequest) -> ProcessingResult:
        """Mode 1: Generate avatar video only"""

        # Content processing
        if request.content_file:
            script = self._summarize_content_to_script(request.content_file)
        else:
            script = request.script_text

        # Apply custom instructions
        if request.instructions:
            script = self._enhance_script_with_instructions(script, request.instructions)

        # Voice cloning (if new voice)
        if request.reference_video and not request.voice_profile:
            voice_profile = self.voice_manager.clone_voice_from_video(
                video_path=request.reference_video,
                profile_name=request.voice_profile_name or "temp_voice"
            )
        else:
            voice_profile = request.voice_profile

        # Generate TTS audio
        narration_audio = self._generate_narration_audio(script, voice_profile)

        # Extract avatar image
        avatar_image = self._extract_avatar_image(request.reference_video)

        # Generate avatar video
        avatar_result = self.avatar_engine.generate_avatar_video(
            audio_path=narration_audio,
            reference_image=avatar_image,
            quality_level=request.quality_level
        )

        return ProcessingResult(
            success=True,
            output_path=avatar_result.output_path,
            mode="video_only",
            processing_time=avatar_result.processing_time
        )

    def process_presentation_only(self, request: PresentationOnlyRequest) -> ProcessingResult:
        """Mode 2: Generate presentation video only"""

        if request.slides_url:
            # Option B: Use existing Google Slides
            presentation_data = self.slides_processor.process_slides_url(request.slides_url)
        else:
            # Option A: Generate new slides
            presentation_data = self._generate_new_presentation(request.content_file)

        # Render presentation to video
        presentation_video = self.slides_renderer.render_presentation_video(
            presentation_data=presentation_data,
            voice_profile=request.voice_profile
        )

        return ProcessingResult(
            success=True,
            output_path=presentation_video,
            mode="presentation_only"
        )

    def process_video_presentation(self, request: VideoPresentationRequest) -> ProcessingResult:
        """Mode 3: Combined avatar + presentation video"""

        # Generate avatar video (Mode 1)
        avatar_request = self._extract_video_only_request(request)
        avatar_result = self.process_video_only(avatar_request)

        # Generate presentation video (Mode 2)
        presentation_request = self._extract_presentation_only_request(request)
        presentation_result = self.process_presentation_only(presentation_request)

        # Append videos
        final_video = self.video_appender.append_videos(
            avatar_video_path=avatar_result.output_path,
            presentation_video_path=presentation_result.output_path
        )

        return ProcessingResult(
            success=True,
            output_path=final_video,
            mode="video_presentation",
            processing_time=avatar_result.processing_time + presentation_result.processing_time
        )
```

## Integration Architecture

### 1. FastAPI Extension Integration

#### API Endpoint Architecture
```python
# Extended from src/service/http.py

@app.post("/training/video-only")
async def process_video_only_mode(
    content: Optional[UploadFile] = None,
    script_text: Optional[str] = None,
    reference_video: Optional[UploadFile] = None,
    voice_profile: Optional[str] = None,
    quality_level: str = "standard",
    instructions: Optional[str] = None
):
    """Process Video-Only mode request"""

    job_id = create_training_job("video_only")

    # Background processing
    background_tasks.add_task(
        orchestrator.process_video_only,
        job_id=job_id,
        request_data=VideoOnlyRequest(
            content_file=content,
            script_text=script_text,
            reference_video=reference_video,
            voice_profile=voice_profile,
            quality_level=quality_level,
            instructions=instructions
        )
    )

    return {"job_id": job_id, "status": "processing"}

@app.post("/training/presentation-only")
async def process_presentation_only_mode(
    slides_url: Optional[str] = None,
    content: Optional[UploadFile] = None,
    voice_profile: Optional[str] = None,
    instructions: Optional[str] = None
):
    """Process Presentation-Only mode request"""

    if not slides_url and not content:
        raise HTTPException(400, "Either slides_url or content must be provided")

    job_id = create_training_job("presentation_only")

    background_tasks.add_task(
        orchestrator.process_presentation_only,
        job_id=job_id,
        request_data=PresentationOnlyRequest(
            slides_url=slides_url,
            content_file=content,
            voice_profile=voice_profile,
            instructions=instructions
        )
    )

    return {"job_id": job_id, "status": "processing"}

@app.post("/training/video-presentation")
async def process_video_presentation_mode(
    # Avatar video parameters
    content: Optional[UploadFile] = None,
    script_text: Optional[str] = None,
    reference_video: Optional[UploadFile] = None,

    # Presentation parameters
    slides_url: Optional[str] = None,
    presentation_content: Optional[UploadFile] = None,

    # Shared parameters
    voice_profile: Optional[str] = None,
    quality_level: str = "standard",
    instructions: Optional[str] = None
):
    """Process combined Video-Presentation mode"""

    job_id = create_training_job("video_presentation")

    background_tasks.add_task(
        orchestrator.process_video_presentation,
        job_id=job_id,
        request_data=VideoPresentationRequest(
            # Video-only parameters
            content_file=content,
            script_text=script_text,
            reference_video=reference_video,

            # Presentation parameters
            slides_url=slides_url,
            presentation_content=presentation_content,

            # Shared parameters
            voice_profile=voice_profile,
            quality_level=quality_level,
            instructions=instructions
        )
    )

    return {"job_id": job_id, "status": "processing"}
```

### 2. Job Management Integration

#### Extended Job System
```python
class TrainingJobManager:
    """Extended job management for training operations"""

    def __init__(self):
        self.jobs = {}  # Integrate with existing job system

    def create_training_job(self, mode: str) -> str:
        """Create job compatible with existing PresGen infrastructure"""

        job_id = str(uuid.uuid4())
        job_data = {
            "id": job_id,
            "type": f"training_{mode}",
            "status": "created",
            "mode": mode,
            "created_at": time.time(),
            "stages": self._get_mode_stages(mode),
            "current_stage": 0,
            "progress": 0.0
        }

        self.jobs[job_id] = job_data
        return job_id

    def _get_mode_stages(self, mode: str) -> List[str]:
        """Define processing stages for each mode"""

        stage_definitions = {
            "video_only": [
                "content_processing",
                "script_generation",
                "voice_cloning",
                "avatar_generation",
                "finalization"
            ],
            "presentation_only": [
                "content_processing",
                "slide_extraction",
                "narration_generation",
                "video_composition",
                "finalization"
            ],
            "video_presentation": [
                "content_processing",
                "script_generation",
                "voice_cloning",
                "avatar_generation",
                "slide_processing",
                "presentation_rendering",
                "video_appending",
                "finalization"
            ]
        }

        return stage_definitions.get(mode, ["processing"])
```

## Performance Optimization Architecture

### 1. M1 Mac Hardware Optimization

#### Resource Management System
```python
class M1MacOptimizer:
    """Optimize processing for Apple Silicon hardware"""

    def __init__(self):
        self.hardware_profile = self._detect_m1_configuration()
        self.thermal_monitor = ThermalMonitor()

    def get_optimized_settings(self, processing_mode: str) -> OptimizationSettings:
        """Get hardware-optimized settings"""

        base_settings = {
            "pytorch_mps_fallback": True,
            "memory_fraction": 0.7 if self.hardware_profile.ram_gb >= 16 else 0.6,
            "batch_size": 1,
            "model_precision": "fp16"
        }

        if self.thermal_monitor.is_thermal_throttling():
            # Reduce processing intensity under thermal load
            base_settings.update({
                "quality_level": "fast",
                "resolution": "720p",
                "memory_fraction": 0.5
            })

        mode_specific_settings = {
            "video_only": {
                "avatar_quality": "standard",
                "processing_timeout": 900
            },
            "presentation_only": {
                "slide_processing_parallel": False,
                "tts_quality": "standard"
            },
            "video_presentation": {
                "avatar_quality": "fast",
                "processing_timeout": 1800
            }
        }

        base_settings.update(mode_specific_settings.get(processing_mode, {}))
        return OptimizationSettings(**base_settings)
```

### 2. Caching and Model Management

#### Model Cache System
```python
class ModelCacheManager:
    """Efficient model loading and caching"""

    def __init__(self):
        self.cache_dir = "models/cache/"
        self.loaded_models = {}
        self.max_cache_size_gb = 4.0  # 4GB cache limit

    def load_liveportrait_model(self, quality_level: str) -> Any:
        """Load LivePortrait model with caching"""

        model_key = f"liveportrait_{quality_level}"

        if model_key in self.loaded_models:
            return self.loaded_models[model_key]

        # Load model with appropriate configuration
        model_config = self._get_model_config(quality_level)
        model = self._load_model_from_disk(model_config)

        # Cache model if space available
        if self._get_cache_size() < self.max_cache_size_gb:
            self.loaded_models[model_key] = model

        return model

    def cleanup_cache(self):
        """Clean up model cache to free memory"""
        self.loaded_models.clear()
        torch.cuda.empty_cache() if torch.cuda.is_available() else None

        # Force garbage collection
        import gc
        gc.collect()
```

## Error Handling and Fallback Architecture

### 1. Graceful Degradation System

#### Quality Fallback Engine
```python
class QualityFallbackSystem:
    """Handle quality degradation under resource constraints"""

    def __init__(self):
        self.quality_levels = ["high", "standard", "fast", "minimal"]
        self.current_level = "standard"

    def handle_processing_failure(self, error: ProcessingError, current_settings: dict):
        """Implement fallback strategy for processing failures"""

        fallback_strategies = [
            self._reduce_quality_level,
            self._reduce_resolution,
            self._switch_to_cpu_processing,
            self._use_static_fallback
        ]

        for strategy in fallback_strategies:
            try:
                new_settings = strategy(current_settings, error)
                logging.info(f"Applying fallback strategy: {strategy.__name__}")
                return new_settings
            except Exception as e:
                logging.warning(f"Fallback strategy {strategy.__name__} failed: {e}")
                continue

        raise ProcessingFailureError("All fallback strategies exhausted")

    def _reduce_quality_level(self, settings: dict, error: ProcessingError) -> dict:
        """Reduce processing quality level"""

        current_index = self.quality_levels.index(settings.get("quality_level", "standard"))
        if current_index < len(self.quality_levels) - 1:
            new_quality = self.quality_levels[current_index + 1]
            settings["quality_level"] = new_quality
            return settings

        raise FallbackExhaustedException("Cannot reduce quality further")
```

## Security and Privacy Architecture

### 1. Local Processing Security

#### Data Privacy System
```python
class PrivacyManager:
    """Ensure data privacy and security"""

    def __init__(self):
        self.encryption_key = self._generate_session_key()
        self.temp_file_manager = TempFileManager()

    def secure_file_processing(self, file_path: str) -> str:
        """Encrypt files during processing"""

        encrypted_path = self.temp_file_manager.create_encrypted_temp_file()

        with open(file_path, 'rb') as infile, \
             open(encrypted_path, 'wb') as outfile:

            encrypted_data = self._encrypt_data(infile.read())
            outfile.write(encrypted_data)

        return encrypted_path

    def cleanup_all_temp_files(self):
        """Secure cleanup of all temporary files"""

        self.temp_file_manager.secure_delete_all()

        # Clear memory
        if hasattr(self, 'encryption_key'):
            del self.encryption_key
```

## Deployment Architecture

### 1. Development Environment Setup

#### Auto-Installation System
```bash
#!/bin/bash
# setup_presgen_training2.sh

echo "Setting up PresGen-Training2 development environment..."

# Check hardware
if [[ $(uname -m) == "arm64" ]]; then
    echo "Detected Apple Silicon (M1/M2) - applying optimizations"
    export PYTORCH_ENABLE_MPS_FALLBACK=1
fi

# Create directory structure
mkdir -p presgen-training2/{src,config,models,temp,output}
mkdir -p presgen-training2/src/{core,presentation,pipeline,api}

# Install LivePortrait
if [ ! -d "LivePortrait" ]; then
    echo "Installing LivePortrait..."
    git clone https://github.com/KwaiVGI/LivePortrait.git
    cd LivePortrait
    pip3 install -r requirements.txt
    cd ..
fi

# Download models
python3 -c "
import subprocess
import sys

try:
    # Download LivePortrait models
    subprocess.run([
        'huggingface-cli', 'download', 'KwaiVGI/LivePortrait',
        '--local-dir', 'LivePortrait/pretrained_weights'
    ], check=True)
    print('✅ LivePortrait models downloaded')
except Exception as e:
    print(f'❌ Model download failed: {e}')
    sys.exit(1)
"

echo "✅ PresGen-Training2 setup complete!"
```

### 2. Production Deployment Configuration

#### Docker Configuration
```dockerfile
# Dockerfile.presgen-training2
FROM python:3.10-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    git \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY presgen-training2/src ./src
COPY presgen-training2/config ./config

# Create necessary directories
RUN mkdir -p {models,temp,output,logs}

# Set environment variables
ENV PYTHONPATH=/app
ENV PYTORCH_ENABLE_MPS_FALLBACK=1

# Expose port
EXPOSE 8080

# Run application
CMD ["python", "-m", "src.api.main"]
```

## Monitoring and Observability Architecture

### 1. Performance Monitoring

#### Metrics Collection System
```python
class PerformanceMonitor:
    """Comprehensive performance monitoring"""

    def __init__(self):
        self.metrics_collector = MetricsCollector()
        self.performance_db = PerformanceDatabase()

    def track_processing_pipeline(self, mode: str, job_id: str):
        """Track complete processing pipeline performance"""

        return ProcessingTracker(
            mode=mode,
            job_id=job_id,
            metrics_collector=self.metrics_collector,
            stages=self._get_pipeline_stages(mode)
        )

    def generate_performance_report(self, time_range: tuple) -> PerformanceReport:
        """Generate performance analysis report"""

        metrics = self.performance_db.get_metrics(time_range)

        return PerformanceReport(
            processing_times=self._analyze_processing_times(metrics),
            resource_usage=self._analyze_resource_usage(metrics),
            success_rates=self._calculate_success_rates(metrics),
            bottlenecks=self._identify_bottlenecks(metrics),
            recommendations=self._generate_optimization_recommendations(metrics)
        )
```

---

## Summary

This architecture provides a comprehensive, production-ready system for AI avatar video generation with advanced presentation integration. Key architectural strengths:

1. **Modular Design**: Composable components for flexibility and maintainability
2. **Hardware Optimization**: Specific optimizations for M1 Mac performance
3. **Robust Fallbacks**: Multiple quality levels and graceful degradation
4. **Privacy-First**: Complete local processing with secure file handling
5. **Integration Ready**: Seamless compatibility with existing PresGen infrastructure

The architecture addresses all critical requirements including Google Slides integration, presentation-to-MP4 conversion, video appending pipeline, and three-mode operation system while maintaining professional code quality and production readiness.

**Status**: Architecture Complete - Ready for Implementation
**Next Phase**: Detailed Implementation Plan with step-by-step development roadmap