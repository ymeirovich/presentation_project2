#!/usr/bin/env python3
"""
Voice Cloning Wrapper Script for PresGen-Training
Uses MuseTalk Python 3.10 environment to run Coqui TTS voice cloning
"""

import sys
import os
import json
import argparse
from pathlib import Path

def clone_voice(text: str, reference_audio_path: str, output_path: str) -> dict:
    """
    Clone voice using Coqui TTS in MuseTalk Python 3.10 environment
    
    Args:
        text: Text to synthesize with cloned voice
        reference_audio_path: Path to reference audio for voice cloning
        output_path: Path to output cloned audio file
        
    Returns:
        dict: Result with success status and any error message
    """
    try:
        # Convert paths to absolute paths
        reference_audio_path = os.path.abspath(reference_audio_path)
        output_path = os.path.abspath(output_path)
        
        # Validate input files exist
        if not os.path.exists(reference_audio_path):
            return {"success": False, "error": f"Reference audio not found: {reference_audio_path}"}
        
        # Create output directory if needed
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # Try voice cloning using Coqui TTS
        print(f"🎤 Starting voice cloning...", file=sys.stderr)
        print(f"   Text: {text[:50]}{'...' if len(text) > 50 else ''}", file=sys.stderr)
        print(f"   Reference: {reference_audio_path}", file=sys.stderr)
        print(f"   Output: {output_path}", file=sys.stderr)
        
        try:
            # Import TTS and related libraries
            import torch
            from TTS.api import TTS
            import tempfile
            import subprocess
            
            print(f"🔧 Loading YourTTS model for voice cloning...", file=sys.stderr)
            
            # Use YourTTS model for voice cloning (fastest multilingual option)
            # Redirect TTS model output to stderr to keep JSON output clean
            import contextlib
            with contextlib.redirect_stdout(sys.stderr):
                tts = TTS(model_name="tts_models/multilingual/multi-dataset/your_tts", progress_bar=False)
            
            # Create temporary file for initial TTS output
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
                temp_output_path = temp_file.name
            
            print(f"🗣️  Generating voice-cloned audio...", file=sys.stderr)
            
            # Generate cloned voice with stdout redirected
            with contextlib.redirect_stdout(sys.stderr):
                tts.tts_to_file(
                    text=text,
                    speaker_wav=reference_audio_path,
                    language="en",
                    file_path=temp_output_path
                )
            
            # Convert to required format (16kHz mono PCM) for MuseTalk compatibility
            convert_cmd = [
                "ffmpeg", "-i", temp_output_path,
                "-acodec", "pcm_s16le",
                "-ar", "16000",  # 16kHz sample rate for MuseTalk
                "-ac", "1",      # Mono
                "-y",            # Overwrite
                output_path
            ]
            
            result = subprocess.run(convert_cmd, capture_output=True, text=True, timeout=30)
            
            # Clean up temp file
            os.unlink(temp_output_path)
            
            if result.returncode == 0 and os.path.exists(output_path):
                file_size_mb = round(os.path.getsize(output_path) / (1024*1024), 2)
                
                print(f"✅ Voice cloning completed successfully!", file=sys.stderr)
                print(f"   Output: {output_path} ({file_size_mb}MB)", file=sys.stderr)
                
                return {
                    "success": True,
                    "output_path": output_path,
                    "file_size_mb": file_size_mb,
                    "method": "YourTTS",
                    "message": "Voice cloning completed using YourTTS model"
                }
            else:
                return {
                    "success": False,
                    "error": f"FFmpeg conversion failed: {result.stderr}",
                    "message": "Voice cloning failed during audio format conversion"
                }
                
        except ImportError as e:
            return {
                "success": False,
                "error": f"TTS library not available: {e}",
                "message": "Coqui TTS not properly installed in environment"
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": f"Voice cloning failed: {e}"
            }
            
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": f"Voice cloning wrapper failed: {e}"
        }

def main():
    parser = argparse.ArgumentParser(description='Voice Cloning Wrapper using Coqui TTS')
    parser.add_argument('--text', required=True, help='Text to synthesize with cloned voice')
    parser.add_argument('--reference', required=True, help='Path to reference audio file')
    parser.add_argument('--output', required=True, help='Path to output audio file')
    parser.add_argument('--json-output', action='store_true', help='Output result as JSON')
    
    args = parser.parse_args()
    
    # Convert paths to absolute paths
    reference_path = os.path.abspath(args.reference)
    output_path = os.path.abspath(args.output)
    
    # Clone voice
    result = clone_voice(args.text, reference_path, output_path)
    
    if args.json_output:
        print(json.dumps(result))
    else:
        if result["success"]:
            print(f"Success: {result['message']}")
            print(f"Output: {result['output_path']}")
        else:
            print(f"Error: {result['message']}")
            if "error" in result:
                print(f"Details: {result['error']}")
            sys.exit(1)

if __name__ == "__main__":
    main()