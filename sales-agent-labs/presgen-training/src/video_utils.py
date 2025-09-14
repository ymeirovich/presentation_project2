"""
Video Utilities

Frame extraction, video analysis, and processing utilities for PresGen-Training.
Integrates with existing PresGen-Video infrastructure.
"""

import logging
import subprocess
import json
import time
from pathlib import Path
from typing import Optional, Dict, Any, List
import sys
import os

# Add project root for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.common.jsonlog import jlog


class VideoUtils:
    """
    Video processing utilities for PresGen-Training.
    
    Handles frame extraction, video analysis, and format conversion.
    """
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger("presgen_training.video_utils")
        
        # Check FFmpeg availability
        self.ffmpeg_available = self._check_ffmpeg()
        
        jlog(self.logger, logging.INFO,
             event="video_utils_init",
             ffmpeg_available=self.ffmpeg_available)

    def _check_ffmpeg(self) -> bool:
        """Check if FFmpeg is available"""
        try:
            result = subprocess.run(
                ["ffmpeg", "-version"],
                capture_output=True,
                timeout=5
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            jlog(self.logger, logging.WARNING,
                 event="ffmpeg_not_available",
                 solution="Install with: brew install ffmpeg (macOS) or apt install ffmpeg (Linux)")
            return False

    def get_video_info(self, video_path: Path) -> Dict[str, Any]:
        """Get comprehensive video information using ffprobe"""
        
        jlog(self.logger, logging.INFO,
             event="video_info_analysis_start",
             video_path=str(video_path))
        
        if not self.ffmpeg_available:
            return {"error": "FFmpeg not available"}
        
        try:
            cmd = [
                "ffprobe", "-v", "quiet",
                "-print_format", "json",
                "-show_format", "-show_streams",
                str(video_path)
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                info = json.loads(result.stdout)
                
                # Extract key video stream information
                video_stream = None
                audio_stream = None
                
                for stream in info.get("streams", []):
                    if stream.get("codec_type") == "video" and not video_stream:
                        video_stream = stream
                    elif stream.get("codec_type") == "audio" and not audio_stream:
                        audio_stream = stream
                
                processed_info = {
                    "duration": float(info.get("format", {}).get("duration", 0)),
                    "size_bytes": int(info.get("format", {}).get("size", 0)),
                    "format_name": info.get("format", {}).get("format_name", ""),
                    "video": {
                        "codec": video_stream.get("codec_name", "") if video_stream else "",
                        "width": int(video_stream.get("width", 0)) if video_stream else 0,
                        "height": int(video_stream.get("height", 0)) if video_stream else 0,
                        "fps": self._extract_fps(video_stream) if video_stream else 0
                    } if video_stream else None,
                    "audio": {
                        "codec": audio_stream.get("codec_name", "") if audio_stream else "",
                        "sample_rate": int(audio_stream.get("sample_rate", 0)) if audio_stream else 0,
                        "channels": int(audio_stream.get("channels", 0)) if audio_stream else 0
                    } if audio_stream else None
                }
                
                jlog(self.logger, logging.INFO,
                     event="video_info_analysis_complete",
                     info=processed_info)
                
                return processed_info
            else:
                jlog(self.logger, logging.ERROR,
                     event="ffprobe_failed",
                     error=result.stderr)
                
        except subprocess.TimeoutExpired:
            jlog(self.logger, logging.ERROR,
                 event="video_info_timeout")
                 
        except json.JSONDecodeError as e:
            jlog(self.logger, logging.ERROR,
                 event="video_info_json_parse_error",
                 error=str(e))
                 
        except Exception as e:
            jlog(self.logger, logging.ERROR,
                 event="video_info_exception",
                 error=str(e))
        
        return {"error": "Failed to analyze video"}

    def _extract_fps(self, video_stream: Dict[str, Any]) -> float:
        """Extract FPS from video stream info"""
        fps_str = video_stream.get("r_frame_rate", "0/1")
        try:
            if "/" in fps_str:
                num, den = fps_str.split("/")
                return float(num) / float(den) if float(den) != 0 else 0
            else:
                return float(fps_str)
        except (ValueError, ZeroDivisionError):
            return 0

    def extract_best_presenter_frame(
        self, 
        video_path: Path, 
        output_path: Path,
        timestamp: Optional[float] = None
    ) -> Optional[Path]:
        """Extract the best presenter frame from video"""
        
        jlog(self.logger, logging.INFO,
             event="frame_extraction_start",
             video_path=str(video_path),
             output_path=str(output_path),
             timestamp=timestamp)
        
        if not self.ffmpeg_available:
            return None
        
        try:
            # Get video info first
            video_info = self.get_video_info(video_path)
            if "error" in video_info:
                return None
            
            duration = video_info.get("duration", 0)
            
            # Use provided timestamp or extract from middle third of video
            if timestamp is None:
                # Extract from 40% into the video (good for presentations)
                timestamp = duration * 0.4
            
            # Ensure timestamp is within video bounds
            timestamp = max(0, min(timestamp, duration - 1))
            
            cmd = [
                "ffmpeg",
                "-ss", str(timestamp),  # Seek to timestamp
                "-i", str(video_path),
                "-vframes", "1",        # Extract 1 frame
                "-q:v", "2",           # High quality
                "-y",                  # Overwrite
                str(output_path)
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0 and output_path.exists():
                jlog(self.logger, logging.INFO,
                     event="frame_extraction_complete",
                     output_path=str(output_path),
                     timestamp=timestamp,
                     file_size_bytes=output_path.stat().st_size)
                
                return output_path
            else:
                jlog(self.logger, logging.ERROR,
                     event="frame_extraction_failed",
                     error=result.stderr)
                     
        except subprocess.TimeoutExpired:
            jlog(self.logger, logging.ERROR,
                 event="frame_extraction_timeout")
                 
        except Exception as e:
            jlog(self.logger, logging.ERROR,
                 event="frame_extraction_exception",
                 error=str(e))
        
        return None

    def extract_multiple_frames(
        self, 
        video_path: Path, 
        output_dir: Path,
        count: int = 5
    ) -> List[Path]:
        """Extract multiple candidate frames from video"""
        
        jlog(self.logger, logging.INFO,
             event="multiple_frame_extraction_start",
             video_path=str(video_path),
             output_dir=str(output_dir),
             frame_count=count)
        
        output_dir.mkdir(parents=True, exist_ok=True)
        extracted_frames = []
        
        if not self.ffmpeg_available:
            return extracted_frames
        
        try:
            # Get video duration
            video_info = self.get_video_info(video_path)
            duration = video_info.get("duration", 0)
            
            if duration <= 0:
                return extracted_frames
            
            # Calculate timestamps for frame extraction
            # Skip first and last 10% of video
            start_time = duration * 0.1
            end_time = duration * 0.9
            effective_duration = end_time - start_time
            
            timestamps = []
            if count == 1:
                timestamps = [start_time + effective_duration * 0.5]
            else:
                for i in range(count):
                    timestamp = start_time + (effective_duration * i / (count - 1))
                    timestamps.append(timestamp)
            
            # Extract frames
            for i, timestamp in enumerate(timestamps):
                frame_path = output_dir / f"frame_candidate_{i+1}.jpg"
                
                cmd = [
                    "ffmpeg",
                    "-ss", str(timestamp),
                    "-i", str(video_path),
                    "-vframes", "1",
                    "-q:v", "2",
                    "-y",
                    str(frame_path)
                ]
                
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=15
                )
                
                if result.returncode == 0 and frame_path.exists():
                    extracted_frames.append(frame_path)
                    
                    jlog(self.logger, logging.DEBUG,
                         event="frame_extracted",
                         frame_path=str(frame_path),
                         timestamp=timestamp)
            
            jlog(self.logger, logging.INFO,
                 event="multiple_frame_extraction_complete",
                 extracted_count=len(extracted_frames),
                 requested_count=count)
            
        except Exception as e:
            jlog(self.logger, logging.ERROR,
                 event="multiple_frame_extraction_exception",
                 error=str(e))
        
        return extracted_frames

    def get_video_duration(self, video_path: Path) -> float:
        """Get video duration in seconds"""
        try:
            info = self.get_video_info(video_path)
            return info.get("duration", 0.0)
        except:
            return 0.0

    def get_audio_duration(self, audio_path: Path) -> float:
        """Get audio duration in seconds"""
        if not self.ffmpeg_available:
            return 0.0
            
        try:
            cmd = [
                "ffprobe", "-v", "quiet",
                "-show_entries", "format=duration",
                "-of", "csv=p=0",
                str(audio_path)
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                return float(result.stdout.strip())
                
        except (subprocess.TimeoutExpired, ValueError):
            pass
            
        return 0.0

    def get_frame_count(self, video_path: Path) -> int:
        """Get total frame count in video"""
        if not self.ffmpeg_available:
            return 0
            
        try:
            cmd = [
                "ffprobe", "-v", "quiet",
                "-select_streams", "v:0",
                "-show_entries", "stream=nb_frames",
                "-of", "csv=p=0",
                str(video_path)
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                return int(result.stdout.strip())
                
        except (subprocess.TimeoutExpired, ValueError):
            pass
            
        return 0

    def convert_video_format(
        self, 
        input_path: Path, 
        output_path: Path,
        codec: str = "libx264",
        quality: str = "medium"
    ) -> bool:
        """Convert video to different format/codec"""
        
        jlog(self.logger, logging.INFO,
             event="video_conversion_start",
             input_path=str(input_path),
             output_path=str(output_path),
             codec=codec,
             quality=quality)
        
        if not self.ffmpeg_available:
            return False
        
        quality_settings = {
            "fast": ["-preset", "ultrafast", "-crf", "28"],
            "medium": ["-preset", "medium", "-crf", "23"], 
            "high": ["-preset", "slow", "-crf", "18"]
        }
        
        try:
            cmd = [
                "ffmpeg", "-i", str(input_path),
                "-c:v", codec,
                "-c:a", "aac"
            ]
            
            cmd.extend(quality_settings.get(quality, quality_settings["medium"]))
            cmd.extend(["-y", str(output_path)])
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )
            
            if result.returncode == 0:
                jlog(self.logger, logging.INFO,
                     event="video_conversion_complete",
                     output_path=str(output_path),
                     file_size_mb=round(output_path.stat().st_size / (1024*1024), 2))
                return True
            else:
                jlog(self.logger, logging.ERROR,
                     event="video_conversion_failed",
                     error=result.stderr)
                     
        except subprocess.TimeoutExpired:
            jlog(self.logger, logging.ERROR,
                 event="video_conversion_timeout")
                 
        except Exception as e:
            jlog(self.logger, logging.ERROR,
                 event="video_conversion_exception",
                 error=str(e))
        
        return False