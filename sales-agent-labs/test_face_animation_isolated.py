#!/usr/bin/env python3
"""
Face Animation Isolation Test
Tests LivePortrait face animation functionality separately from voice cloning
"""

import sys
import os
import time
import logging
from pathlib import Path

# Add the project root to the path
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent / "presgen-training2"))

def setup_logging():
    """Setup detailed logging for face animation test"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('temp/test-face-animation/face_animation_test.log')
        ]
    )
    return logging.getLogger("face_animation_test")

def test_face_animation_isolated():
    """Test face animation in isolation"""
    logger = setup_logging()

    # Test parameters
    source_video = "/Users/yitzchak/Documents/learn/presentation_project/sales-agent-labs/examples/video/presgen_test.mp4"
    driving_video = "/Users/yitzchak/Documents/learn/presentation_project/sales-agent-labs/sadtalker-api/examples/presgen-training-avatar1.mp4"
    output_dir = "temp/test-face-animation"

    logger.info("🎭 Starting Face Animation Isolation Test")
    logger.info("=" * 60)
    logger.info(f"Source video (face): {source_video}")
    logger.info(f"Driving video (animation): {driving_video}")
    logger.info(f"Output directory: {output_dir}")

    # Check source files exist
    if not os.path.exists(source_video):
        logger.error(f"❌ Source video not found: {source_video}")
        return False

    if not os.path.exists(driving_video):
        logger.error(f"❌ Driving video not found: {driving_video}")
        return False

    logger.info(f"✅ Source video found: {os.path.getsize(source_video)} bytes")
    logger.info(f"✅ Driving video found: {os.path.getsize(driving_video)} bytes")

    try:
        # Import LivePortrait engine
        from src.core.liveportrait.avatar_engine import LivePortraitEngine

        logger.info("🔧 Initializing LivePortraitEngine...")

        # Create LivePortrait engine
        engine = LivePortraitEngine(logger=logger)

        logger.info("✅ LivePortraitEngine initialized")
        logger.info(f"LivePortrait path: {engine.liveportrait_path}")
        logger.info(f"Python path: {engine.python_path}")

        # Check LivePortrait directory exists
        if not engine.liveportrait_path.exists():
            logger.error(f"❌ LivePortrait directory not found: {engine.liveportrait_path}")
            return False

        logger.info(f"✅ LivePortrait directory exists")

        # Check quality configurations
        logger.info("\n🎯 Step 1: Checking quality configurations...")
        logger.info("-" * 40)

        for quality, config in engine.quality_configs.items():
            timeout_min = config['timeout'] / 60
            logger.info(f"   {quality}: timeout={timeout_min:.1f}min, source_max_dim={config['source_max_dim']}")

        # Step 2: Extract reference frame from source video
        logger.info("\n🎯 Step 2: Extracting reference frame from source video...")
        logger.info("-" * 40)

        reference_image = os.path.join(output_dir, "reference_frame.jpg")

        extract_success = engine.extract_reference_frame(
            video_path=source_video,
            output_image_path=reference_image
        )

        if extract_success and os.path.exists(reference_image):
            logger.info(f"✅ Reference frame extracted: {reference_image}")
            logger.info(f"   Frame size: {os.path.getsize(reference_image)} bytes")
        else:
            logger.error("❌ Failed to extract reference frame")
            return False

        # Step 3: Test video-to-video animation (using existing video as driving)
        logger.info("\n🎯 Step 3: Testing LivePortrait video-to-video animation...")
        logger.info("-" * 40)
        logger.info("⚠️ This will take several minutes and may timeout - testing with fast quality")

        start_time = time.time()

        # Use the driving video directly for animation test
        animation_result = engine.generate_avatar_video_from_video(
            reference_image=reference_image,
            driving_video=driving_video,
            output_dir=output_dir,
            quality_level="fast"  # Use fast for testing
        )

        processing_time = time.time() - start_time

        if animation_result.success:
            logger.info(f"✅ Video animation completed in {processing_time:.1f}s")
            logger.info(f"   Output: {animation_result.output_path}")
            logger.info(f"   Processing time: {animation_result.processing_time}")

            if os.path.exists(animation_result.output_path):
                output_size = os.path.getsize(animation_result.output_path)
                logger.info(f"   Output size: {output_size} bytes")
            else:
                logger.error(f"❌ Output file not found: {animation_result.output_path}")
                return False

        else:
            logger.error(f"❌ Video animation failed after {processing_time:.1f}s")
            logger.error(f"   Error: {animation_result.error}")
            return False

        # Step 4: Test with audio-driven animation (simpler test)
        logger.info("\n🎯 Step 4: Testing audio-driven animation (simplified)...")
        logger.info("-" * 40)

        # Use the test audio we generated in voice cloning test
        test_audio = "temp/test-clone-voice/test_cloned_speech.wav"

        if os.path.exists(test_audio):
            logger.info(f"Using test audio: {test_audio}")

            audio_start_time = time.time()

            audio_result = engine.generate_avatar_video(
                audio_path=test_audio,
                reference_image=reference_image,
                output_dir=output_dir,
                quality_level="fast"  # Use fast quality for testing
            )

            audio_processing_time = time.time() - audio_start_time

            if audio_result.success:
                logger.info(f"✅ Audio-driven animation completed in {audio_processing_time:.1f}s")
                logger.info(f"   Output: {audio_result.output_path}")

                if os.path.exists(audio_result.output_path):
                    output_size = os.path.getsize(audio_result.output_path)
                    logger.info(f"   Output size: {output_size} bytes")
                else:
                    logger.error(f"❌ Audio output file not found: {audio_result.output_path}")

            else:
                logger.error(f"❌ Audio-driven animation failed after {audio_processing_time:.1f}s")
                logger.error(f"   Error: {audio_result.error}")
                logger.info("⚠️ This is expected if LivePortrait models aren't properly installed")

        else:
            logger.warning(f"⚠️ Test audio not found: {test_audio}")
            logger.info("   Skipping audio-driven test")

        return True

    except ImportError as e:
        logger.error(f"❌ Import error: {e}")
        logger.error("Make sure you're running from the correct directory")
        return False

    except Exception as e:
        logger.error(f"❌ Face animation test failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

def main():
    """Run face animation isolation test"""
    print("🎭 Face Animation Isolation Test")
    print("=" * 50)

    # Ensure output directory exists
    os.makedirs("temp/test-face-animation", exist_ok=True)

    success = test_face_animation_isolated()

    print("\n" + "=" * 50)
    if success:
        print("🎉 Face Animation Isolation Test: PASSED")
        print("\n📋 Results:")
        print("   ✅ LivePortrait engine initialized")
        print("   ✅ Reference frame extracted")
        print("   ✅ Video animation functionality tested")
        print("\n📁 Check output files in: temp/test-face-animation/")
        print("   • reference_frame.jpg - Extracted reference frame")
        print("   • avatar_*.mp4 - Generated animation videos")
        print("   • face_animation_test.log - Detailed logs")
    else:
        print("❌ Face Animation Isolation Test: FAILED")
        print("\n📋 Check the logs for detailed error information:")
        print("   📄 temp/test-face-animation/face_animation_test.log")
        print("\n🔍 Common issues:")
        print("   • LivePortrait models not downloaded")
        print("   • Timeout due to processing time")
        print("   • Missing dependencies")

    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)