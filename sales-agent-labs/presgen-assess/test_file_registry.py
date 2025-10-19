#!/usr/bin/env python3
"""
Test script for FileRegistry database integration
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from src.service.file_upload_service import file_registry


def test_file_registry():
    """Test that FileRegistry can load files from database"""

    cert_profile_id = '455dae60-065c-4038-b3df-6d769b955dbb'

    print("Testing FileRegistry database integration...")
    print(f"Loading files for certification profile: {cert_profile_id}\n")

    # Get files for the AWS ML Specialty profile
    files = file_registry.get_files_for_profile(cert_profile_id)

    print(f"Found {len(files)} files:")
    print("=" * 80)

    for file in files:
        print(f"\nFile ID: {file.file_id}")
        print(f"  Filename: {file.original_filename}")
        print(f"  Resource Type: {file.resource_type.value}")
        print(f"  Size: {file.file_size} bytes")
        print(f"  Status: {file.processing_status}")
        print(f"  Chunk Count: {file.chunk_count}")
        print(f"  Upload Time: {file.upload_timestamp}")

    print("\n" + "=" * 80)
    print(f"✅ Test passed! Successfully loaded {len(files)} files from database.")

    return files


if __name__ == '__main__':
    test_file_registry()
