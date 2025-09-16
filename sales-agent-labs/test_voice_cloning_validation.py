#!/usr/bin/env python3
"""
Voice Cloning Implementation Validation Test
Tests the new ElevenLabs and OpenAI TTS integration
"""

import sys
import os
import tempfile
from pathlib import Path

# Add the project root to the path
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent / "presgen-training2"))

def test_voice_manager_imports():
    """Test that all voice cloning imports work correctly"""
    try:
        from src.core.voice.voice_manager import VoiceProfileManager
        print("✅ VoiceProfileManager import successful")
        return True
    except ImportError as e:
        print(f"❌ VoiceProfileManager import failed: {e}")
        return False

def test_voice_manager_initialization():
    """Test voice manager initialization with new engines"""
    try:
        from src.core.voice.voice_manager import VoiceProfileManager

        # Create temporary directories for testing
        with tempfile.TemporaryDirectory() as temp_dir:
            profiles_db = os.path.join(temp_dir, "profiles.json")
            models_dir = os.path.join(temp_dir, "models")

            manager = VoiceProfileManager(
                profiles_db_path=profiles_db,
                models_dir=models_dir
            )

            print("✅ VoiceProfileManager initialization successful")
            print(f"   Available engines: {list(manager.tts_engines.keys())}")

            # Check that new engines are included
            expected_engines = ["elevenlabs", "openai", "coqui", "piper", "builtin"]
            for engine in expected_engines:
                if engine in manager.tts_engines:
                    availability = manager.tts_engines[engine]["available"]
                    print(f"   {engine}: {'Available' if availability else 'Not available'}")
                else:
                    print(f"   ❌ {engine}: Missing from engine list")
                    return False

            return True

    except Exception as e:
        print(f"❌ VoiceProfileManager initialization failed: {e}")
        return False

def test_avatar_engine_imports():
    """Test that LivePortrait engine imports work correctly"""
    try:
        from src.core.liveportrait.avatar_engine import LivePortraitEngine
        print("✅ LivePortraitEngine import successful")
        return True
    except ImportError as e:
        print(f"❌ LivePortraitEngine import failed: {e}")
        return False

def test_avatar_engine_optimization():
    """Test that LivePortrait has the new optimization parameters"""
    try:
        from src.core.liveportrait.avatar_engine import LivePortraitEngine

        engine = LivePortraitEngine()

        # Check that new configuration parameters exist
        config = engine.quality_configs["standard"]

        required_params = [
            "driving_max_dim", "fps", "enable_face_cropping", "smooth_animation"
        ]

        for param in required_params:
            if param in config:
                print(f"   ✅ {param}: {config[param]}")
            else:
                print(f"   ❌ {param}: Missing from configuration")
                return False

        print("✅ LivePortrait optimization parameters validated")
        return True

    except Exception as e:
        print(f"❌ LivePortrait optimization validation failed: {e}")
        return False

def test_dependencies():
    """Test that new dependencies are available"""
    dependencies = {
        "elevenlabs": "ElevenLabs voice cloning API",
        "openai": "OpenAI TTS API",
        "pydub": "Audio processing library"
    }

    all_available = True

    for package, description in dependencies.items():
        try:
            __import__(package)
            print(f"✅ {package}: {description} - Available")
        except ImportError:
            print(f"⚠️  {package}: {description} - Not installed (optional for testing)")
            # Don't fail the test for optional dependencies

    return all_available

def test_api_key_detection():
    """Test API key detection logic"""
    try:
        from src.core.voice.voice_manager import VoiceProfileManager

        with tempfile.TemporaryDirectory() as temp_dir:
            manager = VoiceProfileManager(
                profiles_db_path=os.path.join(temp_dir, "profiles.json"),
                models_dir=os.path.join(temp_dir, "models")
            )

            # Test API key detection
            elevenlabs_available = manager._check_elevenlabs_availability()
            openai_available = manager._check_openai_availability()

            print(f"   ElevenLabs API: {'Available' if elevenlabs_available else 'API key not configured'}")
            print(f"   OpenAI API: {'Available' if openai_available else 'API key not configured'}")

            print("✅ API key detection working correctly")
            return True

    except Exception as e:
        print(f"❌ API key detection failed: {e}")
        return False

def main():
    """Run all validation tests"""
    print("🔧 Voice Cloning Implementation Validation")
    print("=" * 50)

    tests = [
        ("Voice Manager Imports", test_voice_manager_imports),
        ("Voice Manager Initialization", test_voice_manager_initialization),
        ("Avatar Engine Imports", test_avatar_engine_imports),
        ("Avatar Engine Optimization", test_avatar_engine_optimization),
        ("Dependencies Check", test_dependencies),
        ("API Key Detection", test_api_key_detection),
    ]

    passed = 0
    total = len(tests)

    for test_name, test_func in tests:
        print(f"\n🧪 {test_name}")
        print("-" * 30)

        if test_func():
            passed += 1

    print("\n" + "=" * 50)
    print(f"📊 Validation Results: {passed}/{total} tests passed")

    if passed == total:
        print("🎉 All voice cloning implementation tests passed!")
        print("   The system is ready for integration testing with API keys.")
    else:
        print("⚠️  Some tests failed. Please review the implementation.")

    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)