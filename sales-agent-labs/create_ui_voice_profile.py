#!/usr/bin/env python3
"""
Create a UI-compatible voice profile for dropdown selection.
This creates a properly named profile that will appear nicely in the PresGen Training UI.
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
    """Create UI-compatible voice profile"""

    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    logger = logging.getLogger("create_ui_voice_profile")

    print("🎤 PresGen-Training2: Create UI Voice Profile")
    print("=" * 60)

    # Initialize orchestrator
    try:
        orchestrator = ModeOrchestrator()
        print("✅ ModeOrchestrator initialized successfully")
    except Exception as e:
        print(f"❌ Failed to initialize ModeOrchestrator: {e}")
        return False

    # Profile parameters for UI
    audio_file = "./presgen-training2/temp/enhanced_audio_35f2b2fa2dcb.wav"
    profile_name = "OpenAI Demo Voice (Your Audio)"  # Professional name for UI
    language = "en"

    # Verify audio file exists
    if not Path(audio_file).exists():
        print(f"❌ Audio file not found: {audio_file}")
        return False

    file_size = Path(audio_file).stat().st_size / 1024
    print(f"🎵 Found audio file: {audio_file} ({file_size:.1f} KB)")

    # Delete existing profile if it exists
    if orchestrator.voice_manager.get_profile(profile_name):
        print(f"🗑️  Removing existing profile: {profile_name}")
        orchestrator.voice_manager.delete_profile(profile_name)

    # Create new UI-friendly profile
    print(f"\n🚀 Creating UI voice profile...")
    print(f"Name: {profile_name}")
    print(f"Language: {language}")
    print(f"Engine: OpenAI TTS (alloy voice)")

    try:
        success = orchestrator.clone_voice_from_audio(
            audio_path=audio_file,
            profile_name=profile_name,
            language=language
        )

        if success:
            print(f"✅ UI voice profile created successfully!")

            # Verify the profile
            profile = orchestrator.voice_manager.get_profile(profile_name)
            if profile:
                print(f"\n📋 Profile Details:")
                print(f"  Name: {profile.name}")
                print(f"  Language: {profile.language}")
                print(f"  Created: {profile.created_at}")
                print(f"  Source: {profile.source_video}")

                # Show how it will appear in UI
                from datetime import datetime
                created_date = datetime.fromisoformat(profile.created_at).strftime("%m/%d/%Y")
                print(f"\n🖥️  UI Dropdown Display:")
                print(f"  {profile.name} (Created: {created_date})")

            # List all available profiles
            profiles = orchestrator.voice_manager.list_profiles()
            print(f"\n📋 All Available Voice Profiles ({len(profiles)}):")
            for profile_dict in profiles:
                created_date = datetime.fromisoformat(profile_dict['created_at']).strftime("%m/%d/%Y")
                print(f"  • {profile_dict['name']} (Created: {created_date})")

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
        print("\n🎉 UI Voice Profile Created Successfully!")
        print("💡 This profile is now available in the PresGen Training UI dropdown")
        print("🔧 Profile uses OpenAI TTS with your audio file as reference")
    else:
        print("\n💥 UI Voice Profile Creation Failed!")

    sys.exit(0 if success else 1)