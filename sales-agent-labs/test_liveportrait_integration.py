#!/usr/bin/env python3
"""
Test script for LivePortrait integration in PresGen-Training2
Tests the avatar generation engine with our test video
"""

import sys
import os
sys.path.append('.')
sys.path.append('presgen-training2/src')

from pathlib import Path
from core.liveportrait import LivePortraitEngine

def test_avatar_generation():
    """Test LivePortrait avatar generation with test video"""

    # Test paths
    test_video = "sadtalker-api/examples/presgen_test2.mp4"
    temp_dir = "temp_test"

    # Create temp directory
    os.makedirs(temp_dir, exist_ok=True)

    try:
        print("🚀 Testing LivePortrait Integration")
        print("=" * 50)

        # Initialize engine
        engine = LivePortraitEngine()
        print(f"✅ LivePortrait engine initialized")
        print(f"   Hardware config: {engine.hardware_config}")

        # Extract reference frame from test video
        reference_image = f"{temp_dir}/reference_frame.jpg"
        print(f"\n📸 Extracting reference frame...")

        success = engine.extract_reference_frame(
            video_path=test_video,
            output_image_path=reference_image
        )

        if not success:
            print("❌ Failed to extract reference frame")
            return False

        print(f"✅ Reference frame extracted: {reference_image}")

        # Extract audio from test video
        audio_path = f"{temp_dir}/test_audio.wav"
        print(f"\n🎵 Extracting audio...")

        success = engine.extract_audio_from_video(
            video_path=test_video,
            output_audio_path=audio_path
        )

        if not success:
            print("❌ Failed to extract audio")
            return False

        print(f"✅ Audio extracted: {audio_path}")

        # Test avatar generation using video as both source and driving
        # This is a simplified test - in production we'd use TTS audio
        print(f"\n🎭 Testing avatar generation (video-to-video)...")
        output_dir = f"{temp_dir}/output"

        # For this test, use the same video as both source and driving
        # In production, we'd use a different driving video or sequence
        result = engine.generate_avatar_video_from_video(
            driving_video=test_video,
            reference_image=reference_image,
            output_dir=output_dir,
            quality_level="fast"
        )

        if result.success:
            print(f"✅ Avatar generation successful!")
            print(f"   Output: {result.output_path}")
            print(f"   Processing time: {result.processing_time:.2f}s")
            print(f"   Quality level: {result.quality_level}")
        else:
            print(f"❌ Avatar generation failed: {result.error}")
            return False

        print("\n🎉 All tests passed!")
        return True

    except Exception as e:
        print(f"❌ Test failed with exception: {e}")
        return False

    finally:
        # Cleanup (optional - comment out to inspect outputs)
        # import shutil
        # if os.path.exists(temp_dir):
        #     shutil.rmtree(temp_dir)
        pass

if __name__ == "__main__":
    success = test_avatar_generation()
    sys.exit(0 if success else 1)