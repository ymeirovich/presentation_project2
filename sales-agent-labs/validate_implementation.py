#!/usr/bin/env python3
"""
Simple validation of voice cloning implementation
"""

import sys
import os
from pathlib import Path

def validate_files_exist():
    """Check that key implementation files exist"""
    print("🔍 Checking implementation files...")

    files_to_check = [
        "presgen-training2/src/core/voice/voice_manager.py",
        "presgen-training2/src/core/liveportrait/avatar_engine.py",
        "requirements.txt"
    ]

    all_exist = True
    for file_path in files_to_check:
        if Path(file_path).exists():
            print(f"✅ {file_path}")
        else:
            print(f"❌ {file_path} - Missing")
            all_exist = False

    return all_exist

def validate_dependencies():
    """Check that new dependencies are installed"""
    print("\n🔍 Checking dependencies...")

    dependencies = ["elevenlabs", "openai", "pydub"]
    all_available = True

    for dep in dependencies:
        try:
            __import__(dep)
            print(f"✅ {dep} - Installed")
        except ImportError:
            print(f"❌ {dep} - Not installed")
            all_available = False

    return all_available

def validate_requirements_file():
    """Check that requirements.txt contains new dependencies"""
    print("\n🔍 Checking requirements.txt...")

    try:
        with open("requirements.txt", "r") as f:
            content = f.read()

        required_deps = ["elevenlabs", "openai", "pydub"]
        found_deps = []

        for dep in required_deps:
            if dep in content:
                print(f"✅ {dep} - Found in requirements.txt")
                found_deps.append(dep)
            else:
                print(f"❌ {dep} - Missing from requirements.txt")

        return len(found_deps) == len(required_deps)

    except FileNotFoundError:
        print("❌ requirements.txt not found")
        return False

def validate_voice_manager_changes():
    """Check that voice manager contains new implementations"""
    print("\n🔍 Checking voice manager implementation...")

    try:
        with open("presgen-training2/src/core/voice/voice_manager.py", "r") as f:
            content = f.read()

        checks = [
            ("ElevenLabs integration", "elevenlabs" in content and "_train_elevenlabs_model" in content),
            ("OpenAI integration", "openai" in content and "_train_openai_model" in content),
            ("Audio extraction", "_extract_audio_from_video" in content),
            ("Audio validation", "_validate_audio_for_cloning" in content),
            ("ElevenLabs speech generation", "_generate_elevenlabs_speech" in content),
            ("OpenAI speech generation", "_generate_openai_speech" in content),
        ]

        all_passed = True
        for check_name, condition in checks:
            if condition:
                print(f"✅ {check_name}")
            else:
                print(f"❌ {check_name}")
                all_passed = False

        return all_passed

    except FileNotFoundError:
        print("❌ Voice manager file not found")
        return False

def validate_avatar_engine_changes():
    """Check that avatar engine contains optimizations"""
    print("\n🔍 Checking avatar engine optimizations...")

    try:
        with open("presgen-training2/src/core/liveportrait/avatar_engine.py", "r") as f:
            content = f.read()

        checks = [
            ("Face cropping enabled", "--flag-crop-driving-video" in content),
            ("Smooth animation", "--flag-smooth" in content),
            ("Avatar post-processing", "_post_process_avatar_video" in content),
            ("Fixed dimensions", "driving_max_dim" in content),
            ("FPS configuration", '"fps"' in content),
        ]

        all_passed = True
        for check_name, condition in checks:
            if condition:
                print(f"✅ {check_name}")
            else:
                print(f"❌ {check_name}")
                all_passed = False

        return all_passed

    except FileNotFoundError:
        print("❌ Avatar engine file not found")
        return False

def main():
    """Run all validation checks"""
    print("🔧 Voice Cloning Implementation Validation")
    print("=" * 50)

    tests = [
        ("Files exist", validate_files_exist),
        ("Dependencies installed", validate_dependencies),
        ("Requirements.txt updated", validate_requirements_file),
        ("Voice manager changes", validate_voice_manager_changes),
        ("Avatar engine changes", validate_avatar_engine_changes),
    ]

    passed = 0
    total = len(tests)

    for test_name, test_func in tests:
        print(f"\n📋 {test_name}")
        print("-" * 30)

        if test_func():
            passed += 1

    print("\n" + "=" * 50)
    print(f"📊 Validation Results: {passed}/{total} checks passed")

    if passed == total:
        print("🎉 All implementation checks passed!")
        print("   Ready for git commit and API testing.")
    else:
        print("⚠️  Some checks failed. Please review the implementation.")

    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)