#!/usr/bin/env python3
"""
MuseTalk Wrapper Script for Subprocess Communication
Handles audio-driven lip-sync video generation using MuseTalk
"""

import sys
import os
import json
import argparse
from pathlib import Path

def setup_musetalk_env():
    """Setup MuseTalk environment paths"""
    script_dir = Path(__file__).parent
    musetalk_dir = script_dir / "MuseTalk"
    
    # Add MuseTalk to Python path
    sys.path.insert(0, str(musetalk_dir))
    
    return musetalk_dir

def generate_video(audio_path: str, image_path: str, output_path: str) -> dict:
    """
    Generate lip-synced video using MuseTalk
    
    Args:
        audio_path: Path to input audio file
        image_path: Path to input image file (portrait photo)
        output_path: Path to output video file
        
    Returns:
        dict: Result with success status and any error message
    """
    # Convert all paths to absolute paths to avoid working directory issues
    audio_path = os.path.abspath(audio_path)
    image_path = os.path.abspath(image_path)
    output_path = os.path.abspath(output_path)
    
    # Validate input files exist
    if not os.path.exists(audio_path):
        return {"success": False, "error": f"Audio file not found: {audio_path}", "message": "Input validation failed"}
    if not os.path.exists(image_path):
        return {"success": False, "error": f"Image file not found: {image_path}", "message": "Input validation failed"}
    
    # Create output directory if needed
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    print(f"🎤 Starting MuseTalk lip-sync generation...", file=sys.stderr)
    print(f"   Audio: {audio_path}", file=sys.stderr)
    print(f"   Image: {image_path}", file=sys.stderr)  
    print(f"   Output: {output_path}", file=sys.stderr)
    
    script_dir = Path(__file__).parent
    inference_script = script_dir / "MuseTalk" / "scripts" / "inference.py"
    
    if not inference_script.exists():
        print(f"❌ MuseTalk inference script not found: {inference_script}", file=sys.stderr)
        return {"success": False, "error": "MuseTalk inference script not found"}

    # Create temporary config file and output directory for MuseTalk
    import tempfile
    import yaml
    temp_dir = Path(tempfile.mkdtemp(prefix="musetalk_"))
    temp_config = temp_dir / "inference_config.yaml"
    
    config_data = {
        "task_0": {
            "video_path": image_path,
            "audio_path": audio_path,
            "bbox_shift": 0,
            "batch_size": 8,
            "use_half": False,
            "num_workers": 4,
        }
    }
    
    with open(temp_config, 'w') as f:
        yaml.dump(config_data, f)
    
    musetalk_python = script_dir / "musetalk_env" / "bin" / "python"
    if not musetalk_python.exists():
        return {"success": False, "error": f"MuseTalk python environment not found at {musetalk_python}"}

    cmd = [
        str(musetalk_python),
        "scripts/inference.py",
        "--inference_config", str(temp_config),
        "--result_dir", str(temp_dir),
        "--use_saved_coord",
        "--version", "v15"
    ]
    
    print(f"🔄 Running MuseTalk command: {' '.join(cmd[:3])}...", file=sys.stderr)
    
    import subprocess
    musetalk_dir = script_dir / "MuseTalk"
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=3600,
        cwd=str(musetalk_dir),
        env=os.environ.copy()
    )
    
    if result.returncode == 0:
        import glob
        generated_videos = glob.glob(str(temp_dir / "v15" / "*.mp4"))
        
        if generated_videos:
            generated_video = generated_videos[0]
            import shutil
            shutil.move(generated_video, output_path)
            shutil.rmtree(temp_dir, ignore_errors=True)
            return {
                "success": True,
                "output_path": output_path,
                "message": "MuseTalk lip-sync video generated successfully"
            }
        else:
            error_message = f"MuseTalk completed but no output video found in: {temp_dir / 'v15'}"
            print(f"❌ {error_message}", file=sys.stderr)
            print(f"❌ Directory contents: {list(temp_dir.glob('**/*'))}", file=sys.stderr)
            shutil.rmtree(temp_dir, ignore_errors=True)
            return {"success": False, "error": error_message}
    else:
        error_message = f"MuseTalk failed with return code {result.returncode}"
        print(f"❌ {error_message}", file=sys.stderr)
        print(f"❌ Stderr: {result.stderr}", file=sys.stderr)
        print(f"❌ Stdout: {result.stdout}", file=sys.stderr)
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)
        return {"success": False, "error": error_message, "stderr": result.stderr, "stdout": result.stdout}




def main():
    parser = argparse.ArgumentParser(description='MuseTalk Wrapper for Video Generation')
    parser.add_argument('--audio', required=True, help='Path to audio file')
    parser.add_argument('--image', required=True, help='Path to image file')
    parser.add_argument('--output', required=True, help='Path to output video file')
    parser.add_argument('--json-output', action='store_true', help='Output result as JSON')
    
    args = parser.parse_args()
    
    # Convert paths to absolute paths
    audio_path = os.path.abspath(args.audio)
    image_path = os.path.abspath(args.image)
    output_path = os.path.abspath(args.output)
    
    # Setup MuseTalk environment (no longer changes working directory)
    musetalk_dir = setup_musetalk_env()
    
    # Generate video with absolute paths
    result = generate_video(audio_path, image_path, output_path)
    
    if args.json_output:
        print(json.dumps(result))
    else:
        if result["success"]:
            print(f"Success: {result['message']}")
            print(f"Output: {result['output_path']}")
        else:
            print(f"Error: {result['message']}")
            sys.exit(1)

if __name__ == "__main__":
    main()