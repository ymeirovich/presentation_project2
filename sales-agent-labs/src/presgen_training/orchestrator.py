"""
PresGen-Training Orchestrator

Core orchestration logic for avatar-based training video generation.
Coordinates hardware profiling, avatar generation, and presgen-video integration.
"""

import json
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
import uuid
import subprocess
import sys
import os

from src.common.jsonlog import jlog
from src.presgen_training.hardware_profiler import HardwareProfiler, ResourceMonitor
from src.presgen_training.avatar_generator import AvatarGenerator
from src.presgen_training.video_utils import VideoUtils


class TrainingVideoOrchestrator:
    """
    Main orchestrator for training video generation pipeline.
    
    Coordinates the complete flow:
    1. Hardware validation and resource monitoring
    2. Avatar video generation from script + source video  
    3. Integration with PresGen-Video pipeline for bullet point overlays
    """
    
    def __init__(
        self, 
        quality: str = "standard",
        skip_hardware_check: bool = False,
        output_dir: Path = Path("presgen-training/outputs"),
        logger: Optional[logging.Logger] = None
    ):
        self.quality = quality
        self.skip_hardware_check = skip_hardware_check
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Setup logging
        self.logger = logger or logging.getLogger("presgen_training.orchestrator")
        
        # Initialize components
        self.hardware_profiler = HardwareProfiler(logger=self.logger)
        self.resource_monitor = ResourceMonitor(logger=self.logger)
        self.avatar_generator = AvatarGenerator(quality=quality, logger=self.logger)
        self.video_utils = VideoUtils(logger=self.logger)
        
        # State tracking
        self.job_id = str(uuid.uuid4())
        self.start_time = None
        self.hardware_profile = None
        
        jlog(self.logger, logging.INFO,
             event="orchestrator_init",
             job_id=self.job_id,
             quality=quality,
             output_dir=str(output_dir),
             skip_hardware_check=skip_hardware_check)

    def create_processing_plan(
        self, 
        script_path: Path, 
        source_video_path: Path
    ) -> List[Dict[str, Any]]:
        """Create detailed processing plan for dry-run mode"""
        
        plan = [
            {
                "phase": "1.1 Hardware Validation",
                "description": "Profile system capabilities and validate requirements",
                "duration_mins": 1,
                "skip": self.skip_hardware_check
            },
            {
                "phase": "1.2 Resource Monitoring",
                "description": "Start real-time resource monitoring",
                "duration_mins": 0.5,
                "skip": False
            },
            {
                "phase": "2.1 Script Processing", 
                "description": "Parse script and generate TTS audio",
                "duration_mins": 2,
                "skip": False
            },
            {
                "phase": "2.2 Frame Extraction",
                "description": "Extract presenter frames from source video", 
                "duration_mins": 1,
                "skip": False
            },
            {
                "phase": "3.1 Avatar Generation",
                "description": f"Generate avatar video using SadTalker ({self.quality} quality)",
                "duration_mins": self._estimate_avatar_duration(),
                "skip": False
            },
            {
                "phase": "4.1 PresGen-Video Integration",
                "description": "Process through PresGen-Video for bullet point overlays",
                "duration_mins": 3,
                "skip": False
            },
            {
                "phase": "4.2 Final Composition",
                "description": "Combine avatar video with generated overlays",
                "duration_mins": 2,
                "skip": False
            }
        ]
        
        return [step for step in plan if not step["skip"]]
        
    def _estimate_avatar_duration(self) -> int:
        """Estimate avatar generation time based on quality setting"""
        durations = {
            "fast": 5,      # Low quality, optimized for speed
            "standard": 15,  # Balanced quality/speed
            "high": 45      # High quality, slower processing
        }
        return durations.get(self.quality, 15)

    def process_training_video(
        self,
        script_path: Path,
        source_video_path: Path
    ) -> Dict[str, Any]:
        """
        Main processing pipeline for training video generation.
        
        Returns:
            Dict with success status, output paths, and processing metrics
        """
        self.start_time = time.time()
        
        jlog(self.logger, logging.INFO,
             event="training_video_processing_start",
             job_id=self.job_id,
             script_path=str(script_path),
             source_video_path=str(source_video_path),
             quality=self.quality)
        
        try:
            # Phase 1: Hardware Validation & Monitoring
            if not self._phase1_hardware_setup():
                return self._error_result("Hardware validation failed")
            
            # Phase 2: Content Preparation
            script_content, audio_path = self._phase2_script_processing(script_path, source_video_path)
            if not audio_path:
                return self._error_result("Script processing failed")
                
            presenter_frame = self._phase2_frame_extraction(source_video_path)
            if not presenter_frame:
                return self._error_result("Frame extraction failed")
            
            # Phase 3: Avatar Generation  
            avatar_video_path = self._phase3_avatar_generation(
                audio_path, presenter_frame, script_content
            )
            if not avatar_video_path:
                return self._error_result("Avatar generation failed")
            
            # Phase 4: PresGen-Video Integration
            final_video_path = self._phase4_presgen_integration(
                avatar_video_path, script_content
            )
            if not final_video_path:
                return self._error_result("PresGen-Video integration failed")
            
            # Success - compile results
            processing_time = time.time() - self.start_time
            
            result = {
                "success": True,
                "job_id": self.job_id,
                "output_video": str(final_video_path),
                "avatar_video": str(avatar_video_path),
                "processing_time": processing_time,
                "avatar_frames": self._count_video_frames(avatar_video_path),
                "bullet_points": self._extract_bullet_points(script_content),
                "hardware_profile": self.hardware_profile.to_dict() if self.hardware_profile else None,
                "quality_used": self.quality
            }
            
            jlog(self.logger, logging.INFO,
                 event="training_video_processing_success", 
                 **result)
            
            return result
            
        except Exception as e:
            jlog(self.logger, logging.ERROR,
                 event="training_video_processing_exception",
                 job_id=self.job_id,
                 error=str(e),
                 error_type=type(e).__name__)
            
            return self._error_result(f"Processing exception: {e}")
        
        finally:
            # Always stop resource monitoring
            if hasattr(self, 'resource_monitor'):
                self.resource_monitor.stop_monitoring()

    def _phase1_hardware_setup(self) -> bool:
        """Phase 1: Hardware validation and resource monitoring setup"""
        jlog(self.logger, logging.INFO,
             event="phase1_hardware_setup_start",
             job_id=self.job_id)
        
        if not self.skip_hardware_check:
            # Hardware profiling
            self.hardware_profile = self.hardware_profiler.detect_hardware()
            
            if not self.hardware_profiler.validate_requirements(self.hardware_profile):
                jlog(self.logger, logging.ERROR,
                     event="hardware_validation_failed",
                     profile=self.hardware_profile.__dict__)
                return False
                
            # Auto-adjust quality based on hardware
            recommended_quality = self.hardware_profiler.recommend_quality(self.hardware_profile)
            if recommended_quality != self.quality:
                jlog(self.logger, logging.WARNING,
                     event="quality_auto_adjustment", 
                     original=self.quality,
                     recommended=recommended_quality)
                self.quality = recommended_quality
                self.avatar_generator.quality = recommended_quality
        
        # Start resource monitoring
        self.resource_monitor.start_monitoring()
        
        jlog(self.logger, logging.INFO,
             event="phase1_hardware_setup_complete",
             hardware_profile=self.hardware_profile.__dict__ if self.hardware_profile else None,
             final_quality=self.quality)
        
        return True

    def _phase2_script_processing(self, script_path: Path, source_video_path: Path) -> tuple[str, Optional[Path]]:
        """Phase 2.1: Process script and generate voice-cloned audio"""
        jlog(self.logger, logging.INFO,
             event="phase2_script_processing_start",
             job_id=self.job_id,
             script_path=str(script_path),
             source_video_path=str(source_video_path))
        
        # Read script content
        try:
            script_content = script_path.read_text().strip()
            word_count = len(script_content.split())
            
            jlog(self.logger, logging.INFO,
                 event="script_content_loaded",
                 word_count=word_count,
                 char_count=len(script_content))
                 
        except Exception as e:
            jlog(self.logger, logging.ERROR,
                 event="script_reading_failed",
                 error=str(e))
            return "", None
        
        # Generate voice-cloned audio using avatar generator (with source video as voice reference)
        audio_path = self.avatar_generator.generate_tts_audio(
            text=script_content, 
            output_path=self.output_dir / f"tts_audio_{self.job_id}.wav",
            reference_video_path=source_video_path  # Enable voice cloning
        )
        
        if audio_path:
            jlog(self.logger, logging.INFO,
                 event="phase2_script_processing_complete",
                 audio_path=str(audio_path),
                 audio_duration=self.video_utils.get_audio_duration(audio_path),
                 voice_cloning_attempted=True)
        
        return script_content, audio_path

    def _phase2_frame_extraction(self, source_video_path: Path) -> Optional[Path]:
        """Phase 2.2: Extract presenter frame from source video"""
        jlog(self.logger, logging.INFO,
             event="phase2_frame_extraction_start",
             job_id=self.job_id,
             source_video=str(source_video_path))
        
        # Extract best presenter frame
        frame_path = self.video_utils.extract_best_presenter_frame(
            source_video_path,
            self.output_dir / f"presenter_frame_{self.job_id}.jpg"
        )
        
        if frame_path:
            jlog(self.logger, logging.INFO,
                 event="phase2_frame_extraction_complete",
                 frame_path=str(frame_path),
                 frame_size_bytes=frame_path.stat().st_size)
        
        return frame_path

    def _phase3_avatar_generation(
        self, 
        audio_path: Path, 
        presenter_frame: Path, 
        script_content: str
    ) -> Optional[Path]:
        """Phase 3: Generate avatar video using SadTalker"""
        jlog(self.logger, logging.INFO,
             event="phase3_avatar_generation_start",
             job_id=self.job_id,
             quality=self.quality,
             audio_path=str(audio_path),
             presenter_frame=str(presenter_frame))
        
        avatar_video_path = self.output_dir / f"avatar_video_{self.job_id}.mp4"
        
        success = self.avatar_generator.generate_avatar_video(
            audio_path=audio_path,
            image_path=presenter_frame,
            output_path=avatar_video_path
        )
        
        if success:
            jlog(self.logger, logging.INFO,
                 event="phase3_avatar_generation_complete",
                 avatar_video_path=str(avatar_video_path),
                 video_size_mb=round(avatar_video_path.stat().st_size / (1024*1024), 2),
                 duration=self.video_utils.get_video_duration(avatar_video_path))
            return avatar_video_path
        
        return None

    def _phase4_presgen_integration(
        self, 
        avatar_video_path: Path, 
        script_content: str
    ) -> Optional[Path]:
        """Phase 4: Integrate with PresGen-Video for bullet point overlays"""
        jlog(self.logger, logging.INFO,
             event="phase4_presgen_integration_start",
             job_id=self.job_id,
             avatar_video=str(avatar_video_path))
        
        # CRITICAL FIX: Wait for avatar video to be fully created
        # MuseTalk runs asynchronously and may still be writing the file
        import time
        max_wait_time = 300  # 5 minutes additional wait for file completion
        poll_interval = 10   # Check every 10 seconds
        
        start_wait = time.time()
        while time.time() - start_wait < max_wait_time:
            if avatar_video_path.exists() and avatar_video_path.stat().st_size > 1024*1024:  # >1MB indicates real content
                # Additional check: ensure file is not actively being written
                initial_size = avatar_video_path.stat().st_size
                time.sleep(5)  # Wait 5 seconds
                
                if avatar_video_path.stat().st_size == initial_size:
                    # File size stable - MuseTalk has finished writing
                    jlog(self.logger, logging.INFO,
                         event="avatar_video_ready_for_integration",
                         file_size_mb=round(initial_size / (1024*1024), 2))
                    break
                else:
                    jlog(self.logger, logging.INFO,
                         event="avatar_video_still_writing",
                         current_size_mb=round(avatar_video_path.stat().st_size / (1024*1024), 2))
            
            jlog(self.logger, logging.INFO,
                 event="waiting_for_avatar_video_completion",
                 elapsed_seconds=int(time.time() - start_wait),
                 file_exists=avatar_video_path.exists(),
                 file_size_mb=round(avatar_video_path.stat().st_size / (1024*1024), 2) if avatar_video_path.exists() else 0)
            time.sleep(poll_interval)
        
        if not avatar_video_path.exists() or avatar_video_path.stat().st_size < 1024*1024:
            jlog(self.logger, logging.ERROR,
                 event="avatar_video_not_ready_timeout",
                 waited_seconds=int(time.time() - start_wait))
            return None
        
        # Use existing PresGen-Video Phase 3 pipeline
        try:
            # Import PresGen-Video components
            from src.mcp.tools.video_phase3 import create_full_screen_video_with_overlays
            
            final_output_path = self.output_dir / f"training_video_{self.job_id}.mp4"
            
            # Process through PresGen-Video Phase 3
            result = create_full_screen_video_with_overlays(
                video_path=str(avatar_video_path),
                script_content=script_content,
                output_path=str(final_output_path),
                logger=self.logger
            )
            
            if result.get("success"):
                jlog(self.logger, logging.INFO,
                     event="phase4_presgen_integration_complete",
                     final_video=str(final_output_path),
                     bullet_points=len(result.get("bullet_points", [])))
                return final_output_path
                
        except ImportError as e:
            jlog(self.logger, logging.ERROR,
                 event="presgen_video_import_failed",
                 error=str(e))
            # Fallback: just return avatar video without overlays
            return avatar_video_path
            
        except Exception as e:
            jlog(self.logger, logging.ERROR,
                 event="phase4_presgen_integration_failed",
                 error=str(e))
            return avatar_video_path
        
        return None

    def _error_result(self, error_message: str) -> Dict[str, Any]:
        """Create standardized error result"""
        processing_time = time.time() - self.start_time if self.start_time else 0
        
        result = {
            "success": False,
            "job_id": self.job_id,
            "error": error_message,
            "processing_time": processing_time
        }
        
        jlog(self.logger, logging.ERROR,
             event="training_video_processing_error",
             **result)
        
        return result

    def _count_video_frames(self, video_path: Path) -> int:
        """Count total frames in video file"""
        try:
            return self.video_utils.get_frame_count(video_path)
        except:
            return 0

    def _extract_bullet_points(self, script_content: str) -> List[str]:
        """Extract key bullet points from script content"""
        # Simple bullet point extraction - can be enhanced with LLM
        sentences = [s.strip() for s in script_content.split('.') if s.strip()]
        
        # Return first 5 sentences as bullet points
        bullet_points = []
        for sentence in sentences[:5]:
            if len(sentence) > 20:  # Skip very short sentences
                bullet_points.append(sentence + '.')
                
        return bullet_points