#!/usr/bin/env python3
"""
End-to-End Demo: OpenAI TTS + LivePortrait Face Animation
This creates a complete avatar video using:
1. OpenAI TTS for speech generation (using voice profile from user's .wav)
2. LivePortrait for face animation sync to the generated speech
3. Original reference video as the face source

Output: Complete avatar video with the test sentence
"""

import os
import sys
import logging
import time
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add the presgen-training2 src directory to Python path
sys.path.insert(0, "presgen-training2/src")

from modes.orchestrator import ModeOrchestrator

def main():
    """Complete E2E demo: OpenAI TTS + LivePortrait animation"""

    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    logger = logging.getLogger("e2e_openai_liveportrait_demo")

    print("🎬 PresGen-Training2: E2E OpenAI + LivePortrait Demo")
    print("=" * 70)

    # Initialize orchestrator
    try:
        orchestrator = ModeOrchestrator()
        print("✅ ModeOrchestrator initialized successfully")
    except Exception as e:
        print(f"❌ Failed to initialize ModeOrchestrator: {e}")
        return False

    # Demo parameters
    profile_name = "openai_demo_profile"
    test_sentence = "Hello, this is a test of a cloned voice using my voice"

    # Use the original reference video that corresponds to your .wav file
    reference_video = "sadtalker-api/examples/presgen_test2.mp4"  # This should be your original video

    if not Path(reference_video).exists():
        print(f"❌ Reference video not found: {reference_video}")
        return False

    # Output paths
    temp_audio = "temp/e2e_demo_audio.mp3"
    final_video = "temp/e2e_demo_final_avatar.mp4"

    # Ensure temp directory exists
    Path("temp").mkdir(exist_ok=True)

    print(f"\n📋 Demo Configuration:")
    print(f"  Voice Profile: {profile_name}")
    print(f"  Test Sentence: \"{test_sentence}\"")
    print(f"  Reference Video: {reference_video}")
    print(f"  Temp Audio: {temp_audio}")
    print(f"  Final Output: {final_video}")

    # Step 1: Generate speech using OpenAI TTS
    print(f"\n🎤 Step 1: Generating speech with OpenAI TTS...")

    try:
        start_time = time.time()

        success = orchestrator.voice_manager.synthesize_speech(
            text=test_sentence,
            profile_name=profile_name,
            output_path=temp_audio
        )

        if not success or not Path(temp_audio).exists():
            print(f"❌ Speech generation failed")
            return False

        audio_size = Path(temp_audio).stat().st_size / 1024
        speech_time = time.time() - start_time

        print(f"✅ Speech generated successfully!")
        print(f"   File: {temp_audio} ({audio_size:.1f} KB)")
        print(f"   Time: {speech_time:.1f}s")

    except Exception as e:
        print(f"❌ Speech generation error: {e}")
        return False

    # Step 2: Extract reference frame from video
    print(f"\n🖼️  Step 2: Extracting reference frame from video...")

    reference_image = "temp/reference_frame.jpg"
    try:
        # Extract reference frame using the avatar engine
        success = orchestrator.avatar_engine.extract_reference_frame(
            video_path=reference_video,
            output_image_path=reference_image
        )

        if not success or not Path(reference_image).exists():
            print(f"❌ Reference frame extraction failed")
            return False

        print(f"✅ Reference frame extracted: {reference_image}")

    except Exception as e:
        print(f"❌ Reference frame extraction error: {e}")
        return False

    # Step 3: Create avatar video with LivePortrait
    print(f"\n🎭 Step 3: Creating avatar animation with LivePortrait...")
    print(f"   This may take 10-20 minutes depending on audio length...")

    try:
        start_time = time.time()

        # Use the avatar generation method with correct parameters
        avatar_result = orchestrator.avatar_engine.generate_avatar_video(
            audio_path=temp_audio,
            reference_image=reference_image,
            output_dir="temp",
            quality_level="standard"  # Use standard quality for faster processing
        )

        success = avatar_result and avatar_result.success

        if success and avatar_result.video_path:
            # Move the output to our desired location
            generated_video = avatar_result.video_path
            if Path(generated_video).exists():
                import shutil
                shutil.move(generated_video, final_video)
            else:
                success = False

        if not success or not Path(final_video).exists():
            print(f"❌ Avatar video generation failed")
            if avatar_result and hasattr(avatar_result, 'error'):
                print(f"   Error: {avatar_result.error}")
            return False

        video_size = Path(final_video).stat().st_size / (1024 * 1024)  # MB
        animation_time = time.time() - start_time

        print(f"✅ Avatar video generated successfully!")
        print(f"   File: {final_video} ({video_size:.1f} MB)")
        print(f"   Time: {animation_time:.1f}s ({animation_time/60:.1f} minutes)")

    except Exception as e:
        print(f"❌ Avatar video generation error: {e}")
        return False

    # Step 3: Display final results
    print(f"\n🎉 E2E Demo Completed Successfully!")
    print(f"=" * 50)
    print(f"📁 Final Output: {final_video}")
    print(f"📊 Video Size: {video_size:.1f} MB")
    print(f"⏱️  Total Time: {(speech_time + animation_time):.1f}s")
    print(f"💰 OpenAI Cost: ~${len(test_sentence) * 0.000015:.5f}")

    # Provide playback instructions
    abs_path = Path(final_video).resolve()
    print(f"\n💡 To view the final avatar video:")
    print(f"   open \"{abs_path}\"")
    print(f"   or")
    print(f"   vlc \"{abs_path}\"")

    print(f"\n🔍 Demo Components:")
    print(f"   🎤 Speech: OpenAI TTS (alloy voice)")
    print(f"   🎭 Animation: LivePortrait face sync")
    print(f"   🎵 Reference: Your original .wav file")
    print(f"   🎬 Result: Animated avatar speaking your test sentence")

    return True

if __name__ == "__main__":
    success = main()

    if success:
        print("\n🚀 E2E Demo SUCCESSFUL!")
        print("🎬 Your avatar video is ready for viewing!")
    else:
        print("\n💥 E2E Demo FAILED!")
        print("Check the logs above for error details.")

    sys.exit(0 if success else 1)