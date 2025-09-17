#!/usr/bin/env python3
"""
Test script for direct audio voice cloning using the provided enhanced audio file.
This bypasses video extraction and uses the existing .wav file directly.
"""

import os
import sys
import logging
from pathlib import Path

# Add the presgen-training2 src directory to Python path
sys.path.insert(0, "presgen-training2/src")

from modes.orchestrator import ModeOrchestrator

def main():
    """Test direct audio voice cloning functionality"""

    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    logger = logging.getLogger("test_direct_audio_cloning")

    print("🎤 PresGen-Training2: Direct Audio Voice Cloning Test")
    print("=" * 60)

    # Initialize orchestrator
    try:
        orchestrator = ModeOrchestrator()
        print("✅ ModeOrchestrator initialized successfully")
    except Exception as e:
        print(f"❌ Failed to initialize ModeOrchestrator: {e}")
        return False

    # Test parameters
    audio_file = "./presgen-training2/temp/enhanced_audio_35f2b2fa2dcb.wav"
    profile_name = "test_direct_audio_profile"
    language = "auto"  # Auto-detect language

    # Verify audio file exists
    if not Path(audio_file).exists():
        print(f"❌ Audio file not found: {audio_file}")
        return False

    file_size = Path(audio_file).stat().st_size / 1024  # Size in KB
    print(f"🎵 Found audio file: {audio_file}")
    print(f"📊 File size: {file_size:.1f} KB")

    # Attempt direct audio voice cloning
    print(f"\n🚀 Starting direct audio voice cloning...")
    print(f"Profile name: {profile_name}")
    print(f"Language: {language}")
    print(f"Audio file: {audio_file}")

    try:
        success = orchestrator.clone_voice_from_audio(
            audio_path=audio_file,
            profile_name=profile_name,
            language=language
        )

        if success:
            print(f"✅ Voice cloning completed successfully!")
            print(f"✅ Voice profile '{profile_name}' created")

            # List available voice profiles
            profiles = orchestrator.voice_manager.list_profiles()
            if profiles:
                print(f"\n📋 Available voice profiles:")
                for profile_dict in profiles:
                    print(f"  - {profile_dict['name']}: {profile_dict['language']} (created: {profile_dict['created_at']})")

            return True

        else:
            print(f"❌ Voice cloning failed")
            return False

    except Exception as e:
        print(f"❌ Voice cloning error: {e}")
        return False

if __name__ == "__main__":
    success = main()

    if success:
        print("\n🎉 Direct audio voice cloning test PASSED!")
    else:
        print("\n💥 Direct audio voice cloning test FAILED!")

    sys.exit(0 if success else 1)