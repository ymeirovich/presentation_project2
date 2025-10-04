#!/usr/bin/env python3
"""
Test Google Forms API directly to diagnose the 500 error.

This script makes a minimal API call to create a form and shows detailed error information.
"""

import sys
import json
import logging
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Enable detailed logging
logging.basicConfig(level=logging.DEBUG)

def test_forms_api():
    """Test Forms API with minimal request."""

    token_path = Path(__file__).parent.parent / 'token.json'

    if not token_path.exists():
        print(f"❌ Token file not found: {token_path}")
        return

    print("=" * 60)
    print("🧪 Testing Google Forms API")
    print("=" * 60)
    print()

    # Load credentials
    print("📁 Loading OAuth token from:", token_path)
    creds = Credentials.from_authorized_user_file(str(token_path))

    print("✓ Token loaded")
    print(f"  Scopes: {len(creds.scopes)}")
    for scope in creds.scopes:
        print(f"    • {scope}")
    print()

    # Check if forms scope is present
    forms_scope = "https://www.googleapis.com/auth/forms.body"
    if forms_scope not in creds.scopes:
        print(f"❌ Missing required scope: {forms_scope}")
        return

    print(f"✓ Forms scope is present: {forms_scope}")
    print()

    # Build Forms API service
    print("🔧 Building Forms API service...")
    try:
        service = build('forms', 'v1', credentials=creds, cache_discovery=False)
        print("✓ Forms API service built successfully")
    except Exception as e:
        print(f"❌ Failed to build Forms API service: {e}")
        return

    print()
    print("📝 Attempting to create a test form...")
    print("Request body:", json.dumps({"info": {"title": "API Test Form"}}, indent=2))
    print()

    try:
        # Attempt to create a form with minimal data
        request = service.forms().create(body={"info": {"title": "API Test Form"}})

        # Show the request URI
        print(f"Request URI: {request.uri}")
        print()

        # Execute the request
        response = request.execute()

        print("=" * 60)
        print("✅ SUCCESS! Form created")
        print("=" * 60)
        print()
        print("Response:")
        print(json.dumps(response, indent=2))
        print()
        print(f"Form ID: {response.get('formId')}")
        print(f"Form URL: {response.get('responderUri')}")
        print(f"Edit URL: https://docs.google.com/forms/d/{response.get('formId')}/edit")

    except HttpError as error:
        print("=" * 60)
        print("❌ HTTP ERROR")
        print("=" * 60)
        print()
        print(f"Status Code: {error.resp.status}")
        print(f"Reason: {error.resp.reason}")
        print()
        print("Error Details:")
        print(error)
        print()

        # Try to parse error content
        try:
            error_content = json.loads(error.content.decode('utf-8'))
            print("Parsed Error:")
            print(json.dumps(error_content, indent=2))
        except:
            print("Raw Error Content:")
            print(error.content.decode('utf-8', errors='replace'))

        print()
        print("Possible causes:")
        print("  1. Google Forms API not enabled in your GCP project")
        print("  2. OAuth client doesn't have Forms API access")
        print("  3. Account doesn't have permission to create forms")
        print("  4. API quota exceeded")
        print()
        print("Next steps:")
        print("  1. Go to: https://console.cloud.google.com/apis/library/forms.googleapis.com")
        print("  2. Ensure 'Google Forms API' is ENABLED for your project")
        print("  3. Check quota at: https://console.cloud.google.com/apis/api/forms.googleapis.com/quotas")

    except Exception as e:
        print("=" * 60)
        print("❌ UNEXPECTED ERROR")
        print("=" * 60)
        print()
        print(f"Error type: {type(e).__name__}")
        print(f"Error message: {e}")
        import traceback
        print()
        print("Traceback:")
        traceback.print_exc()

if __name__ == '__main__':
    test_forms_api()
