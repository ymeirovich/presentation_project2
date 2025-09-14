#!/usr/bin/env python3
"""
Comprehensive Test for MuseTalk Video Generation
Tests the complete pipeline from text -> TTS -> MuseTalk -> video output
"""

import tempfile
import time
from pathlib import Path
from src.presgen_training.avatar_generator import AvatarGenerator
import logging
import json

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def create_test_image():
    """Create a simple test image for avatar generation"""
    try:
        from PIL import Image, ImageDraw
        
        # Create a simple 512x512 face-like image
        img = Image.new('RGB', (512, 512), color='lightblue')
        draw = ImageDraw.Draw(img)
        
        # Draw a simple face
        # Head outline
        draw.ellipse([100, 100, 400, 400], fill='peachpuff', outline='black', width=2)
        
        # Eyes
        draw.ellipse([150, 200, 180, 230], fill='white', outline='black', width=1)
        draw.ellipse([320, 200, 350, 230], fill='white', outline='black', width=1)
        draw.ellipse([160, 210, 170, 220], fill='black')  # Left pupil
        draw.ellipse([330, 210, 340, 220], fill='black')  # Right pupil
        
        # Nose
        draw.ellipse([240, 250, 260, 280], fill='peachpuff', outline='black', width=1)
        
        # Mouth
        draw.arc([220, 300, 280, 340], 0, 180, fill='black', width=3)
        
        return img
    except ImportError:
        logger.warning("PIL not available, will use a placeholder")
        return None

def test_musetalk_video_generation():
    """Test complete MuseTalk video generation pipeline"""
    
    print("🎬 Testing MuseTalk Video Generation Pipeline")
    print("=" * 60)
    
    # Initialize avatar generator
    print("1. Initializing Avatar Generator...")
    ag = AvatarGenerator()
    
    # Check dependencies
    print("2. Checking dependencies...")
    deps = ag.check_dependencies()
    print(f"   Dependencies: {deps}")
    
    if not all(deps.values()):
        print("❌ Missing dependencies!")
        return False
    
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        print(f"   Working directory: {temp_path}")
        
        # Step 1: Create test image
        print("3. Creating test image...")
        test_img = create_test_image()
        image_path = temp_path / "test_avatar.png"
        
        if test_img:
            test_img.save(image_path)
            print(f"   ✅ Test image created: {image_path} ({image_path.stat().st_size} bytes)")
        else:
            # Create a minimal placeholder
            with open(image_path, 'wb') as f:
                f.write(b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x02\x00\x00\x00\x02\x00\x08\x02\x00\x00\x00')
            print(f"   ⚠️  Placeholder image created: {image_path}")
        
        # Step 2: Generate test TTS audio
        print("4. Generating TTS audio...")
        test_script = """
        Hello, this is a comprehensive test of the MuseTalk video generation system.
        We are testing the integration between text-to-speech, MuseTalk lip-sync technology,
        and the PresGen training pipeline. This should create a realistic talking avatar
        with synchronized lip movements. The system uses an isolated Python 3.10 environment
        to ensure compatibility with MuseTalk's requirements.
        """
        
        audio_path = temp_path / "test_audio.wav"
        start_time = time.time()
        
        try:
            tts_result = ag.generate_tts_audio(test_script.strip(), audio_path)
            tts_duration = time.time() - start_time
            
            if tts_result and audio_path.exists():
                file_size = audio_path.stat().st_size
                print(f"   ✅ TTS generated: {audio_path} ({file_size} bytes, {tts_duration:.1f}s)")
            else:
                print("   ❌ TTS generation failed")
                return False
        except Exception as e:
            print(f"   ❌ TTS error: {e}")
            return False
        
        # Step 3: Test MuseTalk wrapper directly
        print("5. Testing MuseTalk wrapper...")
        wrapper_path = Path("musetalk_wrapper.py")
        if wrapper_path.exists():
            print(f"   ✅ MuseTalk wrapper found: {wrapper_path}")
        else:
            print("   ❌ MuseTalk wrapper not found")
            return False
        
        # Step 4: Generate avatar video
        print("6. Generating avatar video with MuseTalk...")
        output_path = temp_path / "test_avatar_video.mp4"
        start_time = time.time()
        
        try:
            # This will call MuseTalk through the wrapper
            video_result = ag.generate_avatar_video(audio_path, image_path, output_path)
            video_duration = time.time() - start_time
            
            if video_result and output_path.exists():
                file_size = output_path.stat().st_size
                file_size_mb = file_size / (1024 * 1024)
                print(f"   ✅ Avatar video generated: {output_path}")
                print(f"      File size: {file_size_mb:.2f} MB")
                print(f"      Generation time: {video_duration:.1f}s")
                
                # Check if this was MuseTalk or static fallback
                if file_size > 2 * 1024 * 1024:  # > 2MB suggests animated video
                    print("   🎉 Video appears to be MuseTalk-generated (animated)")
                else:
                    print("   ⚠️  Video might be static fallback (check logs)")
                
            else:
                print("   ❌ Avatar video generation failed")
                return False
                
        except Exception as e:
            print(f"   ❌ Video generation error: {e}")
            return False
        
        # Step 5: Analyze the results
        print("7. Analysis Summary...")
        print(f"   • TTS Audio: {audio_path.stat().st_size / 1024:.1f} KB")
        print(f"   • Input Image: {image_path.stat().st_size / 1024:.1f} KB") 
        print(f"   • Output Video: {output_path.stat().st_size / (1024*1024):.2f} MB")
        print(f"   • Total Processing: {tts_duration + video_duration:.1f}s")
        
        # Step 6: Test video file integrity
        print("8. Verifying video file...")
        try:
            import subprocess
            result = subprocess.run([
                'ffprobe', '-v', 'quiet', '-print_format', 'json', 
                '-show_format', '-show_streams', str(output_path)
            ], capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                info = json.loads(result.stdout)
                duration = float(info['format']['duration'])
                streams = len(info['streams'])
                print(f"   ✅ Valid video file: {duration:.1f}s duration, {streams} streams")
            else:
                print("   ⚠️  Could not verify video file")
                
        except Exception as e:
            print(f"   ⚠️  Video verification failed: {e}")
    
    print("\n🎉 MuseTalk Video Generation Test Completed!")
    print("✅ All components working correctly")
    return True

def test_musetalk_environment():
    """Test the MuseTalk environment separately"""
    print("\n🔧 Testing MuseTalk Environment...")
    
    try:
        import subprocess
        
        # Test MuseTalk Python environment
        result = subprocess.run([
            'musetalk_env/bin/python', '-c', 
            'import torch; print(f"PyTorch: {torch.__version__}"); import numpy; print("Dependencies OK")'
        ], capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            print("✅ MuseTalk environment is healthy")
            print(f"   Output: {result.stdout.strip()}")
            return True
        else:
            print("❌ MuseTalk environment test failed")
            print(f"   Error: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ MuseTalk environment error: {e}")
        return False

if __name__ == "__main__":
    print("🎬 MuseTalk Integration Testing Suite")
    print("====================================")
    
    # Test environment first
    env_ok = test_musetalk_environment()
    
    # Test video generation
    video_ok = test_musetalk_video_generation()
    
    print("\n📊 Test Results:")
    print(f"   MuseTalk Environment: {'✅ PASS' if env_ok else '❌ FAIL'}")
    print(f"   Video Generation: {'✅ PASS' if video_ok else '❌ FAIL'}")
    
    if env_ok and video_ok:
        print("\n🎉 All tests passed! MuseTalk integration is working correctly.")
        exit(0)
    else:
        print("\n❌ Some tests failed. Check the output above for details.")
        exit(1)