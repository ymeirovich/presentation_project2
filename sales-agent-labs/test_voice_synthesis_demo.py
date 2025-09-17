#!/usr/bin/env python3
"""
Demo: Generate test sentence using OpenAI TTS with voice profile created from user's .wav file.
This will create an audio file with the requested test sentence.
"""

import os
import sys
import logging
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add the presgen-training2 src directory to Python path
sys.path.insert(0, "presgen-training2/src")

from modes.orchestrator import ModeOrchestrator

def main():
    """Generate test sentence with OpenAI TTS voice profile"""

    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    logger = logging.getLogger("test_voice_synthesis_demo")

    print("🎤 PresGen-Training2: Voice Synthesis Demo")
    print("=" * 60)

    # Initialize orchestrator
    try:
        orchestrator = ModeOrchestrator()
        print("✅ ModeOrchestrator initialized successfully")
    except Exception as e:
        print(f"❌ Failed to initialize ModeOrchestrator: {e}")
        return False

    # Demo parameters
    profile_name = "openai_demo_profile"  # The profile we created earlier
    test_sentence = "Hello, this is a test of a cloned voice using my voice"
    output_file = "temp/demo_voice_synthesis.mp3"

    # Check if profile exists
    profile = orchestrator.voice_manager.get_profile(profile_name)
    if not profile:
        print(f"❌ Voice profile not found: {profile_name}")
        print("💡 Run test_openai_voice_profile.py first to create the profile")
        return False

    print(f"✅ Found voice profile: {profile_name}")
    print(f"📍 Language: {profile.language}")
    print(f"📅 Created: {profile.created_at}")

    # Read profile details
    import json
    if Path(profile.model_path).exists():
        with open(profile.model_path, 'r') as f:
            model_data = json.load(f)

        engine = model_data.get('engine', 'unknown')
        voice_name = model_data.get('voice_name', 'N/A')
        print(f"🔧 Engine: {engine}")
        print(f"🎭 Voice: {voice_name}")
        print(f"🎵 Reference audio: {model_data.get('audio_path', 'N/A')}")

    # Generate speech
    print(f"\n🚀 Generating speech...")
    print(f"Text: \"{test_sentence}\"")
    print(f"Output: {output_file}")
    print(f"Expected cost: ~${len(test_sentence) * 0.000015:.5f}")

    try:
        # Ensure temp directory exists
        Path("temp").mkdir(exist_ok=True)

        success = orchestrator.voice_manager.synthesize_speech(
            text=test_sentence,
            profile_name=profile_name,
            output_path=output_file
        )

        if success and Path(output_file).exists():
            file_size = Path(output_file).stat().st_size / 1024  # Size in KB
            print(f"✅ Speech synthesis completed!")
            print(f"📁 Generated file: {output_file}")
            print(f"📊 File size: {file_size:.1f} KB")
            print(f"🎧 Play the audio to hear the result!")

            # Provide playback instructions
            abs_path = Path(output_file).resolve()
            print(f"\n💡 To play the audio:")
            print(f"   open \"{abs_path}\"")
            print(f"   or")
            print(f"   afplay \"{abs_path}\"")

            return True

        else:
            print(f"❌ Speech synthesis failed")
            return False

    except Exception as e:
        print(f"❌ Speech synthesis error: {e}")
        return False

if __name__ == "__main__":
    success = main()

    if success:
        print("\n🎉 Voice synthesis demo COMPLETED!")
        print("🎧 Your test sentence has been generated using OpenAI TTS")
        print("💡 Note: This uses OpenAI's 'alloy' voice, not true voice cloning")
    else:
        print("\n💥 Voice synthesis demo FAILED!")

    sys.exit(0 if success else 1)