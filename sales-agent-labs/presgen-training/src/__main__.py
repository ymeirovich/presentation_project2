#!/usr/bin/env python3
"""
PresGen-Training CLI Entry Point

Command line interface for avatar-based training video generation.
Follows project style and integrates with existing PresGen-Video pipeline.

Usage:
    python3 -m presgen-training --script assets/demo_script.txt --source-video examples/video/presgen_test.mp4
    python3 -m presgen-training --script assets/demo_script.txt --quality fast --output outputs/demo_video.mp4
"""

import argparse
import logging
import os
import sys
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.common.jsonlog import jlog
from presgen-training.src.orchestrator import TrainingVideoOrchestrator


def setup_logging(log_level: str = "INFO") -> logging.Logger:
    """Setup logging following project style with presgen-training namespace"""
    # Enable presgen-training specific logging
    os.environ["PRESGEN_TRAINING_LOGGING"] = "true"
    os.environ["ENABLE_LOCAL_DEBUG_FILE"] = "true"
    
    logger = logging.getLogger("presgen_training.cli")
    logger.setLevel(getattr(logging, log_level.upper()))
    
    # Console handler for immediate feedback
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setLevel(logging.INFO)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    
    return logger


def parse_arguments() -> argparse.Namespace:
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description="PresGen-Training: Avatar-based training video generation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 -m presgen-training --script assets/demo_script.txt
  python3 -m presgen-training --script assets/demo_script.txt --quality fast
  python3 -m presgen-training --script assets/demo_script.txt --source-video custom_video.mp4
        """
    )
    
    parser.add_argument(
        "--script", 
        required=True,
        type=Path,
        help="Path to text script file for avatar narration"
    )
    
    parser.add_argument(
        "--source-video",
        type=Path, 
        default=Path("examples/video/presgen_test.mp4"),
        help="Source video for presenter frames (default: presgen_test.mp4)"
    )
    
    parser.add_argument(
        "--quality",
        choices=["fast", "standard", "high"],
        default="standard",
        help="Processing quality level (default: standard)"
    )
    
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("presgen-training/outputs"),
        help="Output directory for generated videos"
    )
    
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Logging level (default: INFO)"
    )
    
    parser.add_argument(
        "--no-hardware-check",
        action="store_true",
        help="Skip hardware validation (use with caution)"
    )
    
    parser.add_argument(
        "--dry-run",
        action="store_true", 
        help="Validate inputs and show processing plan without execution"
    )
    
    return parser.parse_args()


def validate_inputs(args: argparse.Namespace, logger: logging.Logger) -> bool:
    """Validate input arguments and files"""
    jlog(logger, logging.INFO, 
         event="input_validation_start",
         script_path=str(args.script),
         source_video=str(args.source_video))
    
    # Check script file
    if not args.script.exists():
        jlog(logger, logging.ERROR,
             event="script_file_missing", 
             path=str(args.script))
        return False
        
    # Check source video
    if not args.source_video.exists():
        jlog(logger, logging.ERROR,
             event="source_video_missing",
             path=str(args.source_video))
        return False
    
    # Create output directory
    args.output.mkdir(parents=True, exist_ok=True)
    
    jlog(logger, logging.INFO,
         event="input_validation_success",
         script_size_bytes=args.script.stat().st_size,
         video_size_mb=round(args.source_video.stat().st_size / (1024*1024), 2))
    
    return True


def main():
    """Main CLI entry point"""
    args = parse_arguments()
    logger = setup_logging(args.log_level)
    
    jlog(logger, logging.INFO,
         event="presgen_training_start",
         version="1.0.0",
         quality=args.quality,
         script_path=str(args.script),
         source_video=str(args.source_video),
         output_dir=str(args.output))
    
    try:
        # Validate inputs
        if not validate_inputs(args, logger):
            sys.exit(1)
        
        # Initialize orchestrator
        orchestrator = TrainingVideoOrchestrator(
            quality=args.quality,
            skip_hardware_check=args.no_hardware_check,
            output_dir=args.output,
            logger=logger
        )
        
        if args.dry_run:
            jlog(logger, logging.INFO, event="dry_run_mode")
            plan = orchestrator.create_processing_plan(
                script_path=args.script,
                source_video_path=args.source_video
            )
            print("\n=== Processing Plan ===")
            for step in plan:
                print(f"  {step['phase']}: {step['description']} (est. {step['duration_mins']}min)")
            print(f"\nTotal estimated time: {sum(s['duration_mins'] for s in plan)} minutes")
            return
        
        # Execute training video generation
        result = orchestrator.process_training_video(
            script_path=args.script,
            source_video_path=args.source_video
        )
        
        if result["success"]:
            jlog(logger, logging.INFO,
                 event="presgen_training_success",
                 output_video=result["output_video"],
                 processing_time_seconds=result["processing_time"],
                 avatar_frames=result["avatar_frames"],
                 bullet_points=len(result["bullet_points"]))
            
            print(f"\n✅ Training video generated successfully!")
            print(f"   Output: {result['output_video']}")
            print(f"   Processing time: {result['processing_time']:.1f}s")
            print(f"   Avatar frames: {result['avatar_frames']}")
            print(f"   Bullet points: {len(result['bullet_points'])}")
            
        else:
            jlog(logger, logging.ERROR,
                 event="presgen_training_failure",
                 error=result["error"],
                 processing_time_seconds=result.get("processing_time", 0))
            
            print(f"\n❌ Training video generation failed: {result['error']}")
            sys.exit(1)
            
    except KeyboardInterrupt:
        jlog(logger, logging.WARNING, event="presgen_training_interrupted")
        print("\n⚠️  Processing interrupted by user")
        sys.exit(130)
        
    except Exception as e:
        jlog(logger, logging.ERROR,
             event="presgen_training_exception",
             error=str(e),
             error_type=type(e).__name__)
        print(f"\n💥 Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()