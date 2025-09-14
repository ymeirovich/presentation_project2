#!/usr/bin/env python3
"""
Test script to verify bullet timing works with 10-second video
"""

import sys
import os
sys.path.insert(0, '.')

from src.mcp.tools.video_phase3 import Phase3Orchestrator

def test_real_video_timing():
    """Test timing with real 10-second video"""
    
    # Create test orchestrator with real job data
    os.makedirs("/tmp/jobs/timing_test", exist_ok=True)
    orchestrator = Phase3Orchestrator(job_id="timing_test")
    
    # Create job data that mimics what the actual system uses
    real_video = "/Users/yitzchak/Documents/learn/presentation_project/sales-agent-labs/sadtalker-api/examples/presgen-training-avatar.mp4"
    
    if not os.path.exists(real_video):
        print("❌ Real video not found")
        return False
    
    # Get actual video duration
    video_metadata = orchestrator._get_video_metadata(real_video)
    actual_duration = video_metadata.get("duration", 10.0)
    print(f"📹 Video duration: {actual_duration} seconds")
    print(f"📹 Video dimensions: {video_metadata.get('width')}x{video_metadata.get('height')}")
    
    # Mock job data with bullet points
    job_data = {
        "summary": {
            "bullet_points": [
                {"timestamp": "00:30", "text": "AWS Cloud Practitioner certification", "confidence": 0.9, "duration": 15.0},
                {"timestamp": "01:15", "text": "Future-proof your career opportunities", "confidence": 0.8, "duration": 15.0},
                {"timestamp": "02:00", "text": "Join over one million certified professionals", "confidence": 0.9, "duration": 15.0}
            ]
        },
        "video_metadata": video_metadata
    }
    
    # Test timeline generation with real video duration
    timeline = orchestrator._generate_slide_timeline(job_data)
    
    if timeline:
        print(f"✅ Timeline generated with {len(timeline)} bullets:")
        for i, entry in enumerate(timeline, 1):
            print(f"   Bullet {i}: {entry['start_time']}s - '{entry['text'][:50]}...'")
        
        # Test FFmpeg command generation
        try:
            cmd = orchestrator._build_fullscreen_ffmpeg_command(real_video, timeline, "/tmp/timing_test.mp4")
            
            # Extract timing from the command
            cmd_str = " ".join(cmd)
            import re
            timing_matches = re.findall(r"enable='gte\(t,(\d+)\)'", cmd_str)
            print(f"📋 FFmpeg timing: {timing_matches}")
            
            return True
            
        except Exception as e:
            print(f"❌ Command generation failed: {e}")
            return False
    else:
        print("❌ Timeline generation failed")
        return False

if __name__ == "__main__":
    success = test_real_video_timing()
    sys.exit(0 if success else 1)