#!/usr/bin/env python3
"""
Debug script to test FFmpeg command generation and identify syntax issues.
"""

import sys
import os
sys.path.insert(0, '.')

from src.mcp.tools.video_phase3 import Phase3Orchestrator

def test_ffmpeg_command():
    """Test the FFmpeg command generation with mock data"""
    
    # Create necessary directories
    import os
    os.makedirs("/tmp/jobs/debug_test", exist_ok=True)
    
    # Create a test orchestrator
    orchestrator = Phase3Orchestrator(job_id="debug_test")
    
    # Mock slide timeline data matching the SRT transcript
    mock_timeline = [
        {
            "slide_index": 0,
            "start_time": 0,
            "duration": 20.0,
            "text": "Future-proof your career in the rapidly growing cloud industry"
        },
        {
            "slide_index": 1, 
            "start_time": 15,
            "duration": 20.0,
            "text": "Gain foundational knowledge of AWS cloud concepts and services"
        },
        {
            "slide_index": 2,
            "start_time": 30,
            "duration": 20.0,
            "text": "Validate your cloud literacy and demonstrate your understanding"
        }
    ]
    
    # Generate the FFmpeg command
    try:
        # Use sample video dimensions for testing
        test_width, test_height = 1920, 1920  # From the sample video
        drawtext_filters = orchestrator._build_drawtext_filters(mock_timeline, test_width, test_height)
        print("✅ Drawtext filters generated successfully!")
        print("\n📋 Generated FFmpeg drawtext filter:")
        print("-" * 80)
        print(drawtext_filters)
        print("-" * 80)
        
        # Test full command generation with real video
        test_video = "/Users/yitzchak/Documents/learn/presentation_project/sales-agent-labs/sadtalker-api/examples/presgen-training-avatar.mp4"
        test_output = "/tmp/test_output.mp4"
        
        # Test with real video to get accurate timing
        if os.path.exists(test_video):
            cmd = orchestrator._build_fullscreen_ffmpeg_command(
                test_video, mock_timeline, test_output
            )
        else:
            # Fallback to mock if real video doesn't exist
            cmd = ["echo", "Real video not found, using mock command"]
        
        print("\n🔧 Full FFmpeg command:")
        print("-" * 80)
        print(" ".join(cmd))
        print("-" * 80)
        
        return True
        
    except Exception as e:
        print(f"❌ Error generating FFmpeg command: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_ffmpeg_command()
    sys.exit(0 if success else 1)