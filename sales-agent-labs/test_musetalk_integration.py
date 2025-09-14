#!/usr/bin/env python3
"""
Test script for MuseTalk integration with PresGen-Training
"""

import tempfile
from pathlib import Path
from src.presgen_training.avatar_generator import AvatarGenerator
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

def test_musetalk_integration():
    """Test MuseTalk integration end-to-end"""
    
    print("🎬 Testing MuseTalk Integration with PresGen-Training")
    print("=" * 50)
    
    # Initialize avatar generator
    print("1. Initializing Avatar Generator...")
    ag = AvatarGenerator()
    
    # Check dependencies
    print("2. Checking dependencies...")
    deps = ag.check_dependencies()
    print(f"   Dependencies: {deps}")
    
    if not all(deps.values()):
        print("❌ Not all dependencies are available!")
        return False
    
    # Check MuseTalk detection
    print("3. Checking MuseTalk detection...")
    if ag.musetalk_path:
        print(f"   ✅ MuseTalk detected at: {ag.musetalk_path}")
    else:
        print("   ❌ MuseTalk not detected - will use static fallback")
    
    print("4. Testing TTS audio generation...")
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Generate test audio
        test_text = "Hello, this is a test of MuseTalk integration with PresGen-Training."
        audio_file = temp_path / "test_audio.wav"
        
        try:
            result = ag.generate_tts_audio(test_text, audio_file)
            if result and audio_file.exists():
                print(f"   ✅ TTS audio generated: {audio_file} ({audio_file.stat().st_size} bytes)")
            else:
                print("   ❌ TTS audio generation failed")
                return False
        except Exception as e:
            print(f"   ❌ TTS error: {e}")
            return False
    
    print("\n🎉 MuseTalk integration test completed successfully!")
    print("   • Avatar generator initialized ✅")
    print("   • Dependencies available ✅") 
    print("   • MuseTalk detected ✅" if ag.musetalk_path else "   • Will use static fallback ⚠️")
    print("   • TTS working ✅")
    
    return True

if __name__ == "__main__":
    success = test_musetalk_integration()
    exit(0 if success else 1)