#!/usr/bin/env python3
"""
Test OpenAI voice profile creation using the provided .wav file.
This will create a profile that uses the closest OpenAI voice.
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
    """Test OpenAI voice profile creation with quota monitoring"""

    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    logger = logging.getLogger("test_openai_voice_profile")

    print("🎤 PresGen-Training2: OpenAI Voice Profile Test")
    print("=" * 60)

    # Initialize orchestrator
    try:
        orchestrator = ModeOrchestrator()
        print("✅ ModeOrchestrator initialized successfully")
    except Exception as e:
        print(f"❌ Failed to initialize ModeOrchestrator: {e}")
        return False

    # Check TTS engine priority
    engines = orchestrator.voice_manager.tts_engines
    print(f"\n🔧 TTS Engine Priority:")
    sorted_engines = sorted(engines.items(), key=lambda x: x[1]['priority'])
    for name, config in sorted_engines:
        status = "✅" if config['available'] else "❌"
        print(f"  {config['priority']}. {status} {name}")

    best_engine = orchestrator.voice_manager._get_best_tts_engine()
    print(f"🏆 Selected engine: {best_engine}")

    # Test parameters
    audio_file = "./presgen-training2/temp/enhanced_audio_35f2b2fa2dcb.wav"
    profile_name = "openai_demo_profile"
    language = "auto"

    # Verify audio file exists
    if not Path(audio_file).exists():
        print(f"❌ Audio file not found: {audio_file}")
        return False

    file_size = Path(audio_file).stat().st_size / 1024  # Size in KB
    print(f"\n🎵 Found audio file: {audio_file}")
    print(f"📊 File size: {file_size:.1f} KB")

    # Delete existing profile if it exists
    if orchestrator.voice_manager.get_profile(profile_name):
        print(f"🗑️  Removing existing profile: {profile_name}")
        orchestrator.voice_manager.delete_profile(profile_name)

    # Create OpenAI voice profile
    print(f"\n🚀 Creating OpenAI voice profile...")
    print(f"Profile name: {profile_name}")
    print(f"Language: {language}")
    print(f"Expected engine: OpenAI TTS (with quota monitoring)")

    try:
        success = orchestrator.clone_voice_from_audio(
            audio_path=audio_file,
            profile_name=profile_name,
            language=language
        )

        if success:
            print(f"✅ Voice profile created successfully!")

            # Examine the created profile
            profile = orchestrator.voice_manager.get_profile(profile_name)
            if profile:
                print(f"\n📋 Profile Details:")
                print(f"  Name: {profile.name}")
                print(f"  Language: {profile.language}")
                print(f"  Model path: {profile.model_path}")
                print(f"  Source: {profile.source_video}")

                # Check which engine was actually used
                if Path(profile.model_path).exists():
                    import json
                    with open(profile.model_path, 'r') as f:
                        model_data = json.load(f)

                    engine = model_data.get('engine', 'unknown')
                    print(f"  Engine used: {engine}")

                    if engine == "openai":
                        voice_name = model_data.get('voice_name', 'N/A')
                        print(f"  OpenAI voice: {voice_name}")
                        print(f"  ✅ OpenAI TTS configured successfully!")
                    else:
                        print(f"  ⚠️  Expected OpenAI but got: {engine}")

            return True

        else:
            print(f"❌ Voice profile creation failed")
            return False

    except Exception as e:
        print(f"❌ Voice profile creation error: {e}")
        return False

if __name__ == "__main__":
    success = main()

    if success:
        print("\n🎉 OpenAI voice profile test PASSED!")
        print("💡 Ready for demo with OpenAI TTS + LivePortrait face animation")
    else:
        print("\n💥 OpenAI voice profile test FAILED!")

    sys.exit(0 if success else 1)