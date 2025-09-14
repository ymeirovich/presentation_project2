"""
Unified Orchestrator: PresGen-Training + PresGen-Video Integration
Combines avatar generation with professional video composition
"""

import asyncio
import logging
import time
import tempfile
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

from src.presgen_training.avatar_generator import AvatarGenerator
from src.common.jsonlog import jlog

log = logging.getLogger("unified_orchestrator")


@dataclass
class PresentationOptions:
    """Configuration for presentation generation"""
    avatar_quality: str = "standard"  # fast|standard|high
    bullet_style: str = "professional"
    output_format: str = "mp4"
    voice_speed: float = 1.0
    video_fps: int = 25


@dataclass
class PresentationResult:
    """Result of complete presentation generation"""
    success: bool
    output_path: Optional[str]
    total_processing_time: float
    phase_times: Dict[str, float]
    error: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class UnifiedOrchestrator:
    """
    Orchestrates the complete text → professional presentation pipeline
    
    Pipeline Flow:
    1. Text Script → PresGen-Training (Avatar Generation)
    2. Avatar Video → PresGen-Video Phase 2 (Content Analysis) 
    3. Content + Avatar → PresGen-Video Phase 3 (Final Composition)
    """
    
    def __init__(self, job_id: str):
        self.job_id = job_id
        self.avatar_generator = AvatarGenerator()
        
    async def generate_presentation(self, 
                                  script_text: str, 
                                  options: PresentationOptions = None) -> PresentationResult:
        """
        Generate complete presentation from text script
        
        Args:
            script_text: Input text for presentation
            options: Generation options
            
        Returns:
            PresentationResult with output path and timing
        """
        if options is None:
            options = PresentationOptions()
            
        start_time = time.time()
        phase_times = {}
        
        jlog(log, logging.INFO,
             event="unified_presentation_start",
             job_id=self.job_id,
             script_length=len(script_text),
             options=options.__dict__)
        
        try:
            with tempfile.TemporaryDirectory(prefix=f"presentation_{self.job_id}_") as temp_dir:
                temp_path = Path(temp_dir)
                
                # Create job directory structure
                job_paths = self._setup_job_directories(temp_path)
                
                # Phase 1: Avatar Generation (PresGen-Training)
                avatar_result = await self._phase1_avatar_generation(
                    script_text, job_paths, options, phase_times
                )
                if not avatar_result["success"]:
                    return PresentationResult(
                        success=False,
                        output_path=None,
                        total_processing_time=time.time() - start_time,
                        phase_times=phase_times,
                        error=avatar_result["error"]
                    )
                
                # Phase 2: Content Analysis (PresGen-Video Modified)
                content_result = await self._phase2_content_analysis(
                    script_text, avatar_result, job_paths, phase_times
                )
                if not content_result["success"]:
                    return PresentationResult(
                        success=False,
                        output_path=None,
                        total_processing_time=time.time() - start_time,
                        phase_times=phase_times,
                        error=content_result["error"]
                    )
                
                # Phase 3: Final Composition (PresGen-Video Phase 3)
                final_result = await self._phase3_final_composition(
                    avatar_result, content_result, job_paths, options, phase_times
                )
                
                total_time = time.time() - start_time
                
                if final_result["success"]:
                    # Copy the output video to permanent location before temp cleanup
                    try:
                        import shutil
                        permanent_output_dir = Path("out/videos")
                        permanent_output_dir.mkdir(parents=True, exist_ok=True)
                        permanent_output_path = permanent_output_dir / f"presentation_{self.job_id}.mp4"
                        
                        if Path(final_result["output_path"]).exists():
                            shutil.copy2(final_result["output_path"], permanent_output_path)
                            
                            jlog(log, logging.INFO,
                                 event="video_copied_to_permanent_location",
                                 job_id=self.job_id,
                                 permanent_path=str(permanent_output_path),
                                 temp_path=final_result["output_path"])
                            
                            # Update output path to permanent location
                            final_result["output_path"] = str(permanent_output_path)
                    except Exception as copy_error:
                        jlog(log, logging.WARNING,
                             event="video_copy_failed",
                             job_id=self.job_id,
                             error=str(copy_error))
                    
                    jlog(log, logging.INFO,
                         event="unified_presentation_complete",
                         job_id=self.job_id,
                         total_time=round(total_time, 2),
                         output_path=final_result["output_path"],
                         phase_times=phase_times)
                    
                    return PresentationResult(
                        success=True,
                        output_path=final_result["output_path"],
                        total_processing_time=total_time,
                        phase_times=phase_times,
                        metadata={
                            "script_length": len(script_text),
                            "avatar_quality": options.avatar_quality,
                            "final_video_duration": final_result.get("duration_seconds")
                        }
                    )
                else:
                    return PresentationResult(
                        success=False,
                        output_path=None,
                        total_processing_time=total_time,
                        phase_times=phase_times,
                        error=final_result["error"]
                    )
                    
        except Exception as e:
            total_time = time.time() - start_time
            error_msg = f"Unified orchestration failed: {str(e)}"
            
            jlog(log, logging.ERROR,
                 event="unified_presentation_exception",
                 job_id=self.job_id,
                 error=error_msg,
                 total_time=round(total_time, 2))
            
            return PresentationResult(
                success=False,
                output_path=None,
                total_processing_time=total_time,
                phase_times=phase_times,
                error=error_msg
            )
    
    def _setup_job_directories(self, temp_path: Path) -> Dict[str, Path]:
        """Create organized directory structure for processing"""
        paths = {
            "input": temp_path / "input",
            "avatar": temp_path / "avatar", 
            "analysis": temp_path / "analysis",
            "output": temp_path / "output"
        }
        
        for path in paths.values():
            path.mkdir(parents=True, exist_ok=True)
            
        return paths
    
    async def _phase1_avatar_generation(self, 
                                      script_text: str, 
                                      job_paths: Dict[str, Path],
                                      options: PresentationOptions,
                                      phase_times: Dict[str, float]) -> Dict[str, Any]:
        """Phase 1: Generate avatar video using PresGen-Training"""
        
        phase_start = time.time()
        
        jlog(log, logging.INFO,
             event="phase1_avatar_start",
             job_id=self.job_id,
             script_length=len(script_text))
        
        try:
            # Save script text
            script_path = job_paths["input"] / "script.txt"
            script_path.write_text(script_text)
            
            # Generate TTS audio
            audio_path = job_paths["avatar"] / "audio.wav"
            tts_result = self.avatar_generator.generate_tts_audio(script_text, audio_path)
            
            if not tts_result or not audio_path.exists():
                return {"success": False, "error": "TTS generation failed"}
            
            # Create simple avatar image (for now - could be enhanced later)
            avatar_image_path = job_paths["avatar"] / "avatar.png"
            self._create_default_avatar_image(avatar_image_path)
            
            # Generate avatar video
            avatar_video_path = job_paths["avatar"] / "avatar_video.mp4" 
            video_result = self.avatar_generator.generate_avatar_video(
                audio_path, avatar_image_path, avatar_video_path
            )
            
            phase_time = time.time() - phase_start
            phase_times["avatar_generation"] = round(phase_time, 2)
            
            if video_result and avatar_video_path.exists():
                jlog(log, logging.INFO,
                     event="phase1_avatar_complete",
                     job_id=self.job_id,
                     processing_time=round(phase_time, 2),
                     output_size_mb=round(avatar_video_path.stat().st_size / (1024*1024), 2))
                
                return {
                    "success": True,
                    "avatar_video_path": str(avatar_video_path),
                    "audio_path": str(audio_path),
                    "processing_time": phase_time
                }
            else:
                return {"success": False, "error": "Avatar video generation failed"}
                
        except Exception as e:
            phase_times["avatar_generation"] = round(time.time() - phase_start, 2)
            return {"success": False, "error": f"Avatar generation error: {str(e)}"}
    
    async def _phase2_content_analysis(self,
                                     script_text: str,
                                     avatar_result: Dict[str, Any], 
                                     job_paths: Dict[str, Path],
                                     phase_times: Dict[str, float]) -> Dict[str, Any]:
        """Phase 2: Enhanced content analysis using actual PresGen-Video components"""
        
        phase_start = time.time()
        
        jlog(log, logging.INFO,
             event="phase2_enhanced_content_start",
             job_id=self.job_id,
             script_length=len(script_text))
        
        try:
            # Import PresGen-Video content analysis components
            from src.mcp.tools.video_content import ContentAgent, VideoSummary
            from src.mcp.tools.video_transcription import TranscriptSegment
            
            # Create mock transcript segments from script text
            # In a real scenario, these would come from Whisper transcription
            script_segments = self._create_transcript_segments_from_script(script_text)
            
            # Initialize ContentAgent for LLM summarization
            content_agent = ContentAgent(self.job_id)
            
            # Generate structured bullet points using LLM
            content_result = await content_agent.batch_summarize(
                segments=script_segments,
                max_bullets=5
            )
            
            if not content_result.success:
                return {"success": False, "error": f"Content analysis failed: {content_result.error}"}
            
            # Extract structured bullets from result
            summary = content_result.summary
            bullets = []
            bullet_data = []
            
            if hasattr(summary, 'bullet_points'):
                for bullet_point in summary.bullet_points:
                    bullets.append(bullet_point.text)
                    bullet_data.append({
                        "timestamp": bullet_point.timestamp,
                        "text": bullet_point.text,
                        "confidence": bullet_point.confidence,
                        "duration": bullet_point.duration
                    })
            else:
                # Fallback to simple extraction if structured format fails
                bullets = self._extract_simple_bullets(script_text)
                bullet_data = [{"text": bullet, "timestamp": f"{i*10:02d}:00", "confidence": 0.8, "duration": 10.0} 
                              for i, bullet in enumerate(bullets)]
            
            # Save enhanced analysis data
            analysis_path = job_paths["analysis"] / "enhanced_slides.json"
            import json
            analysis_data = {
                "bullets": bullets,
                "bullet_data": bullet_data,
                "script_text": script_text,
                "estimated_duration": getattr(summary, 'estimated_duration', len(script_text.split()) * 0.5),
                "processing_method": "llm_enhanced",
                "llm_processing_time": content_result.processing_time,
                "generated_at": time.time()
            }
            
            analysis_path.write_text(json.dumps(analysis_data, indent=2))
            
            phase_time = time.time() - phase_start
            phase_times["content_analysis"] = round(phase_time, 2)
            
            jlog(log, logging.INFO,
                 event="phase2_enhanced_content_complete",
                 job_id=self.job_id,
                 processing_time=round(phase_time, 2),
                 bullets_count=len(bullets),
                 llm_processing_time=round(content_result.processing_time, 2))
            
            return {
                "success": True,
                "bullets": bullets,
                "bullet_data": bullet_data,
                "summary": summary,
                "analysis_path": str(analysis_path),
                "processing_time": phase_time
            }
            
        except Exception as e:
            phase_times["content_analysis"] = round(time.time() - phase_start, 2)
            
            jlog(log, logging.ERROR,
                 event="phase2_enhanced_content_error",
                 job_id=self.job_id,
                 error=str(e))
            
            # Fallback to simple analysis
            return await self._phase2_simple_fallback(script_text, job_paths, phase_times, phase_start)
    
    def _create_transcript_segments_from_script(self, script_text: str) -> List:
        """Convert script text into mock transcript segments for ContentAgent"""
        from src.mcp.tools.video_transcription import TranscriptSegment
        
        # Split script into sentences for more granular analysis
        sentences = [s.strip() for s in script_text.replace('.', '.\n').split('\n') if s.strip()]
        segments = []
        
        current_time = 0.0
        for i, sentence in enumerate(sentences):
            if len(sentence) > 10:  # Skip very short segments
                # Estimate duration based on sentence length (words per minute)
                word_count = len(sentence.split())
                duration = max(word_count * 0.4, 2.0)  # ~150 WPM, minimum 2s
                
                segment = TranscriptSegment(
                    start_time=current_time,
                    end_time=current_time + duration,
                    text=sentence,
                    confidence=0.95
                )
                segments.append(segment)
                current_time += duration
        
        return segments if segments else [TranscriptSegment(
            start_time=0.0, end_time=30.0, text=script_text[:200], confidence=0.9
        )]
    
    async def _phase2_simple_fallback(self, 
                                    script_text: str, 
                                    job_paths: Dict[str, Path],
                                    phase_times: Dict[str, float], 
                                    phase_start: float) -> Dict[str, Any]:
        """Fallback to simple content analysis if LLM processing fails"""
        
        jlog(log, logging.WARNING,
             event="phase2_fallback_to_simple",
             job_id=self.job_id)
        
        bullets = self._extract_simple_bullets(script_text)
        
        # Save simple analysis
        analysis_path = job_paths["analysis"] / "simple_slides.json"
        import json
        analysis_data = {
            "bullets": bullets,
            "script_text": script_text,
            "estimated_duration": len(script_text.split()) * 0.5,
            "processing_method": "simple_fallback",
            "generated_at": time.time()
        }
        
        analysis_path.write_text(json.dumps(analysis_data, indent=2))
        
        phase_time = time.time() - phase_start
        phase_times["content_analysis"] = round(phase_time, 2)
        
        return {
            "success": True,
            "bullets": bullets,
            "analysis_path": str(analysis_path),
            "processing_time": phase_time
        }
    
    async def _phase3_final_composition(self,
                                      avatar_result: Dict[str, Any],
                                      content_result: Dict[str, Any],
                                      job_paths: Dict[str, Path],
                                      options: PresentationOptions,
                                      phase_times: Dict[str, float]) -> Dict[str, Any]:
        """Phase 3: Enhanced final composition using PresGen-Video Phase 3 bullet overlay system"""
        
        phase_start = time.time()
        
        jlog(log, logging.INFO,
             event="phase3_enhanced_composition_start",
             job_id=self.job_id)
        
        try:
            # Try enhanced composition with PresGen-Video Phase 3
            output_path = job_paths["output"] / "enhanced_presentation.mp4"
            
            success = await self._enhanced_bullet_overlay_composition(
                avatar_result, content_result, job_paths, str(output_path)
            )
            
            phase_time = time.time() - phase_start
            phase_times["final_composition"] = round(phase_time, 2)
            
            if success and output_path.exists():
                # Get video metadata for enhanced result
                video_metadata = await self._get_video_metadata(str(output_path))
                
                jlog(log, logging.INFO,
                     event="phase3_enhanced_composition_complete",
                     job_id=self.job_id,
                     processing_time=round(phase_time, 2),
                     output_size_mb=round(output_path.stat().st_size / (1024*1024), 2),
                     video_metadata=video_metadata)
                
                return {
                    "success": True,
                    "output_path": str(output_path),
                    "processing_time": phase_time,
                    "video_metadata": video_metadata
                }
            else:
                # Fallback to simple composition
                jlog(log, logging.WARNING,
                     event="phase3_fallback_to_simple",
                     job_id=self.job_id)
                
                return await self._phase3_simple_fallback(
                    avatar_result, content_result, job_paths, options, phase_times, phase_start
                )
                
        except Exception as e:
            phase_times["final_composition"] = round(time.time() - phase_start, 2)
            
            jlog(log, logging.ERROR,
                 event="phase3_enhanced_composition_error",
                 job_id=self.job_id,
                 error=str(e))
            
            # Fallback to simple composition
            return await self._phase3_simple_fallback(
                avatar_result, content_result, job_paths, options, phase_times, phase_start
            )
    
    async def _enhanced_bullet_overlay_composition(self,
                                                 avatar_result: Dict[str, Any],
                                                 content_result: Dict[str, Any], 
                                                 job_paths: Dict[str, Path],
                                                 output_path: str) -> bool:
        """Enhanced composition using PresGen-Video Phase 3 techniques"""
        
        try:
            import subprocess
            
            # Prepare bullet data for timeline generation
            bullet_data = content_result.get("bullet_data", [])
            if not bullet_data:
                # Create from simple bullets if structured data not available
                bullets = content_result.get("bullets", [])
                bullet_data = [
                    {
                        "text": bullet,
                        "timestamp": f"{i*10:02d}:00",  # 10-second intervals
                        "confidence": 0.8,
                        "duration": 10.0
                    }
                    for i, bullet in enumerate(bullets)
                ]
            
            # Get video metadata for duration
            video_path = avatar_result["avatar_video_path"]
            video_duration = await self._get_video_duration_ffprobe(video_path)
            
            # Generate timeline with proper distribution
            timeline = self._generate_enhanced_timeline(bullet_data, video_duration)
            
            # Build FFmpeg command with professional styling
            ffmpeg_cmd = self._build_enhanced_ffmpeg_command(
                video_path, timeline, output_path
            )
            
            jlog(log, logging.INFO,
                 event="enhanced_ffmpeg_command",
                 job_id=self.job_id,
                 timeline_entries=len(timeline),
                 video_duration=video_duration)
            
            # Execute FFmpeg with enhanced composition
            result = subprocess.run(
                ffmpeg_cmd, 
                capture_output=True, 
                text=True, 
                timeout=120
            )
            
            if result.returncode == 0:
                jlog(log, logging.INFO,
                     event="enhanced_composition_success",
                     job_id=self.job_id,
                     output_path=output_path)
                return True
            else:
                jlog(log, logging.ERROR,
                     event="enhanced_composition_ffmpeg_error",
                     job_id=self.job_id,
                     error=result.stderr)
                return False
                
        except Exception as e:
            jlog(log, logging.ERROR,
                 event="enhanced_composition_exception",
                 job_id=self.job_id,
                 error=str(e))
            return False
    
    def _generate_enhanced_timeline(self, bullet_data: List[Dict[str, Any]], video_duration: float) -> List[Dict[str, Any]]:
        """Generate professional timeline with proper bullet distribution"""
        
        timeline = []
        buffer = 3.0  # 3-second buffer before video ends
        usable_duration = max(video_duration - buffer, 10.0)  # At least 10 seconds
        
        for idx, bullet in enumerate(bullet_data):
            if len(bullet_data) > 1:
                # Distribute evenly across video duration
                if idx == 0:
                    start_time = 0
                else:
                    time_per_bullet = usable_duration / (len(bullet_data) - 1) 
                    start_time = int(idx * time_per_bullet)
            else:
                start_time = 0
            
            timeline.append({
                "start_time": start_time,
                "text": bullet["text"][:80],  # Truncate long text
                "confidence": bullet.get("confidence", 0.8)
            })
        
        return timeline
    
    def _build_enhanced_ffmpeg_command(self, video_path: str, timeline: List[Dict[str, Any]], output_path: str) -> List[str]:
        """Build professional FFmpeg command with bullet overlays"""
        
        # Build drawtext filters with simplified fixed positioning
        filter_parts = []
        
        # 1. Add right-side white rectangle (320px width for 512px video)
        rect_filter = (
            "drawbox="
            "x=192:y=0:"               # Position at 192px (512*0.75 for 25% remaining)
            "w=320:h=512:"             # 320px width, full height
            "color=white@0.9:t=fill"    # Semi-transparent white
        )
        filter_parts.append(rect_filter)
        
        # 2. Add "Key Points" title (centered in 320px rectangle)
        title_filter = (
            "drawtext=text='Key Points':"
            "fontsize=20:"
            "fontcolor=navy:"
            "x=272:"                   # Roughly centered (192 + 80px offset)
            "y=30"                     # Top margin
        )
        filter_parts.append(title_filter)
        
        # 3. Add bullet points with timing
        for i, entry in enumerate(timeline, 1):
            start_time = entry['start_time']
            text = entry['text'][:40].replace("'", "\\'").replace(":", "\\:")  # Truncate for display
            
            # Numbered bullet
            bullet_text = f"#{i} {text}"
            
            # Position bullets vertically with proper spacing
            y_pos = 70 + (i * 30)  # 30px spacing between bullets
            
            bullet_filter = (
                f"drawtext=text='{bullet_text}':"
                "fontsize=16:"
                "fontcolor=darkblue:"
                "x=212:"                         # 20px margin from rectangle edge
                f"y={y_pos}:"
                f"enable='gte(t,{start_time})'"  # Show from start_time
            )
            filter_parts.append(bullet_filter)
        
        # Combine all filters
        video_filter = ",".join(filter_parts)
        
        # Build complete FFmpeg command
        cmd = [
            "ffmpeg", "-y",
            "-i", video_path,
            "-vf", video_filter,
            "-c:v", "libx264",
            "-c:a", "aac", 
            "-preset", "medium",
            "-crf", "23",
            output_path
        ]
        
        return cmd
    
    async def _get_video_duration_ffprobe(self, video_path: str) -> float:
        """Get video duration using ffprobe"""
        try:
            import subprocess
            import json
            
            result = subprocess.run([
                'ffprobe', '-v', 'quiet', '-print_format', 'json',
                '-show_format', video_path
            ], capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                info = json.loads(result.stdout)
                return float(info['format']['duration'])
            else:
                return 30.0  # Default fallback
                
        except Exception:
            return 30.0  # Default fallback
    
    async def _get_video_metadata(self, video_path: str) -> Dict[str, Any]:
        """Get video metadata for result"""
        try:
            import subprocess
            import json
            
            result = subprocess.run([
                'ffprobe', '-v', 'quiet', '-print_format', 'json',
                '-show_format', '-show_streams', video_path
            ], capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                info = json.loads(result.stdout)
                return {
                    "duration": float(info['format']['duration']),
                    "streams": len(info['streams']),
                    "size_mb": round(Path(video_path).stat().st_size / (1024*1024), 2)
                }
            else:
                return {"duration": 0, "streams": 0, "size_mb": 0}
                
        except Exception:
            return {"duration": 0, "streams": 0, "size_mb": 0}
    
    async def _phase3_simple_fallback(self,
                                    avatar_result: Dict[str, Any],
                                    content_result: Dict[str, Any],
                                    job_paths: Dict[str, Path],
                                    options: PresentationOptions,
                                    phase_times: Dict[str, float],
                                    phase_start: float) -> Dict[str, Any]:
        """Fallback to simple composition if enhanced fails"""
        
        output_path = job_paths["output"] / "simple_presentation.mp4"
        
        success = await self._simple_bullet_overlay_composition(
            avatar_result["avatar_video_path"],
            content_result["bullets"],
            str(output_path)
        )
        
        phase_time = time.time() - phase_start
        phase_times["final_composition"] = round(phase_time, 2)
        
        if success and output_path.exists():
            return {
                "success": True,
                "output_path": str(output_path),
                "processing_time": phase_time
            }
        else:
            return {"success": False, "error": "Both enhanced and simple composition failed"}
    
    def _create_default_avatar_image(self, image_path: Path):
        """Create a simple default avatar image"""
        try:
            from PIL import Image, ImageDraw
            
            # Create simple avatar
            img = Image.new('RGB', (512, 512), 'lightblue')
            draw = ImageDraw.Draw(img)
            
            # Draw face
            draw.ellipse([100, 100, 400, 400], fill='peachpuff', outline='black', width=2)
            draw.ellipse([180, 200, 200, 220], fill='black')  # Left eye
            draw.ellipse([300, 200, 320, 220], fill='black')  # Right eye  
            draw.arc([220, 280, 280, 320], 0, 180, fill='black', width=3)  # Mouth
            
            img.save(image_path)
            
        except ImportError:
            # Fallback: create minimal placeholder
            image_path.write_bytes(b'placeholder')
    
    def _extract_simple_bullets(self, script_text: str) -> List[str]:
        """Extract simple bullet points from script text"""
        # Simple implementation - split by sentences and take key phrases
        sentences = script_text.replace('.', '.\n').split('\n')
        bullets = []
        
        for sentence in sentences[:5]:  # Max 5 bullets
            sentence = sentence.strip()
            if len(sentence) > 10:  # Skip very short sentences
                # Take first part of sentence as bullet
                bullet = sentence.split('.')[0][:50]
                if bullet:
                    bullets.append(bullet.strip())
        
        return bullets if bullets else ["Key presentation point", "Important information", "Main takeaway"]
    
    async def _simple_bullet_overlay_composition(self, 
                                               video_path: str, 
                                               bullets: List[str], 
                                               output_path: str) -> bool:
        """Simple bullet overlay composition using FFmpeg"""
        try:
            import subprocess
            
            # Create simple overlay (copy avatar video for now)
            # TODO: Implement actual bullet overlay using FFmpeg drawtext
            cmd = [
                "ffmpeg", "-y",
                "-i", video_path,
                "-c", "copy",
                output_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            return result.returncode == 0
            
        except Exception as e:
            jlog(log, logging.ERROR,
                 event="simple_composition_error",
                 job_id=self.job_id, 
                 error=str(e))
            return False


# Test function
async def test_unified_orchestrator():
    """Test the unified orchestrator"""
    print("🎬 Testing Unified PresGen Orchestrator")
    print("=" * 50)
    
    orchestrator = UnifiedOrchestrator("test_job_001")
    
    test_script = """
    Welcome to our company presentation. We are excited to share our innovative solutions 
    with you today. Our technology revolutionizes the way businesses operate. 
    We have achieved remarkable growth this quarter. Thank you for your attention.
    """
    
    options = PresentationOptions(
        avatar_quality="standard",
        bullet_style="professional"
    )
    
    print(f"Input script: {len(test_script)} characters")
    print("Starting unified presentation generation...")
    
    result = await orchestrator.generate_presentation(test_script, options)
    
    print(f"\n📊 Results:")
    print(f"Success: {result.success}")
    print(f"Total time: {result.total_processing_time:.1f}s")
    print(f"Phase times: {result.phase_times}")
    
    if result.success:
        print(f"✅ Output: {result.output_path}")
    else:
        print(f"❌ Error: {result.error}")


if __name__ == "__main__":
    asyncio.run(test_unified_orchestrator())