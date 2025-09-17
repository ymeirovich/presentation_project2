#!/usr/bin/env python3
"""
Voice Cloning Isolation Test
Tests voice cloning functionality separately from avatar generation
"""

import sys
import os
import tempfile
import logging
from pathlib import Path

# Add the project root to the path
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent / "presgen-training2"))

def setup_logging():
    """Setup detailed logging for voice cloning test"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('temp/test-clone-voice/voice_cloning_test.log')
        ]
    )
    return logging.getLogger("voice_cloning_test")

def test_voice_cloning_isolated():
    """Test voice cloning in isolation"""
    logger = setup_logging()

    # Test parameters
    source_video = "/Users/yitzchak/Documents/learn/presentation_project/sales-agent-labs/examples/video/presgen_test.mp4"
    narration_text = "Hello, this is a test of a cloned voice from the reference video."
    output_dir = "temp/test-clone-voice"
    profile_name = "test_isolated_voice"

    logger.info("🎤 Starting Voice Cloning Isolation Test")
    logger.info("=" * 60)
    logger.info(f"Source video: {source_video}")
    logger.info(f"Narration text: {narration_text}")
    logger.info(f"Output directory: {output_dir}")
    logger.info(f"Profile name: {profile_name}")

    # Check source video exists
    if not os.path.exists(source_video):
        logger.error(f"❌ Source video not found: {source_video}")
        return False

    logger.info(f"✅ Source video found: {os.path.getsize(source_video)} bytes")

    try:
        # Import voice manager
        from src.core.voice.voice_manager import VoiceProfileManager

        logger.info("🔧 Initializing VoiceProfileManager...")

        # Create voice manager
        profiles_db = os.path.join(output_dir, "profiles.json")
        models_dir = os.path.join(output_dir, "models")

        voice_manager = VoiceProfileManager(
            profiles_db_path=profiles_db,
            models_dir=models_dir,
            logger=logger
        )

        logger.info("✅ VoiceProfileManager initialized")
        logger.info(f"Available engines: {list(voice_manager.tts_engines.keys())}")

        # Check engine availability
        for engine_name, engine_info in voice_manager.tts_engines.items():
            availability = "Available" if engine_info["available"] else "Not Available"
            logger.info(f"   {engine_name}: {availability}")

        # Step 1: Clone voice from video
        logger.info("\n🎯 Step 1: Cloning voice from reference video...")
        logger.info("-" * 40)

        cloned_profile = voice_manager.clone_voice_from_video(
            video_path=source_video,
            profile_name=profile_name,
            language="auto"
        )

        if cloned_profile:
            logger.info(f"✅ Voice cloned successfully: {cloned_profile.name}")
            logger.info(f"   Language: {cloned_profile.language}")
            logger.info(f"   Model path: {cloned_profile.model_path}")
            logger.info(f"   Source video: {cloned_profile.source_video}")
            logger.info(f"   Quality: {cloned_profile.quality}")
            logger.info(f"   Created: {cloned_profile.created_at}")
        else:
            logger.error("❌ Voice cloning failed")
            return False

        # Step 2: Generate speech with cloned voice
        logger.info("\n🎯 Step 2: Generating speech with cloned voice...")
        logger.info("-" * 40)

        output_audio = os.path.join(output_dir, "test_cloned_speech.wav")

        success = voice_manager.generate_speech(
            text=narration_text,
            voice_profile_name=profile_name,
            output_path=output_audio
        )

        if success and os.path.exists(output_audio):
            file_size = os.path.getsize(output_audio)
            logger.info(f"✅ Speech generated successfully: {output_audio}")
            logger.info(f"   File size: {file_size} bytes")
            logger.info(f"   Text: '{narration_text}'")

            # Test different engines if available
            logger.info("\n🎯 Step 3: Testing all available engines...")
            logger.info("-" * 40)

            for engine_name, engine_info in voice_manager.tts_engines.items():
                if engine_info["available"]:
                    test_output = os.path.join(output_dir, f"test_{engine_name}_speech.wav")
                    logger.info(f"Testing {engine_name} engine...")

                    # For testing, try to use the engine directly
                    if engine_name == "elevenlabs" and voice_manager._check_elevenlabs_availability():
                        logger.info("   ElevenLabs API available - would use real voice cloning")
                    elif engine_name == "openai" and voice_manager._check_openai_availability():
                        logger.info("   OpenAI TTS API available - would use voice synthesis")
                    else:
                        # Use the engine as fallback
                        test_success = voice_manager.generate_speech(
                            text="Testing " + engine_name + " engine.",
                            voice_profile_name=profile_name,
                            output_path=test_output
                        )
                        if test_success:
                            logger.info(f"   ✅ {engine_name} engine working")
                        else:
                            logger.info(f"   ⚠️ {engine_name} engine test failed")

            return True

        else:
            logger.error("❌ Speech generation failed")
            return False

    except ImportError as e:
        logger.error(f"❌ Import error: {e}")
        logger.error("Make sure you're running from the correct directory")
        return False

    except Exception as e:
        logger.error(f"❌ Voice cloning test failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

def main():
    """Run voice cloning isolation test"""
    print("🎤 Voice Cloning Isolation Test")
    print("=" * 50)

    # Ensure output directory exists
    os.makedirs("temp/test-clone-voice", exist_ok=True)

    success = test_voice_cloning_isolated()

    print("\n" + "=" * 50)
    if success:
        print("🎉 Voice Cloning Isolation Test: PASSED")
        print("\n📋 Results:")
        print("   ✅ Voice cloning functionality working")
        print("   ✅ Audio file generated successfully")
        print("   ✅ Voice profile created and stored")
        print("\n📁 Check output files in: temp/test-clone-voice/")
        print("   • test_cloned_speech.wav - Generated audio")
        print("   • voice_cloning_test.log - Detailed logs")
        print("   • profiles.json - Voice profile data")
    else:
        print("❌ Voice Cloning Isolation Test: FAILED")
        print("\n📋 Check the logs for detailed error information:")
        print("   📄 temp/test-clone-voice/voice_cloning_test.log")

    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)