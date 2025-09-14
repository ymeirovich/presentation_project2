#!/usr/bin/env python3
"""
Test Voice Cloning + Lip-Sync Pipeline
Tests the complete pipeline from original video to voice-cloned lip-sync video
"""

import sys
import os
import json
import logging
import time
from pathlib import Path
from typing import Optional

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.common.jsonlog import jlog
from src.presgen_training.orchestrator import TrainingVideoOrchestrator
from src.presgen_training.avatar_generator import AvatarGenerator


def test_voice_extraction_and_cloning():
    """Test voice extraction and cloning components"""
    print("🧪 Testing Voice Extraction & Cloning Components...")
    
    # Setup logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("test_voice_clone")
    
    # Initialize avatar generator
    avatar_gen = AvatarGenerator(quality="fast", logger=logger)
    
    # Test dependency check
    deps = avatar_gen.check_dependencies()
    print(f"📋 Dependencies: {deps}")
    
    # Create test script
    test_script = "Hello, this is a test of the voice cloning system. The quick brown fox jumps over the lazy dog."
    output_dir = Path("presgen-training/outputs")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Check if we have any test videos
    test_videos = list(Path(".").glob("*.mp4"))
    if not test_videos:
        print("⚠️  No test videos found - creating mock test data")
        dummy_video_path = output_dir / "dummy.mp4"
        dummy_video_path.touch()
        test_videos = [dummy_video_path]

    
    test_video = test_videos[0]
    print(f"🎬 Using test video: {test_video}")
    
    # Test voice cloning with TTS fallback
    start_time = time.time()
    audio_path = avatar_gen.generate_tts_audio(
        text=test_script,
        output_path=output_dir / "test_cloned_audio.wav",
        reference_video_path=test_video
    )
    duration = time.time() - start_time
    
    result = {
        "voice_extraction": "completed" if audio_path else "failed",
        "voice_cloning_duration": round(duration, 2),
        "audio_output": str(audio_path) if audio_path else None,
        "dependencies": deps
    }
    
    if audio_path and audio_path.exists():
        result["audio_size_mb"] = round(audio_path.stat().st_size / (1024*1024), 2)
        print(f"✅ Voice cloning test completed: {audio_path} ({result['audio_size_mb']} MB)")
    else:
        print("❌ Voice cloning test failed")
    
    return result


def test_lip_sync_generation():
    """Test lip-sync video generation"""
    print("🎤 Testing Lip-Sync Video Generation...")
    
    # Setup
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("test_lip_sync")
    avatar_gen = AvatarGenerator(quality="fast", logger=logger)
    
    output_dir = Path("presgen-training/outputs")
    
    # Look for existing test audio and presenter frame
    test_audio = output_dir / "test_cloned_audio.wav"
    test_frame = Path("presgen-training/assets/presenter_frame.jpg")
    
    if not test_audio.exists():
        print("⚠️  No test audio found - run voice cloning test first")
        return {"lip_sync": "skipped - no audio"}
    
    if not test_frame:
        print("⚠️  No presenter frame found - creating test frame from video")
        # Try to extract frame from any video
        test_videos = list(Path(".").glob("*.mp4"))
        if test_videos:
            test_video = test_videos[0]
            # Extract a frame using ffmpeg
            import subprocess
            test_frame = output_dir / "test_frame.jpg"
            cmd = [
                "ffmpeg", "-i", str(test_video),
                "-vf", "select=eq(n\,10)",  # Select 10th frame
                "-vframes", "1",
                "-y", str(test_frame)
            ]
            try:
                result = subprocess.run(cmd, capture_output=True, timeout=30)
                if result.returncode != 0 or not test_frame.exists():
                    print("❌ Could not extract test frame")
                    return {"lip_sync": "skipped - no presenter frame"}
            except Exception as e:
                print(f"❌ Frame extraction failed: {e}")
                return {"lip_sync": "skipped - frame extraction failed"}
    
    print(f"🎵 Test audio: {test_audio}")
    print(f"🖼️  Test frame: {test_frame}")
    
    # Generate lip-sync video
    start_time = time.time()
    output_video = output_dir / "test_lip_sync_video.mp4"
    
    success = avatar_gen.generate_avatar_video(
        audio_path=test_audio,
        image_path=test_frame,
        output_path=output_video
    )
    
    duration = time.time() - start_time
    
    result = {
        "lip_sync": "completed" if success else "failed",
        "generation_duration": round(duration, 2),
        "video_output": str(output_video) if success else None
    }
    
    if success and output_video.exists():
        result["video_size_mb"] = round(output_video.stat().st_size / (1024*1024), 2)
        print(f"✅ Lip-sync generation completed: {output_video} ({result['video_size_mb']} MB)")
    else:
        print("❌ Lip-sync generation failed")
    
    return result


def test_full_pipeline():
    """Test the complete orchestrated pipeline"""
    print("🚀 Testing Full Voice Cloning + Lip-Sync Pipeline...")
    
    # Setup
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("test_full_pipeline")
    
    # Create test script file
    test_script = """
Welcome to our voice cloning demonstration. This system can take your original video,
extract your voice characteristics, and generate new lip-synced videos with different text content.

Key features include:
- Advanced voice extraction with noise reduction
- High-quality voice cloning using Coqui TTS
- Real-time lip-sync generation using MuseTalk
- Integration with bullet point overlays
    """.strip()
    
    output_dir = Path("presgen-training/outputs")
    script_path = output_dir / "test_script.txt"
    script_path.write_text(test_script)
    
    # Find test video
    test_videos = list(Path(".").glob("*.mp4"))
    if not test_videos:
        print("⚠️  No test videos found - cannot run full pipeline test")
        return {"full_pipeline": "skipped - no test video"}
    
    source_video = test_videos[0]
    print(f"🎬 Source video: {source_video}")
    print(f"📝 Test script: {script_path}")
    
    # Initialize orchestrator
    orchestrator = TrainingVideoOrchestrator(
        quality="fast",
        skip_hardware_check=True,
        output_dir=output_dir,
        logger=logger
    )
    
    # Run full pipeline
    start_time = time.time()
    
    try:
        result = orchestrator.process_training_video(
            script_path=script_path,
            source_video_path=source_video
        )
        
        duration = time.time() - start_time
        result["total_duration"] = round(duration, 2)
        
        if result["success"]:
            print(f"✅ Full pipeline completed successfully!")
            print(f"   Final video: {result['output_video']}")
            print(f"   Avatar video: {result['avatar_video']}")
            print(f"   Processing time: {result['total_duration']} seconds")
            print(f"   Avatar frames: {result.get('avatar_frames', 0)}")
        else:
            print(f"❌ Full pipeline failed: {result['error']}")
        
        return result
        
    except Exception as e:
        print(f"❌ Full pipeline exception: {e}")
        return {
            "success": False,
            "error": str(e),
            "total_duration": round(time.time() - start_time, 2)
        }

def main():
    print("🧪 Isolating Lip-Sync Generation Test")
    print("=" * 60)
    
    # To ensure the audio file exists, we first run the voice extraction part.
    try:
        print("Running preliminary voice extraction to generate audio for lip-sync test...")
        test_voice_extraction_and_cloning()
        print("\n" + "-" * 40 + "\n")
    except Exception as e:
        print(f"❌ Preliminary voice extraction failed: {e}")
        print("Cannot proceed to lip-sync test without audio.")
        return

    # Now, run only the lip-sync generation test
    try:
        results = test_lip_sync_generation()
        print("\n" + "=" * 60)
        print("🏁 Test Summary:")
        if results and results.get("lip_sync") == "completed":
            print("   lip_sync: ✅ PASSED")
            print(f"   - Video Output: {results.get('video_output')}")
            print(f"   - Duration: {results.get('generation_duration')}s")
            print(f"   - Size: {results.get('video_size_mb')} MB")
        else:
            print("   lip_sync: ❌ FAILED")
            print(f"   - Reason: {results}")

    except Exception as e:
        print(f"❌ Lip-sync test failed with an exception: {e}")


if __name__ == "__main__":
    main()
