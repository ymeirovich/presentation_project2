#!/usr/bin/env python3
"""
Script to update hardcoded port references to use centralized config
Updates all route.ts files in presgen-ui/src/app/api/presgen-assess
"""
import os
import re
from pathlib import Path

# Pattern to find and replace the old constant declaration
OLD_PATTERN = re.compile(
    r"^// PresGen-Assess Backend API URL\nconst ASSESS_API_URL = process\.env\.NEXT_PUBLIC_ASSESS_API_URL \|\| 'http://localhost:8081'$",
    re.MULTILINE
)

NEW_IMPORT = "import { ASSESS_API_URL } from '@/lib/config'"

def update_file(file_path: Path):
    """Update a single file to use the config import."""
    try:
        content = file_path.read_text()

        # Skip if already updated
        if '@/lib/config' in content:
            print(f"✓ Already updated: {file_path.relative_to(file_path.parents[6])}")
            return False

        # Check if it has the old pattern
        if "const ASSESS_API_URL = process.env.NEXT_PUBLIC_ASSESS_API_URL || 'http://localhost:8081'" in content:
            # Replace the old pattern
            new_content = content.replace(
                "// PresGen-Assess Backend API URL\nconst ASSESS_API_URL = process.env.NEXT_PUBLIC_ASSESS_API_URL || 'http://localhost:8081'",
                NEW_IMPORT
            )

            file_path.write_text(new_content)
            print(f"✓ Updated: {file_path.relative_to(file_path.parents[6])}")
            return True
        else:
            print(f"⊘ No pattern found: {file_path.relative_to(file_path.parents[6])}")
            return False

    except Exception as e:
        print(f"✗ Error updating {file_path}: {e}")
        return False

def main():
    # Find all route.ts files in presgen-ui/src/app/api/presgen-assess
    base_path = Path(__file__).parent / "presgen-ui" / "src" / "app" / "api" / "presgen-assess"

    if not base_path.exists():
        print(f"Error: Path does not exist: {base_path}")
        return

    # Find all route.ts files
    route_files = list(base_path.rglob("route.ts"))

    print(f"Found {len(route_files)} route.ts files")
    print("=" * 60)

    updated_count = 0
    for route_file in sorted(route_files):
        if update_file(route_file):
            updated_count += 1

    print("=" * 60)
    print(f"Updated {updated_count} files")

    # Also check test_upload_fix.js
    test_file = Path(__file__).parent / "presgen-ui" / "test_upload_fix.js"
    if test_file.exists():
        print(f"\n⚠️  Note: {test_file.name} also contains port 8081 - review manually")

if __name__ == "__main__":
    main()
