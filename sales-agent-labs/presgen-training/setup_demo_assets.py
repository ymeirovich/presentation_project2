#!/usr/bin/env python3
"""
Setup PresGen-Training Demo Assets

Prepares demo assets using the existing presgen_test.mp4 video for avatar generation.
This script extracts the best frame for avatar generation and validates video properties.
"""

import subprocess
import json
from pathlib import Path
import time

def setup_demo_assets():
    """Setup demo assets using existing presgen_test.mp4"""
    
    print("🎬 Setting up PresGen-Training Demo Assets...")
    
    # Paths
    source_video = Path("examples/video/presgen_test.mp4")
    assets_dir = Path("presgen-training/assets")
    presenter_frame = assets_dir / "presenter_frame.jpg"
    
    # Validate source video exists
    if not source_video.exists():
        raise FileNotFoundError(f"Source video not found: {source_video}")
    
    # Create assets directory
    assets_dir.mkdir(parents=True, exist_ok=True)
    
    # Get video properties
    print(f"📹 Analyzing source video: {source_video}")
    video_info = get_video_properties(source_video)
    print(f"   Duration: {video_info['duration']:.1f} seconds")
    print(f"   Resolution: {video_info['width']}x{video_info['height']}")
    print(f"   Frame Rate: {video_info['fps']:.1f} fps")
    print(f"   File Size: {video_info['size_mb']:.1f} MB")
    
    # Extract multiple frames to find the best one
    print("🖼️  Extracting presenter frames...")
    frame_candidates = extract_frame_candidates(source_video, assets_dir)
    
    # Select best frame (for demo, we'll use the first one)
    best_frame = frame_candidates[0]
    if best_frame != presenter_frame:
        import shutil
        shutil.copy2(best_frame, presenter_frame)
    
    print(f"✅ Selected presenter frame: {presenter_frame}")
    
    # Validate frame quality
    frame_info = get_image_properties(presenter_frame)
    print(f"   Frame Resolution: {frame_info['width']}x{frame_info['height']}")
    
    # Create demo script file
    demo_script_path = assets_dir / "demo_script.txt"
    with open(demo_script_path, "w") as f:
        f.write(get_demo_script())
    
    print(f"✅ Created demo script: {demo_script_path}")
    
    # Generate asset manifest
    manifest = {
        "source_video": {
            "path": str(source_video),
            "duration": video_info['duration'],
            "resolution": f"{video_info['width']}x{video_info['height']}",
            "fps": video_info['fps'],
            "size_mb": video_info['size_mb']
        },
        "presenter_frame": {
            "path": str(presenter_frame),
            "resolution": f"{frame_info['width']}x{frame_info['height']}"
        },
        "demo_script": {
            "path": str(demo_script_path),
            "word_count": len(get_demo_script().split()),
            "estimated_duration": len(get_demo_script().split()) * 0.4  # ~0.4 seconds per word
        },
        "created_at": time.time()
    }
    
    manifest_path = assets_dir / "asset_manifest.json"
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)
    
    print(f"✅ Created asset manifest: {manifest_path}")
    print("🎉 Demo assets setup complete!")
    
    return manifest

def get_video_properties(video_path: Path) -> dict:
    """Get video properties using ffprobe"""
    
    cmd = [
        "ffprobe", "-v", "quiet", "-print_format", "json",
        "-show_format", "-show_streams", str(video_path)
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode != 0:
        raise RuntimeError(f"ffprobe failed: {result.stderr}")
    
    data = json.loads(result.stdout)
    
    # Extract video stream info
    video_stream = next(s for s in data["streams"] if s["codec_type"] == "video")
    
    return {
        "duration": float(data["format"]["duration"]),
        "width": int(video_stream["width"]),
        "height": int(video_stream["height"]),
        "fps": eval(video_stream["r_frame_rate"]),  # Convert "num/den" to float
        "size_mb": int(data["format"]["size"]) / (1024 * 1024)
    }

def get_image_properties(image_path: Path) -> dict:
    """Get image properties using ffprobe"""
    
    cmd = [
        "ffprobe", "-v", "quiet", "-print_format", "json",
        "-show_streams", str(image_path)
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode != 0:
        raise RuntimeError(f"ffprobe failed: {result.stderr}")
    
    data = json.loads(result.stdout)
    stream = data["streams"][0]
    
    return {
        "width": int(stream["width"]),
        "height": int(stream["height"])
    }

def extract_frame_candidates(video_path: Path, output_dir: Path) -> list:
    """Extract multiple frame candidates for avatar generation"""
    
    frame_times = [2, 5, 10, 15, 20]  # Extract frames at these seconds
    frame_paths = []
    
    for i, time_sec in enumerate(frame_times):
        frame_path = output_dir / f"frame_candidate_{i+1}.jpg"
        
        cmd = [
            "ffmpeg", "-y", "-i", str(video_path),
            "-ss", str(time_sec), "-vframes", "1",
            "-q:v", "2", str(frame_path)
        ]
        
        result = subprocess.run(cmd, capture_output=True)
        
        if result.returncode == 0 and frame_path.exists():
            frame_paths.append(frame_path)
            print(f"   Extracted frame at {time_sec}s: {frame_path}")
        else:
            print(f"   ⚠️  Failed to extract frame at {time_sec}s")
    
    return frame_paths

def get_demo_script() -> str:
    """Get the VC demo script content"""
    return """Hello investors, I'm excited to present PresGen-Training, our revolutionary AI avatar technology.

Our system transforms any text script into professional presentation videos with automatic content analysis and overlay generation.

This video demonstrates our proprietary avatar generation technology, seamlessly integrated with our existing PresGen-Video pipeline.

Key innovations include local-first processing with zero cloud costs, intelligent resource management for MacBook hardware, and automatic bullet point extraction from script content.

We're transforming how companies create training videos, marketing content, and professional presentations. With PresGen-Training, anyone can produce studio-quality videos in minutes, not hours."""

def validate_demo_setup():
    """Validate that demo assets are properly set up"""
    
    print("\n🔍 Validating demo setup...")
    
    required_files = [
        "presgen-training/assets/presenter_frame.jpg",
        "presgen-training/assets/demo_script.txt", 
        "presgen-training/assets/asset_manifest.json",
        "examples/video/presgen_test.mp4"
    ]
    
    all_valid = True
    
    for file_path in required_files:
        if Path(file_path).exists():
            print(f"✅ {file_path}")
        else:
            print(f"❌ {file_path} - MISSING")
            all_valid = False
    
    if all_valid:
        print("🎉 All demo assets validated successfully!")
    else:
        print("⚠️  Some demo assets are missing - run setup again")
    
    return all_valid

if __name__ == "__main__":
    try:
        manifest = setup_demo_assets()
        validate_demo_setup()
        
        print(f"\n📋 Demo Asset Summary:")
        print(f"   Source Video: {manifest['source_video']['duration']:.1f}s, {manifest['source_video']['resolution']}")
        print(f"   Demo Script: {manifest['demo_script']['word_count']} words, ~{manifest['demo_script']['estimated_duration']:.1f}s")
        print(f"   Presenter Frame: {manifest['presenter_frame']['resolution']}")
        print("\n🚀 Ready for PresGen-Training implementation!")
        
    except Exception as e:
        print(f"❌ Setup failed: {e}")
        exit(1)