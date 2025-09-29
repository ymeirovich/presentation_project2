#!/usr/bin/env python3
"""
PresGen Cache Clearing Script

This script clears various caches to ensure fresh slide generation.
Use this when cache is interfering with development or when slides
aren't being generated properly despite cache being disabled.

Usage:
    python3 clear_cache.py                    # Clear all caches
    python3 clear_cache.py --idempotency      # Clear only idempotency cache
    python3 clear_cache.py --llm              # Clear only LLM cache
    python3 clear_cache.py --images           # Clear only image cache
    python3 clear_cache.py --data-slides      # Clear only data slide cache entries
"""

import json
import shutil
import os
import argparse
import sys
from pathlib import Path
from datetime import datetime

def backup_file(file_path: Path) -> Path:
    """Create a timestamped backup of a file."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = file_path.with_suffix(f".backup_{timestamp}")
    shutil.copy2(file_path, backup_path)
    print(f"✓ Backed up {file_path} to {backup_path}")
    return backup_path

def clear_idempotency_cache(clear_all: bool = True, pattern: str = None):
    """Clear idempotency cache entries."""
    idempotency_file = Path("out/state/idempotency.json")

    if not idempotency_file.exists():
        print("✓ No idempotency cache found")
        return

    # Backup first
    backup_file(idempotency_file)

    # Load current cache
    with open(idempotency_file, 'r') as f:
        cache = json.load(f)

    original_count = len(cache)

    if clear_all:
        # Clear everything
        cache = {}
        print(f"✓ Cleared all {original_count} idempotency cache entries")
    elif pattern:
        # Clear entries matching pattern
        entries_to_remove = [key for key in cache.keys() if pattern in key]
        for key in entries_to_remove:
            del cache[key]
        removed_count = len(entries_to_remove)
        print(f"✓ Cleared {removed_count} idempotency entries matching '{pattern}'")

        if entries_to_remove:
            print("  Removed entries:")
            for entry in entries_to_remove:
                print(f"    - {entry}")

    # Write back
    with open(idempotency_file, 'w') as f:
        json.dump(cache, f)

    remaining_count = len(cache)
    print(f"✓ Remaining cache entries: {remaining_count}")

def clear_llm_cache():
    """Clear LLM summarization cache."""
    llm_cache_dir = Path("out/state/cache/llm_summarize")

    if not llm_cache_dir.exists():
        print("✓ No LLM cache found")
        return

    # Count files before deletion
    cache_files = list(llm_cache_dir.glob("*.json"))
    file_count = len(cache_files)

    if file_count > 0:
        # Backup directory
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_dir = llm_cache_dir.parent / f"llm_summarize_backup_{timestamp}"
        shutil.copytree(llm_cache_dir, backup_dir)
        print(f"✓ Backed up LLM cache to {backup_dir}")

        # Clear cache
        shutil.rmtree(llm_cache_dir)
        llm_cache_dir.mkdir(parents=True, exist_ok=True)
        print(f"✓ Cleared {file_count} LLM cache files")
    else:
        print("✓ LLM cache is already empty")

def clear_image_cache():
    """Clear image generation cache."""
    image_cache_dir = Path("out/state/cache/imagen")

    if not image_cache_dir.exists():
        print("✓ No image cache found")
        return

    # Count files before deletion
    cache_files = list(image_cache_dir.glob("*.json"))
    file_count = len(cache_files)

    if file_count > 0:
        # Backup directory
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_dir = image_cache_dir.parent / f"imagen_backup_{timestamp}"
        shutil.copytree(image_cache_dir, backup_dir)
        print(f"✓ Backed up image cache to {backup_dir}")

        # Clear cache
        shutil.rmtree(image_cache_dir)
        image_cache_dir.mkdir(parents=True, exist_ok=True)
        print(f"✓ Cleared {file_count} image cache files")
    else:
        print("✓ Image cache is already empty")

def clear_data_slide_cache():
    """Clear only data query slide cache entries (req-*#dq* pattern)."""
    clear_idempotency_cache(clear_all=False, pattern="#dq")

def show_cache_status():
    """Show current cache status."""
    print("\n📊 Current Cache Status:")
    print("=" * 50)

    # Idempotency cache
    idempotency_file = Path("out/state/idempotency.json")
    if idempotency_file.exists():
        with open(idempotency_file, 'r') as f:
            cache = json.load(f)
        print(f"Idempotency entries: {len(cache)}")

        # Count data query entries
        data_entries = [key for key in cache.keys() if "#dq" in key]
        print(f"  - Data query entries: {len(data_entries)}")
        if data_entries:
            print("  - Data query IDs:")
            for entry in data_entries:
                print(f"    • {entry}")
    else:
        print("Idempotency cache: Not found")

    # LLM cache
    llm_cache_dir = Path("out/state/cache/llm_summarize")
    if llm_cache_dir.exists():
        llm_files = list(llm_cache_dir.glob("*.json"))
        print(f"LLM cache files: {len(llm_files)}")
    else:
        print("LLM cache: Not found")

    # Image cache
    image_cache_dir = Path("out/state/cache/imagen")
    if image_cache_dir.exists():
        image_files = list(image_cache_dir.glob("*.json"))
        print(f"Image cache files: {len(image_files)}")
    else:
        print("Image cache: Not found")

    # Environment settings
    print(f"\n🔧 Environment Settings:")
    try:
        from dotenv import load_dotenv
        load_dotenv()
        presgen_dev_mode = os.getenv("PRESGEN_DEV_MODE", "not set")
        presgen_use_cache = os.getenv("PRESGEN_USE_CACHE", "not set")
        print(f"PRESGEN_DEV_MODE: {presgen_dev_mode}")
        print(f"PRESGEN_USE_CACHE: {presgen_use_cache}")

        # Determine effective cache setting
        dev_mode = presgen_dev_mode.lower() == "true"
        cache_disabled = presgen_use_cache.lower() == "false"
        effective_cache_disabled = dev_mode or cache_disabled

        print(f"Effective cache status: {'DISABLED' if effective_cache_disabled else 'ENABLED'}")

        if not effective_cache_disabled:
            print("⚠️  WARNING: Cache appears to be enabled!")
            print("   This might explain why slides aren't regenerating.")

    except ImportError:
        print("Install python-dotenv to see environment settings: pip install python-dotenv")

def main():
    parser = argparse.ArgumentParser(description="Clear PresGen caches")
    parser.add_argument("--idempotency", action="store_true", help="Clear only idempotency cache")
    parser.add_argument("--llm", action="store_true", help="Clear only LLM cache")
    parser.add_argument("--images", action="store_true", help="Clear only image cache")
    parser.add_argument("--data-slides", action="store_true", help="Clear only data slide cache entries")
    parser.add_argument("--status", action="store_true", help="Show cache status without clearing")

    args = parser.parse_args()

    # Ensure we're in the right directory
    if not Path("out/state").exists():
        print("❌ Error: This script must be run from the project root directory")
        print("   (out/state directory not found)")
        sys.exit(1)

    print("🧹 PresGen Cache Cleaner")
    print("=" * 30)

    if args.status:
        show_cache_status()
        return

    # If no specific flags, clear all
    clear_all = not any([args.idempotency, args.llm, args.images, args.data_slides])

    if clear_all or args.idempotency:
        print("\n🗑️  Clearing idempotency cache...")
        clear_idempotency_cache()

    if clear_all or args.llm:
        print("\n🗑️  Clearing LLM cache...")
        clear_llm_cache()

    if clear_all or args.images:
        print("\n🗑️  Clearing image cache...")
        clear_image_cache()

    if args.data_slides:
        print("\n🗑️  Clearing data slide cache entries...")
        clear_data_slide_cache()

    print("\n✅ Cache clearing complete!")
    print("\nNext steps:")
    print("1. Restart the backend server if it's running")
    print("2. Try generating slides again")
    print("3. Check logs to verify use_cache: false")

if __name__ == "__main__":
    main()