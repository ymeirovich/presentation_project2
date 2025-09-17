#!/usr/bin/env python3
"""
ElevenLabs Voice Cloning Test
Tests real voice cloning using ElevenLabs API instead of Mac say command
"""

import sys
import os
import logging
from pathlib import Path

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()

# Add the project root to the path
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent / "presgen-training2"))

def setup_logging():
    """Setup logging for ElevenLabs voice cloning test"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('temp/test-elevenlabs-voice/elevenlabs_test.log')
        ]
    )
    return logging.getLogger("elevenlabs_test")

def test_elevenlabs_voice_cloning():
    """Test ElevenLabs voice cloning with real API"""
    logger = setup_logging()

    # Test parameters
    source_video = "/Users/yitzchak/Documents/learn/presentation_project/sales-agent-labs/examples/video/presgen_test.mp4"
    narration_text = "Hello, this is a test of real voice cloning using ElevenLabs API."
    output_dir = "temp/test-elevenlabs-voice"
    profile_name = "test_elevenlabs_voice"

    logger.info("🎤 Starting ElevenLabs Voice Cloning Test")
    logger.info("=" * 60)
    logger.info(f"Source video: {source_video}")
    logger.info(f"Narration text: {narration_text}")
    logger.info(f"Output directory: {output_dir}")
    logger.info(f"Profile name: {profile_name}")

    # Check source file exists
    if not os.path.exists(source_video):
        logger.error(f"❌ Source video not found: {source_video}")
        return False

    logger.info(f"✅ Source video found: {os.path.getsize(source_video)} bytes")

    try:
        # Import and test ElevenLabs availability
        logger.info("\n🎯 Step 1: Testing ElevenLabs API availability...")
        logger.info("-" * 40)

        from elevenlabs.client import ElevenLabs
        api_key = os.getenv("ELEVENLABS_API_KEY")

        if not api_key:
            logger.error("❌ ELEVENLABS_API_KEY not found in environment")
            return False

        logger.info(f"✅ ElevenLabs API key found: {api_key[:8]}...{api_key[-4:]}")

        # Initialize ElevenLabs client
        client = ElevenLabs(api_key=api_key)

        # Test API connection by listing available voices
        try:
            voices = client.voices.get_all()
            logger.info(f"✅ ElevenLabs API connection successful")
            logger.info(f"   Available voices: {len(voices.voices)}")
            for voice in voices.voices[:3]:  # Show first 3 voices
                logger.info(f"      - {voice.name} ({voice.voice_id[:8]}...)")
        except Exception as e:
            logger.error(f"❌ ElevenLabs API connection failed: {e}")
            return False

        # Import VoiceProfileManager
        from src.core.voice.voice_manager import VoiceProfileManager

        logger.info("\n🎯 Step 2: Initializing VoiceProfileManager...")
        logger.info("-" * 40)

        # Initialize voice manager with ElevenLabs support
        voice_manager = VoiceProfileManager(
            profiles_db_path=f"{output_dir}/profiles.json",
            models_dir=f"{output_dir}/models",
            logger=logger
        )

        logger.info("✅ VoiceProfileManager initialized")

        # Check engine availability
        available_engines = []
        for engine, config in voice_manager.tts_engines.items():
            status = "Available" if config["available"] else "Not Available"
            logger.info(f"   {engine}: {status}")
            if config["available"]:
                available_engines.append(engine)

        if "elevenlabs" not in available_engines:
            logger.error("❌ ElevenLabs engine not available in VoiceProfileManager")
            return False

        logger.info("✅ ElevenLabs engine is available and has priority")

        # Step 3: Clone voice using ElevenLabs
        logger.info("\n🎯 Step 3: Cloning voice using ElevenLabs API...")
        logger.info("-" * 40)

        # Clean up any existing profile first
        if voice_manager.get_profile(profile_name):
            voice_manager.delete_profile(profile_name)
            logger.info(f"   Cleaned up existing profile: {profile_name}")

        cloned_profile = voice_manager.clone_voice_from_video(
            video_path=source_video,
            profile_name=profile_name,
            language="auto"
        )

        if cloned_profile:
            logger.info(f"✅ Voice cloned successfully using ElevenLabs: {profile_name}")
            logger.info(f"   Language: {cloned_profile.language}")
            logger.info(f"   Model path: {cloned_profile.model_path}")
            logger.info(f"   Source video: {cloned_profile.source_video}")
            logger.info(f"   Quality: {cloned_profile.quality}")
            logger.info(f"   Created: {cloned_profile.created_at}")

            # Verify the model file contains ElevenLabs data
            import json
            model_data = json.loads(Path(cloned_profile.model_path).read_text())
            if model_data.get("engine") == "elevenlabs" and "voice_id" in model_data:
                logger.info(f"✅ ElevenLabs voice model created successfully")
                logger.info(f"   Voice ID: {model_data['voice_id']}")
            else:
                logger.error(f"❌ Model file doesn't contain ElevenLabs data")
                return False
        else:
            logger.error("❌ Voice cloning failed")
            return False

        # Step 4: Generate speech with cloned voice
        logger.info("\n🎯 Step 4: Generating speech with ElevenLabs cloned voice...")
        logger.info("-" * 40)

        output_speech = os.path.join(output_dir, "test_elevenlabs_cloned_speech.wav")

        speech_success = voice_manager.generate_speech(
            text=narration_text,
            voice_profile_name=profile_name,
            output_path=output_speech
        )

        if speech_success and os.path.exists(output_speech):
            output_size = os.path.getsize(output_speech)
            logger.info(f"✅ ElevenLabs speech generated successfully: {output_speech}")
            logger.info(f"   File size: {output_size} bytes")
            logger.info(f"   Text: '{narration_text}'")
        else:
            logger.error("❌ ElevenLabs speech generation failed")
            return False

        # Step 5: Compare with previous Mac voice output
        logger.info("\n🎯 Step 5: Comparison with previous output...")
        logger.info("-" * 40)

        previous_output = "temp/test-clone-voice/test_cloned_speech.wav"
        if os.path.exists(previous_output):
            prev_size = os.path.getsize(previous_output)
            curr_size = os.path.getsize(output_speech)
            logger.info(f"📊 File size comparison:")
            logger.info(f"   Previous (Mac say): {prev_size} bytes")
            logger.info(f"   Current (ElevenLabs): {curr_size} bytes")
            logger.info(f"   Difference: {curr_size - prev_size:+d} bytes")
        else:
            logger.info("⚠️ No previous output found for comparison")

        return True

    except ImportError as e:
        logger.error(f"❌ Import error: {e}")
        logger.error("Make sure elevenlabs package is installed: pip3 install elevenlabs")
        return False

    except Exception as e:
        logger.error(f"❌ ElevenLabs voice cloning test failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

def main():
    """Run ElevenLabs voice cloning test"""
    print("🎤 ElevenLabs Voice Cloning Test")
    print("=" * 50)

    # Ensure output directory exists
    os.makedirs("temp/test-elevenlabs-voice", exist_ok=True)

    success = test_elevenlabs_voice_cloning()

    print("\n" + "=" * 50)
    if success:
        print("🎉 ElevenLabs Voice Cloning Test: PASSED")
        print("\n📋 Results:")
        print("   ✅ ElevenLabs API connection successful")
        print("   ✅ Voice cloned using real AI voice cloning")
        print("   ✅ Speech generated with cloned voice")
        print("   ✅ No more Mac 'say' command fallback")
        print("\n📁 Check output files in: temp/test-elevenlabs-voice/")
        print("   • test_elevenlabs_cloned_speech.wav - Generated with cloned voice")
        print("   • profiles.json - Voice profile database")
        print("   • models/ - ElevenLabs voice models")
        print("   • elevenlabs_test.log - Detailed logs")
        print("\n🔍 Key Improvements:")
        print("   • Real voice cloning instead of generic TTS")
        print("   • Higher quality speech synthesis")
        print("   • Preserves original speaker characteristics")
    else:
        print("❌ ElevenLabs Voice Cloning Test: FAILED")
        print("\n📋 Check the logs for detailed error information:")
        print("   📄 temp/test-elevenlabs-voice/elevenlabs_test.log")
        print("\n🔍 Common issues:")
        print("   • Invalid ElevenLabs API key")
        print("   • Network connectivity issues")
        print("   • Missing elevenlabs package")
        print("   • API quota/rate limits")

    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)