#!/usr/bin/env python3
"""
Test the quality and engine used by the voice profile created from direct audio.
This will help determine if we're getting real voice cloning or Mac "say" fallback.
"""

import os
import sys
import json
import logging
from pathlib import Path

# Add the presgen-training2 src directory to Python path
sys.path.insert(0, "presgen-training2/src")

from modes.orchestrator import ModeOrchestrator

def main():
    """Test voice profile quality and engine"""

    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    logger = logging.getLogger("test_voice_profile_quality")

    print("🔍 PresGen-Training2: Voice Profile Quality Test")
    print("=" * 60)

    # Initialize orchestrator
    try:
        orchestrator = ModeOrchestrator()
        print("✅ ModeOrchestrator initialized successfully")
    except Exception as e:
        print(f"❌ Failed to initialize ModeOrchestrator: {e}")
        return False

    # Test profile name
    profile_name = "test_direct_audio_profile"

    # Check if profile exists
    profile = orchestrator.voice_manager.get_profile(profile_name)
    if not profile:
        print(f"❌ Profile '{profile_name}' not found")
        return False

    print(f"✅ Found profile: {profile_name}")
    print(f"📍 Language: {profile.language}")
    print(f"📅 Created: {profile.created_at}")
    print(f"🗂️  Model path: {profile.model_path}")

    # Examine the model file to see which engine was used
    try:
        if Path(profile.model_path).exists():
            with open(profile.model_path, 'r') as f:
                model_data = json.load(f)

            engine = model_data.get('engine', 'unknown')
            print(f"🔧 TTS Engine: {engine}")

            if engine == "elevenlabs":
                print(f"🎯 ElevenLabs Voice ID: {model_data.get('voice_id', 'N/A')}")
            elif engine == "openai":
                print(f"🎯 OpenAI Voice: {model_data.get('voice_name', 'N/A')}")
            elif engine == "builtin":
                print(f"⚠️  Using Mac 'say' command fallback")

            print(f"📂 Original audio: {model_data.get('audio_path', 'N/A')}")
        else:
            print(f"❌ Model file not found: {profile.model_path}")
            return False

    except Exception as e:
        print(f"❌ Error reading model file: {e}")
        return False

    # Generate test speech
    test_text = "Hello, this is a test of the voice cloning system using the provided audio sample."
    output_path = "temp/test_voice_output.wav"

    print(f"\n🎤 Testing voice synthesis...")
    print(f"Text: {test_text}")
    print(f"Output: {output_path}")

    try:
        success = orchestrator.voice_manager.synthesize_speech(
            text=test_text,
            profile_name=profile_name,
            output_path=output_path
        )

        if success and Path(output_path).exists():
            file_size = Path(output_path).stat().st_size / 1024  # Size in KB
            print(f"✅ Speech synthesis completed!")
            print(f"📊 Output file size: {file_size:.1f} KB")
            print(f"📁 Generated: {output_path}")

            # Analyze the audio file characteristics to detect if it's Mac "say" or real TTS
            # Mac "say" typically produces smaller files with specific characteristics
            if file_size < 50:  # Mac "say" typically produces very small files
                print(f"⚠️  Warning: Small file size suggests Mac 'say' fallback")
            else:
                print(f"✅ File size suggests real TTS engine")

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
        print("\n🎉 Voice profile quality test COMPLETED!")
        print("Check the generated audio file to verify voice quality.")
    else:
        print("\n💥 Voice profile quality test FAILED!")

    sys.exit(0 if success else 1)