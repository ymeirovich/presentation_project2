# Phase 5: PresGen-Avatar Video Integration

## Overview
**Phase 5** integrates with PresGen-Avatar (formerly Presgen-Training) for personalized video content generation with AI avatars delivering targeted learning content.

## Core Components

### 1. Avatar Content Generator (`src/services/avatar_content_generator.py`)
```python
class AvatarContentGenerator:
    """Generate personalized avatar video content."""

    async def generate_avatar_script(self, learning_objectives: List[str]) -> Dict:
        """Generate scripts for avatar video content."""

    async def create_personalized_videos(self, user_profile: Dict, content: Dict) -> Dict:
        """Create personalized avatar videos."""
```

### 2. Video Pipeline Manager (`src/services/video_pipeline_manager.py`)
```python
class VideoPipelineManager:
    """Manage video generation pipeline."""

    async def orchestrate_video_creation(self, assessment_results: Dict) -> Dict:
        """Full video creation from assessment to delivery."""
```

## API Endpoints
- `POST /api/v1/avatar/generate-script` - Generate avatar scripts
- `POST /api/v1/avatar/create-video` - Create personalized videos
- `GET /api/v1/avatar/videos/{video_id}/status` - Check video generation status

## Integration Features
- PresGen-Avatar API integration
- Personalized content delivery
- Video quality optimization
- Multi-format video generation

**Phase 5 Status**: ✅ **ARCHITECTURE DEFINED** - Ready for Implementation

## Implementation Roadmap (Detailed)

1. **Script Generation Pipeline**
   - Convert gap analysis outputs into narrative scripts with persona-specific tone, length, and call-to-action blocks.
   - Support modular sections (intro, domain deep dives, remediation tips) enabling reuse in multi-video workflows.
2. **Video Rendering Orchestrator**
   - Integrate with PresGen-Avatar API for TTS, lip-sync/avatar rendering, and compositing slides/audio.
   - Manage queueing, concurrency limits, and progress reporting.
3. **Asset Management**
   - Store rendered video URLs, durations, and caption files; attach to workflow output fields and Drive folders.
4. **Quality Assurance**
   - Analyze rendered videos for duration mismatches, audio clipping, missing captions, and provide automated fixes.
5. **Workflow Integration**
   - Update statuses (`avatar_rendering`, `avatar_videos_generated`) and allow retries per section.

## Test-Driven Development Strategy

1. **Script Generator Tests**
   - TDD transformation logic ensuring scripts respect length limits, persona voice, and include required sections.
2. **API Integration Tests**
   - Mock PresGen-Avatar endpoints to verify request payloads, progress polling, and error handling (timeouts, asset not found).
3. **Video Validation Tests**
   - Build utilities to inspect generated metadata (duration, resolution) and ensure pipeline flags discrepancies.
4. **Workflow Tests**
   - Confirm status transitions and idempotent retries produce consistent outcomes.

## Logging & Observability Enhancements

1. **Pipeline Logs**
   - Log each stage (`script_generate`, `tts_synthesize`, `avatar_render`, `video_publish`) with latency and asset identifiers.
2. **Metrics**
   - Track video generation counts, success/failure ratio, and average render duration.
3. **Alerting**
   - Trigger alerts when render failures exceed thresholds, or when processing time exceeds SLA.
4. **Audit Trail**
   - Maintain mapping between source assessment data and final video assets for traceability.
