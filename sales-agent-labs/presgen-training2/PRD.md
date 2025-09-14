# PresGen-Training2: Product Requirements Document

## Executive Summary

**PresGen-Training2** is an advanced AI-powered avatar video generation system that creates professional presentation videos by combining LivePortrait avatar technology with intelligent content processing and Google Slides integration. The system supports three distinct modes of operation with voice cloning capabilities and seamless integration with existing PresGen infrastructure.

### Mission Statement
Enable rapid creation of professional avatar-based training and presentation videos with automatic content analysis, voice cloning, and flexible presentation options - optimized for speed, quality, and cost-effectiveness.

## Product Overview

### Core Value Proposition
- **AI Avatar Generation**: Realistic avatar videos using LivePortrait technology
- **Voice Cloning**: Clone and save voice profiles for consistent narration
- **Flexible Content Input**: Support both content generation and existing Google Slides
- **Unified Output**: Single MP4 files combining avatar videos with narrated presentations
- **Local-First Processing**: Zero cloud costs, complete privacy control

### Target Use Cases
- **VC Demo Presentations**: Professional investor pitch videos
- **Training Content**: Employee training and onboarding videos
- **Marketing Videos**: Product demonstrations with consistent branding
- **Educational Content**: Course materials with presenter avatars

## Feature Specifications

### 1. Three-Mode Operation System

#### Mode 1: Video-Only
**Purpose**: Generate standalone avatar videos with narration

**Input Options**:
- Upload content files (PDF, DOCX, TXT)
- Direct text input
- Reference video for avatar and voice cloning

**Features**:
- Automatic content summarization into presentation script
- Avatar video generation using LivePortrait
- Voice cloning from reference video with profile saving
- Custom prompt instructions for script customization
- Multi-language support architecture

**Output**: Single MP4 avatar video with narration

**Workflow**:
```
Content Upload → Script Summarization → Voice Cloning → Avatar Generation → MP4 Output
```

#### Mode 2: Presentation-Only
**Purpose**: Generate narrated slideshow videos

**Input Options**:
- **Option A: Generate New Slides**
  - Upload content files → Generate slides via PresGen-Core
  - Auto-generate narration script
- **Option B: Use Existing Google Slides**
  - Paste Google Slides URL
  - Extract slides and Notes section
  - Use Notes as per-slide narration script

**Features**:
- Google Slides API integration
- Notes section extraction for narration timing
- Slide export to high-quality images
- Text-to-speech with saved voice profiles
- Slide timing based on narration length
- Professional video transitions between slides

**Output**: Single MP4 slideshow video with synchronized narration

**Workflow**:
```
Option A: Content Upload → Slide Generation → Narration → Video Composition → MP4
Option B: Google Slides URL → Slides + Notes Extract → Narration → Video Composition → MP4
```

#### Mode 3: Video-Presentation
**Purpose**: Combined avatar introduction + narrated presentation

**Features**:
- Combines Video-Only and Presentation-Only modes
- Consistent voice across both segments
- Seamless video transitions
- Unified timeline and audio synchronization

**Output**: Single MP4 with avatar intro + narrated slideshow

**Workflow**:
```
Content/Slides Input → Avatar Video + Presentation Video → Video Appending → Unified MP4
```

### 2. Voice Cloning System

#### Voice Profile Management
- **Clone from Video**: Extract voice characteristics from uploaded videos
- **Save Profiles**: Named voice profiles for reuse across projects
- **Profile Library**: Manage multiple voice profiles with metadata
- **Quality Levels**: High-quality cloning vs fast processing options

#### Voice Features
- **Multi-Language Support**: Architecture ready for multiple languages
- **Voice Consistency**: Same voice across video and presentation segments
- **Fallback Options**: Open-source TTS when cloning unavailable
- **Export/Import**: Voice profile sharing and backup

#### Technical Implementation
```python
VoiceProfile = {
    "name": "Executive Voice",
    "language": "en",
    "created_at": "2025-01-14",
    "model_path": "voice-models/executive-voice.pt",
    "quality": "high",
    "source_video": "reference-video.mp4"
}
```

### 3. Google Slides Integration

#### URL-Based Access
- **Presentation Import**: Paste Google Slides URL for direct access
- **Notes Extraction**: Parse Notes section for slide-specific narration
- **Slide Export**: High-resolution image export for video composition
- **Access Control**: Support public and service-account accessible presentations

#### Narration Timing
- **Per-Slide Scripts**: Individual narration text from Notes section
- **Timing Calculation**: Slide duration based on narration length
- **Default Timing**: 3-second minimum for slides without notes
- **Transition Effects**: Professional transitions between slides

#### Content Processing
```python
SlideData = {
    "slide_id": "slide_001",
    "slide_order": 1,
    "slide_image": "exports/slide_001.png",
    "notes_text": "Welcome to our company presentation...",
    "narration_audio": "audio/slide_001.wav",
    "duration": 15.3  # seconds
}
```

### 4. Hardware Optimization

#### M1 Mac Support
- **Apple Silicon Optimization**: MPS fallback enabled for LivePortrait
- **Memory Management**: Intelligent memory allocation and cleanup
- **Processing Settings**: Hardware-specific quality and speed settings
- **Thermal Management**: Automatic quality reduction under thermal load

#### Performance Targets
- **M1 Mac Processing Time**: <15 minutes for 1-minute combined video
- **Memory Usage**: <8GB peak usage
- **Quality Options**: Fast (5min) / Standard (10min) / High (15min)
- **Fallback System**: Graceful degradation when resources limited

## Technical Requirements

### 1. Integration Architecture

#### Existing System Integration
- **PresGen-Core**: Leverage slide generation capabilities
- **PresGen-Video**: Reuse video processing infrastructure
- **FastAPI Extension**: Extend existing HTTP service
- **Job Management**: Compatible with existing job system

#### API Endpoints
```python
POST /training/video-only          # Mode 1: Avatar video generation
POST /training/presentation-only   # Mode 2: Slideshow creation
POST /training/video-presentation  # Mode 3: Combined video
POST /training/clone-voice         # Voice cloning from video
GET  /training/voice-profiles      # List saved voice profiles
GET  /training/status/{job_id}     # Job progress monitoring
GET  /training/download/{job_id}   # Download completed video
```

### 2. File Format Specifications

#### Input Formats
- **Content Files**: PDF, DOCX, TXT, MD
- **Reference Videos**: MP4, MOV, AVI (H.264 preferred)
- **Google Slides**: Public URLs or service-account accessible

#### Output Formats
- **Final Videos**: MP4 (H.264, AAC audio)
- **Resolution Options**: 720p (standard), 1080p (high quality)
- **Frame Rate**: 30fps (25fps for fast processing)
- **Audio**: 44.1kHz stereo, 192kbps AAC

### 3. Quality Control System

#### Processing Modes
```yaml
fast:
  resolution: "720p"
  fps: 25
  avatar_quality: "basic"
  enhancement: false
  timeout: "10 minutes"

standard:
  resolution: "720p"
  fps: 30
  avatar_quality: "standard"
  enhancement: false
  timeout: "15 minutes"

high:
  resolution: "1080p"
  fps: 30
  avatar_quality: "high"
  enhancement: true
  timeout: "25 minutes"
```

## User Experience Flow

### 1. Initial Setup
1. **Reference Video Upload**: Provide video for avatar and voice extraction
2. **Voice Profile Creation**: Clone and save voice with custom name
3. **Quality Selection**: Choose processing speed vs quality preference
4. **Test Generation**: Quick validation with short content

### 2. Video-Only Workflow
1. **Content Input**: Upload file or paste text
2. **Script Review**: Review auto-generated script, add custom instructions
3. **Voice Selection**: Choose saved profile or clone new voice
4. **Generation**: Start avatar video creation
5. **Download**: Retrieve completed MP4

### 3. Presentation-Only Workflow
1. **Presentation Source**: Choose generate new OR paste Google Slides URL
2. **Content Processing**:
   - New: Upload content for slide generation
   - Existing: Validate Google Slides access and extract notes
3. **Voice Selection**: Choose saved profile for narration
4. **Preview**: Review slide timing and narration assignments
5. **Generation**: Create narrated slideshow video
6. **Download**: Retrieve completed MP4

### 4. Video-Presentation Workflow
1. **Avatar Setup**: Configure video-only portion
2. **Presentation Setup**: Configure presentation portion
3. **Voice Consistency**: Ensure same voice for both segments
4. **Timeline Review**: Verify smooth transition between segments
5. **Generation**: Create unified video
6. **Download**: Retrieve completed MP4

## User Interface Specifications

### 1. PresGen-UI Tab Integration

#### Tab Addition
- **Tab Name**: "PresGen-Training"
- **Position**: After "PresGen-Video" tab
- **Status**: Enabled by default

#### Main Interface Components
```typescript
<TrainingWorkflow>
  <ModeSelector />           // Three-mode selection
  <ContentUpload />          // File upload or text input
  <GoogleSlidesInput />      // URL input for existing slides
  <VoiceManager />           // Voice cloning and profile selection
  <ProcessingOptions />      // Quality and speed settings
  <ProgressMonitor />        // Real-time job progress
  <ResultsDownload />        // Output video download
</TrainingWorkflow>
```

### 2. Voice Management Interface

#### Voice Profile Dashboard
- **Profile List**: Saved voices with metadata
- **Clone New Voice**: Upload video for voice extraction
- **Test Playback**: Preview voice quality
- **Export/Import**: Profile backup and sharing

#### Voice Cloning Interface
```typescript
<VoiceCloning>
  <VideoUpload />            // Reference video upload
  <ProfileName />            // Custom name for voice
  <LanguageDetection />      // Auto-detect or manual selection
  <QualitySettings />        // Fast vs high-quality cloning
  <CloneProgress />          // Real-time cloning progress
  <ProfilePreview />         // Test generated voice
</VoiceCloning>
```

### 3. Google Slides Interface

#### URL Input Component
```typescript
<GoogleSlidesInput>
  <URLField />               // Google Slides URL input
  <AccessValidation />       // Check presentation accessibility
  <SlidesPreview />          // Preview slides and notes
  <NotesExtraction />        // Show extracted notes per slide
  <TimingPreview />          // Estimated narration timing
</GoogleSlidesInput>
```

## Success Metrics

### Technical Performance
- **Processing Speed**: Target <15 minutes on M1 Mac for 1-minute video
- **Success Rate**: >95% job completion without errors
- **Quality Rating**: Professional output suitable for business use
- **Resource Efficiency**: <8GB RAM peak, <85% CPU sustained

### User Experience
- **Workflow Completion**: <5 clicks from upload to generation start
- **Learning Curve**: New users productive within 10 minutes
- **Error Recovery**: Automatic fallbacks prevent total failures
- **Output Satisfaction**: Professional quality suitable for target use cases

### Business Metrics
- **Cost Efficiency**: $0 marginal cost per video (local processing)
- **Speed Advantage**: 10x faster than manual video creation
- **Quality Consistency**: Repeatable professional results
- **Scalability**: Architecture ready for cloud deployment

## Risk Mitigation

### Technical Risks
| Risk | Probability | Impact | Mitigation |
|------|------------|---------|------------|
| M1 Mac performance insufficient | Medium | High | Multiple quality levels, fallback to fast mode |
| LivePortrait setup complexity | Medium | Medium | Automated installation, Docker option |
| Google Slides API limitations | Low | Medium | Service account setup, fallback to manual export |
| Voice cloning quality issues | Medium | Low | Multiple TTS engines, open-source fallbacks |

### User Experience Risks
| Risk | Probability | Impact | Mitigation |
|------|------------|---------|------------|
| Complex multi-mode interface | Medium | Medium | Progressive disclosure, mode-specific guidance |
| Google Slides URL confusion | High | Low | Clear instructions, validation feedback |
| Voice profile management | Low | Medium | Simple naming, automatic organization |

### Integration Risks
| Risk | Probability | Impact | Mitigation |
|------|------------|---------|------------|
| PresGen infrastructure conflicts | Low | High | Extensive testing, separate job namespacing |
| File format compatibility | Medium | Low | Format validation, automatic conversion |
| API endpoint conflicts | Low | Medium | Careful endpoint naming, versioning |

## Future Enhancements

### Phase 2 Features (Post-MVP)
- **Multi-Language**: Full support for Spanish, French, German, Japanese, Chinese
- **Avatar Customization**: Multiple avatar styles and personalities
- **Advanced Transitions**: Custom video transitions and effects
- **Batch Processing**: Multiple videos in queue
- **Template Library**: Pre-built presentation templates

### Phase 3 Features (Advanced)
- **Real-Time Generation**: Live avatar streaming
- **Interactive Elements**: Clickable areas in presentations
- **Background Replacement**: Custom backgrounds and environments
- **Gesture Library**: Professional presenter gestures
- **Analytics Dashboard**: Usage metrics and optimization insights

## Compliance and Security

### Data Privacy
- **Local Processing**: All content processed locally, never uploaded to cloud
- **Voice Data**: Voice profiles stored locally, user-controlled deletion
- **Google Slides**: Read-only access, no data storage

### Content Security
- **File Encryption**: Temporary files encrypted during processing
- **Access Controls**: Service account permissions for Google Slides
- **Audit Trail**: Processing logs for troubleshooting

## Deployment Specification

### Development Environment
- **Hardware**: M1 Mac with 16GB RAM recommended (8GB minimum)
- **Software**: Python 3.10+, Node.js 18+, FFmpeg, Google Cloud SDK
- **Storage**: 20GB free space for models and temporary files

### Production Considerations
- **Docker Support**: Containerized deployment option
- **Cloud Scaling**: Architecture ready for cloud deployment
- **Load Balancing**: Multiple processing nodes for high volume
- **Monitoring**: Health checks and performance metrics

---

## Appendix: Technical Specifications

### Voice Cloning Models
- **Primary**: Coqui TTS with voice cloning
- **Fallback**: TortoiseTS for high-quality cloning
- **Fast Option**: OpenSource TTS for quick processing

### Video Processing Pipeline
```yaml
Avatar_Generation:
  Engine: LivePortrait
  Input: Reference image + audio
  Output: MP4 avatar video

Presentation_Generation:
  Engine: Custom slides-to-video
  Input: Slides + narration timing
  Output: MP4 slideshow video

Video_Appending:
  Engine: FFmpeg
  Input: Multiple MP4 files
  Output: Single concatenated MP4
```

### File Structure
```
presgen-training2/
├── PRD.md                    # This document
├── Architecture.md           # Technical architecture
├── Implementation-Plan.md    # Development roadmap
├── src/                     # Source code
├── config/                  # Configuration files
├── models/                  # AI model files (gitignored)
└── examples/                # Test assets and demos
```

**Status**: Ready for Implementation
**Timeline**: 4 weeks MVP → Production Ready
**Owner**: Development Team