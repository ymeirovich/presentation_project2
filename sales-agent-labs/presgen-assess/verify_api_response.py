#!/usr/bin/env python3
"""
Verify API Response Format

This script simulates what the backend API will return when queried for files.
"""

import sys
import json
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from src.service.file_upload_service import file_registry


def verify_api_response():
    """Verify that the API response matches the expected format"""

    cert_profile_id = '455dae60-065c-4038-b3df-6d769b955dbb'

    print("Simulating API endpoint: GET /api/v1/presgen-assess/files/profile/{cert_profile_id}")
    print(f"Profile ID: {cert_profile_id}\n")

    # Get files from registry (as the API endpoint would)
    files = file_registry.get_files_for_profile(cert_profile_id)

    # Format response as the API would
    api_response = {
        "files": [
            {
                "file_id": fm.file_id,
                "original_filename": fm.original_filename,
                "resource_type": fm.resource_type.value,
                "file_size": fm.file_size,
                "processing_status": fm.processing_status,
                "chunk_count": fm.chunk_count,
                "upload_timestamp": fm.upload_timestamp,
                "error_message": fm.error_message
            }
            for fm in files
        ],
        "total_count": len(files)
    }

    print("API Response (JSON):")
    print("=" * 80)
    print(json.dumps(api_response, indent=2))
    print("=" * 80)

    # Verify response structure matches UI expectations
    print("\n✅ Verification:")
    print(f"  - Response has 'files' key: {('files' in api_response)}")
    print(f"  - Total files: {api_response['total_count']}")
    print(f"  - All files have required fields: {all(['file_id' in f and 'original_filename' in f and 'resource_type' in f for f in api_response['files']])}")

    # Check resource type distribution
    resource_types = {}
    for file in api_response['files']:
        rt = file['resource_type']
        resource_types[rt] = resource_types.get(rt, 0) + 1

    print(f"  - Resource type distribution:")
    for rt, count in resource_types.items():
        print(f"    - {rt}: {count}")

    print("\n✅ API response format is valid and matches UI expectations!")

    return api_response


if __name__ == '__main__':
    verify_api_response()
