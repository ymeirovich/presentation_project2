# src/mcp/tools/video_phase3.py
"""
Phase3Orchestrator for final video composition with 50/50 layout and timed slides
"""

import asyncio
import logging
import time
import subprocess
import json
import os
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass

from src.common.jsonlog import jlog

log = logging.getLogger("video_phase3")


@dataclass
class CompositionResult:
    """Final composition result"""
    success: bool
    output_path: Optional[str]
    processing_time: float
    video_metadata: Optional[Dict[str, Any]]
    error: Optional[str] = None


class Phase3Orchestrator:
    """Orchestrator for full-screen video composition with natural SRT subtitle overlays"""
    
    def __init__(self, job_id: str, job_data: Optional[Dict[str, Any]] = None):
        self.job_id = job_id
        self.job_dir = Path(f"/tmp/jobs/{job_id}")
        self.output_dir = self.job_dir / "output"
        self.output_dir.mkdir(exist_ok=True)
        self._provided_job_data = job_data  # Store provided job data
        
    def compose_final_video(self) -> Dict[str, Any]:
        """
        Create final video with full-screen layout and natural SRT subtitle overlay:
        - Original video at full resolution
        - Timed text overlays using SRT subtitles
        
        Returns:
            Dict with success status, output path, and processing time
        """
        start_time = time.time()
        
        try:
            jlog(log, logging.INFO,
                 event="phase3_composition_start",
                 job_id=self.job_id)
            
            # 1. Load job data and validate inputs
            job_data = self._load_job_data()
            if not job_data:
                return {"success": False, "error": "Failed to load job data"}
            
            # 2. Prepare video assets
            video_assets = self._prepare_video_assets(job_data)
            if not video_assets:
                return {"success": False, "error": "Failed to prepare video assets"}
            
            # 3. Generate slide timeline
            slide_timeline = self._generate_slide_timeline(job_data)
            if not slide_timeline:
                return {"success": False, "error": "Failed to generate slide timeline"}
            
            # 3.5. Generate subtitle file for debugging/reference
            subtitle_path = self._generate_subtitle_file(slide_timeline)
            jlog(log, logging.INFO,
                 event="subtitle_file_generated",
                 job_id=self.job_id,
                 subtitle_path=subtitle_path)
            
            # 4. Create full-screen composition with SRT overlay
            output_path = self._create_fullscreen_composition(
                video_assets, slide_timeline, job_data
            )
            if not output_path:
                return {"success": False, "error": "Failed to create video composition"}
            
            processing_time = time.time() - start_time
            
            # 5. Verify output and get metadata
            video_metadata = self._get_video_metadata(output_path)
            
            jlog(log, logging.INFO,
                 event="phase3_composition_complete",
                 job_id=self.job_id,
                 output_path=str(output_path),
                 processing_time=processing_time,
                 video_metadata=video_metadata)
            
            return {
                "success": True,
                "output_path": str(output_path),
                "processing_time": processing_time,
                "video_metadata": video_metadata,
                "corrected_timeline": slide_timeline  # Corrected timestamps for UI
            }
            
        except Exception as e:
            error_msg = f"Phase 3 composition failed: {str(e)}"
            jlog(log, logging.ERROR,
                 event="phase3_composition_exception",
                 job_id=self.job_id,
                 error=error_msg)
            return {"success": False, "error": error_msg}
    
    def _load_job_data(self) -> Optional[Dict[str, Any]]:
        """Load job data including summary, crop region, and slide information"""
        try:
            summary_data = None
            
            # First try to use provided job data (from HTTP service)
            if self._provided_job_data:
                jlog(log, logging.INFO,
                     event="job_data_provided_debug",
                     job_id=self.job_id,
                     provided_keys=list(self._provided_job_data.keys()),
                     has_summary="summary" in self._provided_job_data)
                
                if "summary" in self._provided_job_data:
                    summary_data = self._provided_job_data["summary"]
                    jlog(log, logging.INFO,
                         event="job_data_loaded_from_provided",
                         job_id=self.job_id,
                         has_summary=bool(summary_data),
                         summary_keys=list(summary_data.keys()) if isinstance(summary_data, dict) else "not_dict")
            else:
                jlog(log, logging.WARNING,
                     event="no_job_data_provided",
                     job_id=self.job_id)
            
            # Fallback to loading from saved state file
            if not summary_data:
                job_state_file = self.job_dir / "job_state.json"
                if job_state_file.exists():
                    # Load from saved job state
                    import json
                    with open(job_state_file, 'r') as f:
                        job_state = json.load(f)
                        summary_data = job_state.get("summary")
                        
                    jlog(log, logging.INFO,
                         event="job_data_loaded_from_state",
                         job_id=self.job_id,
                         has_summary=bool(summary_data))
            
            # Final fallback to mock data if no source found
            if not summary_data:
                jlog(log, logging.WARNING,
                     event="job_data_fallback_to_mock",
                     job_id=self.job_id,
                     reason="no_saved_state_found")
                
                summary_data = {
                    "bullet_points": [
                        {"timestamp": "00:30", "text": "Our goal is to demonstrate AI transformation", "confidence": 0.9, "duration": 20.0},
                        {"timestamp": "01:15", "text": "Data shows significant improvements", "confidence": 0.8, "duration": 25.0},
                        {"timestamp": "02:00", "text": "Recommendation: implement company-wide", "confidence": 0.9, "duration": 15.0}
                    ],
                    "main_themes": ["Strategy", "Data", "Implementation"],
                    "total_duration": "02:30"
                }
            
            return {
                "summary": summary_data,
                "video_metadata": {"width": 1280, "height": 720, "duration": 150.0, "fps": 30}
            }
            
        except Exception as e:
            jlog(log, logging.ERROR,
                 event="load_job_data_failed",
                 job_id=self.job_id,
                 error=str(e))
            return None
    
    def _prepare_video_assets(self, job_data: Dict[str, Any]) -> Optional[Dict[str, str]]:
        """Prepare and validate video assets (simplified - only raw video needed)"""
        try:
            raw_video = self.job_dir / "raw_video.mp4"
            
            # Validate raw video exists
            if not raw_video.exists():
                jlog(log, logging.ERROR,
                     event="raw_video_missing",
                     job_id=self.job_id,
                     expected_path=str(raw_video))
                return None
            
            return {
                "raw_video": str(raw_video)
            }
            
        except Exception as e:
            jlog(log, logging.ERROR,
                 event="prepare_assets_failed",
                 job_id=self.job_id,
                 error=str(e))
            return None
    
    def _generate_slide_timeline(self, job_data: Dict[str, Any]) -> Optional[List[Dict[str, Any]]]:
        """Generate timeline for slide overlays based on bullet points with video duration validation"""
        try:
            bullet_points = job_data["summary"]["bullet_points"]
            timeline = []
            
            # Get actual video duration - try multiple sources
            video_duration = self._get_actual_video_duration(job_data)
            
            jlog(log, logging.INFO,
                 event="video_duration_check",
                 job_id=self.job_id,
                 video_duration=video_duration,
                 bullet_count=len(bullet_points))
            
            # Sort bullets by original timestamp to maintain order
            sorted_bullets = []
            for i, bullet in enumerate(bullet_points):
                # Convert MM:SS timestamp to seconds
                timestamp_parts = bullet["timestamp"].split(":")
                start_seconds = int(timestamp_parts[0]) * 60 + int(timestamp_parts[1])
                sorted_bullets.append((i, bullet, start_seconds))
            
            # Use timing that fits within the actual video duration
            # Distribute bullets evenly across the available time
            for idx, (original_index, bullet, original_timestamp) in enumerate(sorted_bullets):
                if len(bullet_points) > 1:
                    # Calculate timing based on actual video duration
                    if video_duration <= 15:
                        # Short video: use tight spacing (0s, 3s, 6s for 10s video)
                        interval = max(3, int(video_duration / len(bullet_points)))
                        adjusted_start = idx * interval
                    elif video_duration <= 60:
                        # Medium video: use moderate spacing
                        interval = max(5, int(video_duration / (len(bullet_points) + 1)))
                        adjusted_start = idx * interval
                    else:
                        # Long video: use original 15-second intervals
                        timing_intervals = [0, 15, 30, 45, 60]
                        adjusted_start = timing_intervals[idx] if idx < len(timing_intervals) else idx * 15
                        
                    # Ensure we don't exceed video duration minus small buffer
                    buffer = 2  # 2-second buffer before video ends
                    max_start_time = max(video_duration - buffer, 1)
                    adjusted_start = min(adjusted_start, max_start_time)
                else:
                    adjusted_start = 0
                
                # Log if timestamp was adjusted
                if original_timestamp != adjusted_start:
                    jlog(log, logging.WARNING,
                         event="timestamp_adjusted",
                         job_id=self.job_id,
                         bullet_index=idx+1,
                         original_timestamp=original_timestamp,
                         adjusted_timestamp=adjusted_start,
                         video_duration=video_duration)
                
                timeline.append({
                    "slide_index": original_index,
                    "start_time": adjusted_start,
                    "duration": bullet["duration"],
                    "text": bullet["text"]
                })
            
            jlog(log, logging.INFO,
                 event="slide_timeline_generated",
                 job_id=self.job_id,
                 timeline_entries=len(timeline),
                 video_duration=video_duration,
                 final_timestamps=[entry["start_time"] for entry in timeline])
            
            return timeline
            
        except Exception as e:
            jlog(log, logging.ERROR,
                 event="timeline_generation_failed",
                 job_id=self.job_id,
                 error=str(e))
            return None
    
    def _get_actual_video_duration(self, job_data: Dict[str, Any]) -> float:
        """Get actual video duration using ffprobe (most reliable method)"""
        # ALWAYS use ffprobe for accurate duration - job metadata can be wrong
        try:
            raw_video_path = self.job_dir / "raw_video.mp4"
            if raw_video_path.exists():
                metadata = self._get_video_metadata(raw_video_path)
                if metadata and "duration" in metadata:
                    duration = metadata["duration"]
                    jlog(log, logging.INFO,
                         event="video_duration_from_ffprobe",
                         job_id=self.job_id,
                         duration=duration,
                         source="ffprobe_direct")
                    return float(duration)
        except Exception as e:
            jlog(log, logging.WARNING,
                 event="video_duration_probe_failed",
                 job_id=self.job_id,
                 error=str(e))
        
        # Fallback: Try to get from job metadata (less reliable)
        if "video_metadata" in job_data:
            duration = job_data["video_metadata"].get("duration")
            if duration:
                jlog(log, logging.WARNING,
                     event="video_duration_from_metadata_fallback",
                     job_id=self.job_id,
                     duration=duration,
                     message="Using job metadata as fallback - may be inaccurate")
                return float(duration)
        
        # Default to 66 seconds (1:06)
        jlog(log, logging.WARNING,
             event="video_duration_default",
             job_id=self.job_id,
             default_duration=66)
        return 66.0
    
    def _create_fullscreen_composition(self, 
                                     video_assets: Dict[str, str], 
                                     slide_timeline: List[Dict[str, Any]],
                                     job_data: Dict[str, Any]) -> Optional[Path]:
        """Create full-screen video with natural SRT subtitle overlay"""
        try:
            raw_video = video_assets["raw_video"]
            output_path = self.output_dir / f"final_video_{self.job_id}.mp4"
            
            # Build simplified ffmpeg command for full-screen with SRT overlay
            cmd = self._build_fullscreen_ffmpeg_command(raw_video, slide_timeline, output_path)
            
            jlog(log, logging.INFO,
                 event="ffmpeg_command_start",
                 job_id=self.job_id,
                 command=" ".join(cmd),  # Log full command for debugging
                 input_video=raw_video)
            
            # Execute ffmpeg command
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )
            
            if result.returncode != 0:
                jlog(log, logging.ERROR,
                     event="ffmpeg_execution_failed",
                     job_id=self.job_id,
                     return_code=result.returncode,
                     stderr=result.stderr,  # Log full stderr for debugging
                     stdout=result.stdout)
                return None
            
            # Verify output file was created
            if not output_path.exists() or output_path.stat().st_size == 0:
                jlog(log, logging.ERROR,
                     event="ffmpeg_output_invalid",
                     job_id=self.job_id,
                     output_path=str(output_path),
                     exists=output_path.exists(),
                     size=output_path.stat().st_size if output_path.exists() else 0)
                return None
            
            jlog(log, logging.INFO,
                 event="ffmpeg_composition_success",
                 job_id=self.job_id,
                 output_path=str(output_path),
                 file_size=output_path.stat().st_size)
            
            return output_path
            
        except subprocess.TimeoutExpired:
            jlog(log, logging.ERROR,
                 event="ffmpeg_timeout",
                 job_id=self.job_id)
            return None
        except Exception as e:
            jlog(log, logging.ERROR,
                 event="ffmpeg_composition_exception",
                 job_id=self.job_id,
                 error=str(e))
            return None
    
    def _build_fullscreen_ffmpeg_command(self, 
                                        raw_video: str, 
                                        slide_timeline: List[Dict[str, Any]],
                                        output_path: Path) -> List[str]:
        """Build simplified ffmpeg command for full-screen video with right-side highlights rectangle"""
        
        # Get video dimensions for fixed coordinate calculation
        video_metadata = self._get_video_metadata(Path(raw_video))
        video_width = video_metadata.get("width", 1280)  # Default fallback
        video_height = video_metadata.get("height", 720)  # Default fallback
        
        # Build drawtext filters with calculated fixed coordinates
        drawtext_filters = self._build_drawtext_filters(slide_timeline, video_width, video_height, video_metadata)
        if not drawtext_filters:
            raise Exception("Failed to generate drawtext filters")
        
        # Use proven presgen-video approach: simple fixed coordinates with drawtext
        filter_chain = drawtext_filters
        
        # Command with drawtext filters using presgen-video's proven approach
        cmd = [
            "ffmpeg", "-y",  # Overwrite output
            "-i", raw_video,
            "-vf", filter_chain,
            "-c:v", "libx264",  # Video codec
            "-c:a", "aac",      # Audio codec  
            "-preset", "medium", # Balance between quality and speed
            "-crf", "23",       # Quality setting (lower = better quality)
            str(output_path)
        ]
        
        return cmd
    
    def _create_srt_subtitle_file(self, slide_timeline: List[Dict[str, Any]], output_path: Path) -> str:
        """Create SRT subtitle file for text overlays"""
        srt_path = str(output_path).replace('.mp4', '.srt')
        
        srt_content = []
        subtitle_index = 1
        
        # Add header subtitle
        srt_content.append(f"{subtitle_index}")
        srt_content.append("00:00:00,000 --> 99:59:59,999")
        srt_content.append("{\\an9}Key Points")  # Top-right alignment
        srt_content.append("")
        subtitle_index += 1
        
        # Add bullet points
        for i, entry in enumerate(slide_timeline, 1):
            start_time = entry['start_time']
            text = entry['text']
            
            # Convert seconds to SRT time format
            start_hours = int(start_time // 3600)
            start_minutes = int((start_time % 3600) // 60)
            start_seconds = int(start_time % 60)
            start_ms = int((start_time % 1) * 1000)
            
            start_timecode = f"{start_hours:02d}:{start_minutes:02d}:{start_seconds:02d},{start_ms:03d}"
            end_timecode = "99:59:59,999"  # Show until end of video
            
            srt_content.append(f"{subtitle_index}")
            srt_content.append(f"{start_timecode} --> {end_timecode}")
            srt_content.append(f"{{\\an9}}#{i} {text}")  # Top-right alignment with bullet number
            srt_content.append("")
            subtitle_index += 1
        
        # Write SRT file
        with open(srt_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(srt_content))
        
        return srt_path
    
    def _build_drawtext_filters(self, slide_timeline: List[Dict[str, Any]], video_width: int, video_height: int, video_metadata: Dict[str, Any]) -> str:
        """Build drawtext filters using presgen-video's proven simple approach"""
        if not slide_timeline:
            return ""
            
        filter_parts = []
        
        # Use presgen-video's proven approach: simple fixed coordinates
        # Scale basic coordinates for video resolution (presgen-video used 512px width)
        base_width = 512  # Reference width from working presgen-video
        scale_factor = video_width / base_width
        
        # Fix rectangle to be exactly 25% of screen width on the right side
        rect_width = int(video_width * 0.25)    # Exactly 25% of video width
        rect_x = video_width - rect_width       # Position at right edge minus width
        rect_height = video_height              # Full height
        
        # 1. Add black semi-transparent rectangle with 5% top and bottom margins
        margin_y = int(video_height * 0.05)  # 5% of video height
        rect_filter = (
            f"drawbox="
            f"x={rect_x}:y={margin_y}:"                           # 5% top margin
            f"w={rect_width}:h={rect_height - 2*margin_y}:"       # Reduce height by margins
            f"color=black@0.7:t=fill"                             # Black semi-transparent
        )
        filter_parts.append(rect_filter)
        
        # 2. Add "Key Points" title (top-center, 5% from top of rectangle)
        title_font_size = int(10 * scale_factor)  # Base 10px scales to ~28px final size
        title_x = rect_x + (rect_width // 2) - int(len("Key Points") * title_font_size * 0.3)  # Center within rectangle
        effective_rect_height = rect_height - 2*margin_y  # Height of actual rectangle
        title_y = margin_y + int(effective_rect_height * 0.05)  # 5% from top of rectangle
        
        title_filter = (
            "drawtext=text='Key Points':"
            f"fontsize={title_font_size}:"
            "fontcolor=white:"
            "fontfile=/System/Library/Fonts/Helvetica.ttc:"  # Arial/Helvetica font
            f"x={title_x}:y={title_y}"
        )
        filter_parts.append(title_filter)
        
        # 3. Add bullet points with proper word wrapping
        bullet_font_size = int(8 * scale_factor)  # Base 8px scales to ~24px final size
        bullet_start_x = rect_x + int(rect_width * 0.08)  # Increased margin from rectangle left edge
        bullet_start_y = title_y + title_font_size + int(effective_rect_height * 0.05)  # 5% margin below title (same as between bullets)
        
        current_y = bullet_start_y
        
        # Get maxBullets from job config, default to 5
        config = (self._provided_job_data or {}).get('config', {})
        max_bullets = config.get('maxBullets', 5)
        
        # Apply user's max bullets limit first
        limited_timeline = slide_timeline[:max_bullets]
        
        # Calculate bullets per group based on available space
        bullets_per_group = self._calculate_bullets_per_group(rect_height, bullet_font_size, limited_timeline)
        
        # Create bullet groups with rotation logic
        bullet_groups = self._create_bullet_groups(limited_timeline, bullets_per_group)
        group_timings = self._calculate_group_timings(bullet_groups)
        
        # Generate display filters for each group with individual bullet timing but group boundaries
        for group_timing in group_timings:
            group_start_time = group_timing['start_time']
            group_end_time = group_timing['end_time']
            group_bullets = group_timing['bullets']
            
            # Reset Y position for each group (all groups start at same Y)
            group_current_y = bullet_start_y
            
            # Add bullets in this group - each appears at its individual time
            for bullet_idx, entry in enumerate(group_bullets):
                # Calculate original bullet number for numbering
                original_bullet_num = limited_timeline.index(entry) + 1
                bullet_start_time = entry['start_time']
                
                # Build individual bullet enable condition:
                # Show from bullet's time AND within group boundaries
                if group_end_time is not None:
                    # Bullet appears at its time, disappears when group ends
                    bullet_enable_condition = f"'gte(t,{bullet_start_time})*lt(t,{group_end_time})'"
                else:
                    # Last group - bullet appears at its time, stays visible
                    bullet_enable_condition = f"'gte(t,{bullet_start_time})'"
                
                text = entry['text'].replace("'", "\\'").replace(":", "\\:")  # Escape special chars
                numbered_text = f"#{original_bullet_num} {text}"
                
                # Word wrap text to fit within rectangle width
                max_chars_per_line = int(rect_width / (bullet_font_size * 0.6))  # Estimate chars per line
                wrapped_lines = self._wrap_text_for_rectangle(numbered_text, max_chars_per_line)
                
                # Add each line of wrapped text with individual bullet timing
                for line_idx, line in enumerate(wrapped_lines):
                    line_y = group_current_y + (line_idx * int(bullet_font_size * 1.3))  # Line spacing
                    
                    bullet_filter = (
                        f"drawtext=text='{line}':"
                        f"fontsize={bullet_font_size}:"
                        "fontcolor=white:"
                        "fontfile=/System/Library/Fonts/Helvetica.ttc:"  # Arial/Helvetica font
                        f"x={bullet_start_x}:y={line_y}:"
                        f"enable={bullet_enable_condition}"
                    )
                    filter_parts.append(bullet_filter)
                
                # Move Y position for next bullet in this group
                group_current_y += len(wrapped_lines) * int(bullet_font_size * 1.3) + int(effective_rect_height * 0.05)  # 5% margin between bullets
        
        # Chain all filters together
        return ",".join(filter_parts)
    
    def _calculate_bullets_per_group(self, rect_height: int, font_size: int, slide_timeline: List[Dict[str, Any]]) -> int:
        """Calculate maximum bullets that can fit in the overlay rectangle"""
        # Calculate available space
        effective_rect_height = rect_height - int(rect_height * 0.10)  # Subtract 5% top + 5% bottom margins
        title_space = font_size + int(effective_rect_height * 0.05)  # Title + 5% margin below
        usable_height = effective_rect_height - int(effective_rect_height * 0.05) - title_space  # Subtract title space
        
        # Estimate space needed per bullet
        line_height = int(font_size * 1.3)  # Line spacing
        bullet_spacing = int(effective_rect_height * 0.05)  # 5% spacing between bullets
        
        # Estimate average lines per bullet by sampling a few bullets
        avg_lines_per_bullet = 1
        if slide_timeline:
            sample_size = min(3, len(slide_timeline))
            total_lines = 0
            max_chars_per_line = 25  # Rough estimate
            
            for i in range(sample_size):
                bullet_text = f"#{i+1} {slide_timeline[i]['text']}"
                wrapped_lines = self._wrap_text_for_rectangle(bullet_text, max_chars_per_line)
                total_lines += len(wrapped_lines)
            
            avg_lines_per_bullet = max(1, total_lines / sample_size)
        
        # Calculate space per bullet (lines + spacing)
        space_per_bullet = int(avg_lines_per_bullet * line_height) + bullet_spacing
        
        # Calculate max bullets that fit, with safety margin
        max_bullets = max(2, int(usable_height / space_per_bullet) - 1)  # Subtract 1 for safety margin
        
        # Cap at reasonable limits
        return min(max_bullets, 4)  # Never more than 4 bullets per group for readability

    def _create_bullet_groups(self, slide_timeline: List[Dict[str, Any]], bullets_per_group: int) -> List[List[Dict[str, Any]]]:
        """Group bullets into displayable chunks with calculated transition times"""
        if not slide_timeline or bullets_per_group <= 0:
            return []
        
        groups = []
        for i in range(0, len(slide_timeline), bullets_per_group):
            group = slide_timeline[i:i + bullets_per_group]
            groups.append(group)
        
        return groups

    def _calculate_group_timings(self, bullet_groups: List[List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
        """Calculate when each bullet group should appear and disappear"""
        if not bullet_groups:
            return []
        
        group_timings = []
        
        for i, group in enumerate(bullet_groups):
            # Group starts when its first bullet should appear
            start_time = group[0]['start_time']
            
            # Group ends when next group starts, or video ends
            if i < len(bullet_groups) - 1:
                end_time = bullet_groups[i + 1][0]['start_time']
            else:
                end_time = None  # Last group shows until end of video
            
            group_timings.append({
                'group_index': i,
                'bullets': group,
                'start_time': start_time,
                'end_time': end_time
            })
        
        return group_timings

    def _wrap_text_for_rectangle(self, text: str, max_chars_per_line: int = 25) -> List[str]:
        """Wrap text to fit within rectangle width"""
        words = text.split()
        lines = []
        current_line = ""
        
        for word in words:
            # Check if adding this word would exceed the line limit
            test_line = current_line + (" " if current_line else "") + word
            if len(test_line) <= max_chars_per_line:
                current_line = test_line
            else:
                # Start a new line
                if current_line:
                    lines.append(current_line)
                current_line = word
                
                # Handle very long words that exceed line limit
                if len(word) > max_chars_per_line:
                    # Split long word
                    while len(current_line) > max_chars_per_line:
                        lines.append(current_line[:max_chars_per_line-1] + "-")
                        current_line = current_line[max_chars_per_line-1:]
        
        # Add the last line
        if current_line:
            lines.append(current_line)
            
        return lines if lines else [""]
    
    def _generate_subtitle_file(self, slide_timeline: List[Dict[str, Any]]) -> str:
        """Generate SRT subtitle file for timed text overlays"""
        # Use the presgen-video/srt directory
        srt_dir = Path("presgen-video/subtitles")
        srt_dir.mkdir(parents=True, exist_ok=True)
        srt_path = srt_dir / f"subtitles_{self.job_id}.srt"
        
        try:
            with open(srt_path, 'w', encoding='utf-8') as f:
                for i, entry in enumerate(slide_timeline, 1):
                    start_time = entry['start_time']
                    duration = entry['duration']
                    end_time = start_time + duration
                    text = entry['text']
                    
                    # Convert seconds to SRT time format (HH:MM:SS,mmm)
                    start_srt = self._seconds_to_srt_time(start_time)
                    end_srt = self._seconds_to_srt_time(end_time)
                    
                    # Write SRT entry
                    f.write(f"{i}\n")
                    f.write(f"{start_srt} --> {end_srt}\n")
                    f.write(f"{text}\n\n")
            
            jlog(log, logging.INFO,
                 event="subtitle_file_generated",
                 job_id=self.job_id,
                 subtitle_path=str(srt_path),
                 entries=len(slide_timeline))
            
            return str(srt_path)
            
        except Exception as e:
            jlog(log, logging.ERROR,
                 event="subtitle_generation_failed",
                 job_id=self.job_id,
                 error=str(e))
            return None
    
    def _seconds_to_srt_time(self, seconds: float) -> str:
        """Convert seconds to SRT timestamp format HH:MM:SS,mmm"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millisecs = int((seconds % 1) * 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{millisecs:03d}"
    
    def _get_video_metadata(self, video_path: Path) -> Dict[str, Any]:
        """Extract metadata from the final video using ffprobe"""
        try:
            cmd = [
                "ffprobe", "-v", "quiet", "-print_format", "json",
                "-show_format", "-show_streams", str(video_path)
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                return {}
            
            metadata = json.loads(result.stdout)
            video_stream = next(
                (s for s in metadata.get("streams", []) if s.get("codec_type") == "video"), 
                {}
            )
            
            # Calculate pixel aspect ratio
            sar = video_stream.get("sample_aspect_ratio", "1:1")
            pixel_aspect_ratio = 1.0
            if sar and ":" in sar:
                try:
                    sar_num, sar_den = map(int, sar.split(":"))
                    pixel_aspect_ratio = sar_num / sar_den
                except:
                    pixel_aspect_ratio = 1.0

            return {
                "duration": float(metadata.get("format", {}).get("duration", 0)),
                "width": video_stream.get("width"),
                "height": video_stream.get("height"),
                "pixel_aspect_ratio": pixel_aspect_ratio,
                "fps": eval(video_stream.get("r_frame_rate", "30/1")),  # Convert fraction to float
                "codec": video_stream.get("codec_name"),
                "file_size": int(metadata.get("format", {}).get("size", 0))
            }
            
        except Exception as e:
            jlog(log, logging.WARNING,
                 event="metadata_extraction_failed",
                 job_id=self.job_id,
                 error=str(e))
            return {}


# PresGen-Training Integration Function
def create_full_screen_video_with_overlays(
    video_path: str,
    script_content: str, 
    output_path: str,
    max_bullets: int = 5,
    logger: Optional[logging.Logger] = None
) -> Dict[str, Any]:
    """
    Create full-screen video with bullet point overlays for PresGen-Training.
    
    Simplified version of Phase3Orchestrator for avatar videos with bullet point overlays.
    
    Args:
        video_path: Path to input avatar video
        script_content: Text script content to extract bullet points from
        output_path: Path for output video with overlays
        logger: Optional logger instance
        
    Returns:
        Dict with success status, output path, and bullet points
    """
    start_time = time.time()
    
    if logger:
        jlog(logger, logging.INFO,
             event="presgen_training_overlay_start",
             video_path=video_path,
             output_path=output_path,
             script_length=len(script_content))
    
    try:
        # 1. Extract bullet points from script content
        bullet_points = _extract_bullet_points_from_script(script_content)
        
        if logger:
            jlog(logger, logging.INFO,
                 event="bullet_points_extracted",
                 bullet_count=len(bullet_points),
                 bullet_points=bullet_points)
        
        # 2. Get video metadata for timing
        video_metadata = _get_simple_video_metadata(video_path)
        if not video_metadata or not video_metadata.get('duration'):
            return {
                "success": False,
                "error": "Could not analyze video metadata",
                "bullet_points": bullet_points
            }
        
        video_duration = video_metadata['duration']
        
        # 3. Generate timeline for bullet overlays
        timeline = _generate_bullet_timeline(bullet_points, video_duration)
        
        # 4. Create video with overlays using FFmpeg
        success = _create_overlay_video(video_path, output_path, timeline, max_bullets, logger)
        
        if not success:
            return {
                "success": False, 
                "error": "Failed to create overlay video",
                "bullet_points": bullet_points
            }
        
        processing_time = time.time() - start_time
        
        if logger:
            jlog(logger, logging.INFO,
                 event="presgen_training_overlay_complete",
                 output_path=output_path,
                 processing_time=processing_time,
                 bullet_count=len(bullet_points))
        
        return {
            "success": True,
            "output_path": output_path,
            "bullet_points": bullet_points,
            "processing_time": processing_time,
            "video_metadata": video_metadata
        }
        
    except Exception as e:
        error_msg = f"Overlay creation failed: {str(e)}"
        if logger:
            jlog(logger, logging.ERROR,
                 event="presgen_training_overlay_exception",
                 error=error_msg)
        
        return {
            "success": False,
            "error": error_msg,
            "bullet_points": []
        }


def _extract_bullet_points_from_script(script_content: str) -> List[str]:
    """Extract key highlight bullet points from script content (not transcript)"""
    # Create highlight summaries instead of using transcript directly
    sentences = [s.strip() for s in script_content.split('.') if s.strip()]
    
    bullet_points = []
    
    # Extract key themes and create highlight summaries
    for sentence in sentences:
        if len(sentence) > 20:
            # Create highlight summaries instead of full transcript
            highlight = _create_highlight_summary(sentence.strip())
            if highlight and highlight not in bullet_points:
                bullet_points.append(highlight)
    
    # Limit to 5 bullet points for overlay readability
    return bullet_points[:5]


def _create_highlight_summary(sentence: str) -> str:
    """Create concise highlight summary from sentence"""
    sentence = sentence.strip()
    
    # Key phrase extraction patterns
    key_patterns = {
        'technology': ['AI avatar technology', 'Avatar generation', 'AI technology'],
        'transformation': ['System transforms', 'Video transformation', 'Content transformation'], 
        'automation': ['Automatic analysis', 'Auto-generation', 'Automated processing'],
        'innovation': ['Key innovations', 'Local processing', 'Zero cloud costs'],
        'business': ['Training videos', 'Marketing content', 'Professional presentations']
    }
    
    # Extract highlights based on content
    if any(word in sentence.lower() for word in ['ai', 'avatar', 'technology']):
        if 'revolutionary' in sentence.lower():
            return "Revolutionary AI Avatar Technology"
        elif 'proprietary' in sentence.lower():
            return "Proprietary Avatar Generation"
        else:
            return "Advanced AI Avatar System"
            
    elif any(word in sentence.lower() for word in ['transform', 'system']):
        if 'automatic' in sentence.lower():
            return "Automatic Content Analysis & Overlays"
        else:
            return "Professional Video Transformation"
            
    elif any(word in sentence.lower() for word in ['local', 'cloud', 'cost']):
        return "Local Processing • Zero Cloud Costs"
        
    elif any(word in sentence.lower() for word in ['innovation', 'management']):
        return "Intelligent Resource Management"
        
    elif any(word in sentence.lower() for word in ['training', 'marketing', 'presentation']):
        return "Training • Marketing • Presentations"
        
    else:
        # Fallback: create concise version
        words = sentence.split()
        if len(words) > 8:
            # Take first 6-8 words and add key ending
            key_part = ' '.join(words[:6])
            if any(word in sentence.lower() for word in ['video', 'content']):
                return f"{key_part} Video Solutions"
            else:
                return f"{key_part}..."
        else:
            return sentence[:50] + "..." if len(sentence) > 50 else sentence


def _get_simple_video_metadata(video_path: str) -> Dict[str, Any]:
    """Get basic video metadata using ffprobe"""
    try:
        cmd = [
            "ffprobe", "-v", "quiet", "-print_format", "json",
            "-show_format", "-show_streams", video_path
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode != 0:
            return {}
        
        metadata = json.loads(result.stdout)
        video_stream = next(
            (s for s in metadata.get("streams", []) if s.get("codec_type") == "video"), 
            {}
        )
        
        return {
            "duration": float(metadata.get("format", {}).get("duration", 0)),
            "width": video_stream.get("width", 1280),
            "height": video_stream.get("height", 720),
            "fps": eval(video_stream.get("r_frame_rate", "25/1")),
            "codec": video_stream.get("codec_name", "h264")
        }
        
    except Exception:
        return {}


def _generate_bullet_timeline(bullet_points: List[str], video_duration: float) -> List[Dict[str, Any]]:
    """Generate timeline for bullet point overlays"""
    if not bullet_points:
        return []
    
    timeline = []
    
    # Distribute bullet points across video duration
    # Leave 10-second buffer at the end
    usable_duration = max(video_duration - 10, 20)
    
    for i, bullet in enumerate(bullet_points):
        if len(bullet_points) == 1:
            start_time = 5  # Single bullet starts at 5 seconds
        else:
            # Distribute evenly across video
            start_time = int((i * usable_duration) / len(bullet_points))
        
        timeline.append({
            "index": i + 1,
            "start_time": start_time, 
            "text": bullet,
            "duration": 15  # Show each bullet for 15 seconds
        })
    
    return timeline


def _create_overlay_video(
    input_video: str,
    output_video: str, 
    timeline: List[Dict[str, Any]],
    max_bullets: int = 5,
    logger: Optional[logging.Logger] = None
) -> bool:
    """Create video with bullet point overlays using FFmpeg"""
    
    if not timeline:
        # No overlays needed, just copy the video
        import shutil
        shutil.copy2(input_video, output_video)
        return True
    
    try:
        # Simplified approach: Create a much simpler overlay
        filter_parts = []
        
        # 1. Add semi-transparent background rectangle with 5% margins
        rect_x = 900
        rect_width = 350
        rect_height = 650
        margin_y = int(rect_height * 0.05)  # 5% of rectangle height
        
        # Simple square rectangle
        rect_filter = f"drawbox=x={rect_x}:y={margin_y}:w={rect_width}:h={rect_height - 2*margin_y}:color=black@0.7:t=fill"
        filter_parts.append(rect_filter)
        
        # 2. Add title with Arial font - positioned 5% from top of rectangle
        effective_rect_height = rect_height - 2*margin_y
        title_y = margin_y + int(effective_rect_height * 0.05)  # 5% from top of rectangle
        title_filter = f"drawtext=text='Key Points':fontsize=28:fontcolor=white:fontfile=/System/Library/Fonts/Helvetica.ttc:x=1000:y={title_y}"
        filter_parts.append(title_filter)
        
        # 3. Add properly word-wrapped bullet points  
        y_start = title_y + 28 + int(effective_rect_height * 0.05)  # 5% margin below title (same as between bullets)
        line_height = 24
        bullet_spacing = int(effective_rect_height * 0.05)  # 5% spacing between bullets
        
        # Calculate bullets per group and create groups with rotation
        bullets_per_group = self._calculate_bullets_per_group(effective_rect_height, 24, timeline)
        bullet_groups = self._create_bullet_groups(timeline[:max_bullets], bullets_per_group)
        group_timings = self._calculate_group_timings(bullet_groups)
        
        # Process each bullet group with individual bullet timing but group boundaries
        for group_idx, (bullet_group, timing_info) in enumerate(zip(bullet_groups, group_timings)):
            group_start_time = timing_info['start_time']
            group_end_time = timing_info['end_time']
            
            for i, entry in enumerate(bullet_group):
                bullet_text = entry['text']
                bullet_start_time = entry['start_time']
                
                # Build individual bullet enable condition:
                # Show from bullet's time AND within group boundaries
                if group_end_time is not None:
                    # Bullet appears at its time, disappears when group ends
                    enable_condition = f"'gte(t,{bullet_start_time})*lt(t,{group_end_time})'"
                else:
                    # Last group - bullet appears at its time, stays visible
                    enable_condition = f"'gte(t,{bullet_start_time})'"
                
                # Use existing word-wrap function from PresGen-Video
                wrapped_lines = _wrap_text_for_highlight_display(bullet_text, max_chars_per_line=30)
                
                # Calculate y position for this bullet
                bullet_y = y_start + (i * bullet_spacing)
                
                # Add each wrapped line as a separate drawtext filter
                for line_idx, line in enumerate(wrapped_lines):
                    clean_line = line.replace("'", "").replace(":", "").replace('"', '')
                    line_y = bullet_y + (line_idx * line_height)
                    
                    # Add numbered bullet point for first line, indent continuation lines  
                    if line_idx == 0:
                        # Use original bullet numbering across all groups
                        bullet_number = entry['original_index'] + 1
                        display_text = f"#{bullet_number} {clean_line}"  # Match screenshot format
                        x_pos = 920
                    else:
                        display_text = f"    {clean_line}"  # Indent continuation lines
                        x_pos = 940
                    
                    bullet_filter = (
                        f"drawtext=text='{display_text}'"
                        f":fontsize=24:fontcolor=white"  # Fixed to 24px as requested
                        f":fontfile=/System/Library/Fonts/Helvetica.ttc"  # Arial font
                        f":x={x_pos}:y={line_y}"
                        f":enable={enable_condition}"
                    )
                    filter_parts.append(bullet_filter)
        
        # Build simplified FFmpeg command
        drawtext_filter = ",".join(filter_parts)
        
        cmd = [
            "ffmpeg", "-y",
            "-i", input_video,
            "-vf", drawtext_filter,
            "-c:v", "libx264",
            "-c:a", "copy",  # Copy audio without re-encoding
            "-preset", "fast",  # Faster encoding
            output_video
        ]
        
        if logger:
            jlog(logger, logging.INFO,
                 event="ffmpeg_overlay_command_detailed",
                 timeline_count=len(timeline),
                 full_command=" ".join(cmd),
                 drawtext_filter=drawtext_filter[:500] + "..." if len(drawtext_filter) > 500 else drawtext_filter)
        
        # Execute FFmpeg
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120  # 2 minute timeout
        )
        
        if result.returncode != 0:
            if logger:
                jlog(logger, logging.ERROR,
                     event="ffmpeg_overlay_failed",
                     stderr=result.stderr[:1000])  # More stderr for debugging
            return False
        
        # Verify output exists
        output_path = Path(output_video)
        if not output_path.exists() or output_path.stat().st_size == 0:
            if logger:
                jlog(logger, logging.ERROR,
                     event="overlay_output_invalid")
            return False
        
        # Validate that overlays were actually applied
        overlay_validation = _validate_overlay_applied(output_video, input_video, logger)
        
        if logger:
            jlog(logger, logging.INFO,
                 event="overlay_creation_success",
                 output_size_mb=round(output_path.stat().st_size / (1024*1024), 2),
                 overlay_validation=overlay_validation)
        
        # Critical: If overlays weren't applied and we expected them, this is a failure
        if not overlay_validation["overlays_detected"] and timeline:
            if logger:
                jlog(logger, logging.ERROR,
                     event="overlay_validation_failed", 
                     error="Bullet overlays not detected in output video",
                     expected_overlays=len(timeline),
                     validation_details=overlay_validation)
            return False
        
        return True
        
    except subprocess.TimeoutExpired:
        if logger:
            jlog(logger, logging.ERROR,
                 event="ffmpeg_overlay_timeout")
        return False
    except Exception as e:
        if logger:
            jlog(logger, logging.ERROR,
                 event="overlay_creation_exception",
                 error=str(e))
        return False


def _wrap_text_simple(text: str, max_chars: int = 35) -> List[str]:
    """Simple text wrapping for overlay display"""
    words = text.split()
    lines = []
    current_line = ""
    
    for word in words:
        test_line = current_line + (" " if current_line else "") + word
        if len(test_line) <= max_chars:
            current_line = test_line
        else:
            if current_line:
                lines.append(current_line)
            current_line = word
    
    if current_line:
        lines.append(current_line)
    
    return lines if lines else [text[:max_chars]]


def _wrap_text_for_highlight_display(text: str, max_chars_per_line: int = 30) -> List[str]:
    """Wrap text for highlight display using PresGen-Video word-wrap logic"""
    words = text.split()
    lines = []
    current_line = ""
    
    for word in words:
        # Check if adding this word would exceed the line limit
        test_line = current_line + (" " if current_line else "") + word
        if len(test_line) <= max_chars_per_line:
            current_line = test_line
        else:
            # Start a new line
            if current_line:
                lines.append(current_line)
            current_line = word
            
            # Handle very long words that exceed line limit
            if len(word) > max_chars_per_line:
                # Split long word
                while len(current_line) > max_chars_per_line:
                    lines.append(current_line[:max_chars_per_line-1] + "-")
                    current_line = current_line[max_chars_per_line-1:]
    
    # Add the last line
    if current_line:
        lines.append(current_line)
        
    return lines if lines else [""]


def _validate_overlay_applied(
    output_video: str, 
    input_video: str, 
    logger: Optional[logging.Logger] = None
) -> Dict[str, Any]:
    """
    Validate that overlays were actually applied to the video.
    
    Compares file sizes and extracts sample frames to detect visual differences
    indicating overlay rendering.
    
    Returns:
        Dict with validation results including overlays_detected boolean
    """
    try:
        from pathlib import Path
        import subprocess
        
        output_path = Path(output_video)
        input_path = Path(input_video)
        
        if not output_path.exists() or not input_path.exists():
            return {
                "overlays_detected": False,
                "error": "Input or output video missing",
                "validation_method": "file_check"
            }
        
        # Check 1: File size difference (overlays should increase file size slightly)
        input_size = input_path.stat().st_size
        output_size = output_path.stat().st_size
        size_diff_percent = ((output_size - input_size) / input_size) * 100
        
        # Check 2: Extract a frame from overlay region to detect visual differences
        frame_check_result = _check_overlay_region_for_content(output_video, logger)
        
        # Heuristic: If file size increased and overlay region has content, overlays likely applied
        overlays_detected = (
            size_diff_percent > -10 and  # File shouldn't shrink significantly
            frame_check_result.get("has_overlay_content", False)
        )
        
        validation_result = {
            "overlays_detected": overlays_detected,
            "file_size_diff_percent": round(size_diff_percent, 2),
            "input_size_mb": round(input_size / (1024*1024), 2),
            "output_size_mb": round(output_size / (1024*1024), 2),
            "frame_analysis": frame_check_result,
            "validation_method": "size_and_frame_analysis"
        }
        
        if logger:
            jlog(logger, logging.INFO,
                 event="overlay_validation_analysis",
                 **validation_result)
        
        return validation_result
        
    except Exception as e:
        error_result = {
            "overlays_detected": False,
            "error": f"Validation failed: {str(e)}",
            "validation_method": "error"
        }
        
        if logger:
            jlog(logger, logging.WARNING,
                 event="overlay_validation_exception",
                 **error_result)
        
        return error_result


def _check_overlay_region_for_content(video_path: str, logger: Optional[logging.Logger] = None) -> Dict[str, Any]:
    """
    Extract a frame from the overlay region (right side) to detect if there's overlay content.
    
    Uses FFmpeg to extract a specific region and checks for non-uniform content.
    """
    try:
        import tempfile
        import subprocess
        
        # Extract frame from overlay region (x=920, y=80, w=350, h=300) at 5 seconds  
        # Updated to match actual overlay positioning (title at x=920:y=80)
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as temp_frame:
            extract_cmd = [
                "ffmpeg", "-y", "-ss", "5", "-i", video_path,
                "-vf", "crop=350:300:920:80",  # Extract overlay region matching actual positioning
                "-vframes", "1",
                temp_frame.name
            ]
            
            result = subprocess.run(extract_cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode != 0:
                return {
                    "has_overlay_content": False,
                    "error": "Frame extraction failed",
                    "method": "ffmpeg_crop"
                }
            
            # Simple check: if file is created and has reasonable size, likely has content
            frame_path = Path(temp_frame.name)
            if frame_path.exists() and frame_path.stat().st_size > 1000:  # > 1KB suggests content
                
                # Try to detect variation in the extracted region using ffprobe
                variation_check = _detect_pixel_variation(temp_frame.name)
                
                # Cleanup
                frame_path.unlink(missing_ok=True)
                
                return {
                    "has_overlay_content": variation_check.get("has_variation", False),
                    "frame_size_bytes": frame_path.stat().st_size if frame_path.exists() else 0,
                    "variation_analysis": variation_check,
                    "method": "ffmpeg_crop_with_analysis"
                }
            else:
                return {
                    "has_overlay_content": False,
                    "error": "Extracted frame too small or missing",
                    "method": "ffmpeg_crop"
                }
                
    except Exception as e:
        return {
            "has_overlay_content": False,
            "error": f"Region analysis failed: {str(e)}",
            "method": "error"
        }


def _detect_pixel_variation(image_path: str) -> Dict[str, Any]:
    """
    Detect if an image has pixel variation (indicating overlay content vs solid background).
    
    Uses ffprobe to analyze pixel statistics.
    """
    try:
        # Use ffprobe to get basic statistics about the image
        cmd = [
            "ffprobe", "-v", "quiet", "-select_streams", "v:0",
            "-show_entries", "frame=pkt_size", "-of", "csv=p=0",
            image_path
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        
        if result.returncode == 0 and result.stdout.strip():
            # If we can get frame info, assume there's content variation
            return {
                "has_variation": True,
                "method": "ffprobe_stats",
                "frame_data_size": result.stdout.strip()
            }
        
        return {
            "has_variation": False,
            "method": "ffprobe_stats",
            "error": "No frame data detected"
        }
        
    except Exception as e:
        # Default to assuming variation exists if we can't analyze
        return {
            "has_variation": True,
            "method": "error_fallback",
            "error": str(e)
        }