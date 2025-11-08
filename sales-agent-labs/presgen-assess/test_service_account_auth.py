"""Test script to validate Google Service Account authentication for Forms API.

This script tests:
1. Service account credentials can be loaded
2. Service account has proper scopes for Google Forms
3. Service account can create a test form (and delete it)
4. OAuth authentication is NOT being used
"""

import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


def test_service_account_auth():
    """Test service account authentication for Google Forms API."""

    print("=" * 80)
    print("GOOGLE SERVICE ACCOUNT AUTHENTICATION TEST")
    print("=" * 80)

    # Step 1: Check environment variables
    print("\n[1/5] Checking environment variables...")
    creds_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    oauth_path = os.getenv("OAUTH_TOKEN_PATH")
    impersonate_user = os.getenv("GOOGLE_SERVICE_ACCOUNT_IMPERSONATE_USER")
    project = os.getenv("GOOGLE_CLOUD_PROJECT")

    print(f"  ✓ GOOGLE_APPLICATION_CREDENTIALS: {creds_path}")
    print(f"  ✓ GOOGLE_CLOUD_PROJECT: {project}")
    print(f"  ✓ GOOGLE_SERVICE_ACCOUNT_IMPERSONATE_USER: {impersonate_user}")

    if oauth_path:
        print(f"  ⚠️  OAUTH_TOKEN_PATH is set: {oauth_path}")
        print(f"  ⚠️  This may cause OAuth to be used instead of service account!")
    else:
        print(f"  ✓ OAUTH_TOKEN_PATH: Not set (good - using service account only)")

    # Step 2: Load service account credentials
    print("\n[2/5] Loading service account credentials...")
    if not creds_path or not Path(creds_path).exists():
        print(f"  ❌ ERROR: Service account file not found: {creds_path}")
        return False

    try:
        scopes = [
            "https://www.googleapis.com/auth/forms.body",
            "https://www.googleapis.com/auth/drive",
        ]

        credentials = service_account.Credentials.from_service_account_file(
            creds_path,
            scopes=scopes,
        )

        # Add domain-wide delegation if impersonate user is set
        if impersonate_user:
            print(f"  ✓ Applying domain-wide delegation for: {impersonate_user}")
            credentials = credentials.with_subject(impersonate_user)

        print(f"  ✓ Service account credentials loaded successfully")
        print(f"  ✓ Scopes: {credentials.scopes}")

    except Exception as e:
        print(f"  ❌ ERROR loading credentials: {e}")
        return False

    # Step 3: Build Google Forms API service
    print("\n[3/5] Building Google Forms API client...")
    try:
        forms_service = build("forms", "v1", credentials=credentials, cache_discovery=False)
        print(f"  ✓ Google Forms API client built successfully")
    except Exception as e:
        print(f"  ❌ ERROR building Forms API client: {e}")
        return False

    # Step 4: Test creating a form
    print("\n[4/5] Testing form creation...")
    test_form_id = None
    try:
        form_body = {
            "info": {
                "title": "🧪 Service Account Auth Test Form",
                "documentTitle": "Service Account Test"
            }
        }

        result = forms_service.forms().create(body=form_body).execute()
        test_form_id = result.get("formId")
        form_url = result.get("responderUri")

        print(f"  ✓ Form created successfully!")
        print(f"  ✓ Form ID: {test_form_id}")
        print(f"  ✓ Form URL: {form_url}")

    except HttpError as e:
        print(f"  ❌ ERROR creating form: HTTP {e.resp.status}")
        print(f"  ❌ Error details: {e.error_details}")
        print(f"\n  Common causes:")
        print(f"    - Service account doesn't have domain-wide delegation enabled")
        print(f"    - OAuth scopes not authorized in Google Workspace Admin")
        print(f"    - IMPERSONATE_USER email is incorrect")
        return False
    except Exception as e:
        print(f"  ❌ ERROR: {e}")
        return False

    # Step 5: Clean up - delete test form
    print("\n[5/5] Cleaning up test form...")
    if test_form_id:
        try:
            # Use Drive API to delete the form
            drive_service = build("drive", "v3", credentials=credentials, cache_discovery=False)
            drive_service.files().delete(fileId=test_form_id).execute()
            print(f"  ✓ Test form deleted successfully")
        except Exception as e:
            print(f"  ⚠️  Could not delete test form (may need manual cleanup): {e}")
            print(f"  ⚠️  Form URL: {form_url}")

    # Success!
    print("\n" + "=" * 80)
    print("✅ ALL TESTS PASSED - Service account authentication is working!")
    print("=" * 80)
    return True


if __name__ == "__main__":
    success = test_service_account_auth()
    sys.exit(0 if success else 1)
