#!/usr/bin/env python3
"""Validate Google Sheets service account authentication.

This script checks:
1. Service account file exists and is valid
2. Required Google API libraries are installed
3. Service account has proper permissions
4. API credentials work correctly

Usage:
    python scripts/validate_google_auth.py
"""

import sys
import os
import json
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def validate_service_account_file():
    """Validate service account JSON file."""
    print("🔍 Step 1: Validating service account file...")

    # Check environment variable
    creds_path = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')
    if not creds_path:
        print("❌ GOOGLE_APPLICATION_CREDENTIALS environment variable not set")
        print("💡 Set it in .env file or export it:")
        print(f"   export GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json")
        return False

    print(f"✅ GOOGLE_APPLICATION_CREDENTIALS: {creds_path}")

    # Check file exists
    if not os.path.exists(creds_path):
        print(f"❌ Service account file not found: {creds_path}")
        return False

    print(f"✅ Service account file exists")

    # Validate JSON structure
    try:
        with open(creds_path, 'r') as f:
            creds = json.load(f)

        required_fields = ['type', 'project_id', 'private_key_id', 'private_key', 'client_email', 'client_id']
        missing = [f for f in required_fields if f not in creds]

        if missing:
            print(f"❌ Missing required fields: {', '.join(missing)}")
            return False

        if creds['type'] != 'service_account':
            print(f"❌ Invalid account type: {creds['type']} (expected 'service_account')")
            return False

        print(f"✅ Service account JSON structure valid")
        print(f"   📧 Email: {creds['client_email']}")
        print(f"   🔑 Project: {creds['project_id']}")

        return True

    except json.JSONDecodeError as e:
        print(f"❌ Invalid JSON: {e}")
        return False
    except Exception as e:
        print(f"❌ Error reading file: {e}")
        return False

def validate_libraries():
    """Validate required Google API libraries are installed."""
    print("\n🔍 Step 2: Validating required libraries...")

    required_libs = [
        ('google.oauth2.service_account', 'google-auth'),
        ('googleapiclient.discovery', 'google-api-python-client'),
        ('googleapiclient.errors', 'google-api-python-client')
    ]

    missing_libs = []
    for module, package in required_libs:
        try:
            __import__(module)
            print(f"✅ {package} installed")
        except ImportError:
            print(f"❌ {package} not installed")
            missing_libs.append(package)

    if missing_libs:
        print(f"\n💡 Install missing libraries:")
        print(f"   pip install {' '.join(set(missing_libs))}")
        return False

    return True

def validate_api_access():
    """Validate Google Sheets API access."""
    print("\n🔍 Step 3: Validating Google Sheets API access...")

    try:
        from google.oauth2.service_account import Credentials
        from googleapiclient.discovery import build
        from googleapiclient.errors import HttpError

        creds_path = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')

        # Load credentials
        creds = Credentials.from_service_account_file(
            creds_path,
            scopes=[
                'https://www.googleapis.com/auth/spreadsheets',
                'https://www.googleapis.com/auth/drive.file'
            ]
        )

        print("✅ Credentials loaded successfully")

        # Build service
        service = build('sheets', 'v4', credentials=creds, cache_discovery=False)
        print("✅ Google Sheets API service initialized")

        # Test API by creating a spreadsheet
        print("\n🧪 Testing API access (creating test spreadsheet)...")

        spreadsheet_body = {
            'properties': {
                'title': 'PresGen-Auth-Test'
            }
        }

        try:
            spreadsheet = service.spreadsheets().create(body=spreadsheet_body).execute()
            spreadsheet_id = spreadsheet['spreadsheetId']
            spreadsheet_url = f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}"

            print(f"✅ Test spreadsheet created!")
            print(f"   📊 ID: {spreadsheet_id}")
            print(f"   🔗 URL: {spreadsheet_url}")

            # Clean up
            drive_service = build('drive', 'v3', credentials=creds, cache_discovery=False)
            drive_service.files().delete(fileId=spreadsheet_id).execute()
            print(f"✅ Test spreadsheet deleted (cleanup successful)")

            return True

        except HttpError as e:
            if e.resp.status == 403:
                print(f"❌ Permission denied (403)")
                print(f"\n💡 Possible issues:")
                print(f"   1. Google Sheets API not enabled in project")
                print(f"   2. Service account lacks necessary permissions")
                print(f"   3. API quota exceeded")
                print(f"\n🔧 To fix:")
                print(f"   1. Go to: https://console.cloud.google.com/apis/library/sheets.googleapis.com")
                print(f"   2. Enable Google Sheets API for project: {creds.project_id}")
                print(f"   3. Enable Google Drive API: https://console.cloud.google.com/apis/library/drive.googleapis.com")
                print(f"   4. Verify service account has Editor or Owner role")
                return False
            else:
                raise

    except Exception as e:
        print(f"❌ API access test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def validate_presgen_config():
    """Validate PresGen-Assess configuration."""
    print("\n🔍 Step 4: Validating PresGen-Assess configuration...")

    try:
        from src.common.config import Settings

        settings = Settings()

        print(f"✅ PresGen settings loaded")
        print(f"   📁 Credentials path: {settings.google_application_credentials}")
        print(f"   🔑 Project: {settings.google_cloud_project}")

        if not settings.google_application_credentials:
            print(f"❌ google_application_credentials not configured")
            return False

        return True

    except Exception as e:
        print(f"❌ Failed to load settings: {e}")
        return False

def main():
    """Run all validation steps."""
    print("=" * 60)
    print("Google Service Account Authentication Validation")
    print("=" * 60)

    # Load environment from .env if exists
    env_file = project_root / '.env'
    if env_file.exists():
        print(f"📄 Loading environment from: {env_file}")
        from dotenv import load_dotenv
        load_dotenv(env_file)

    results = []

    # Step 1: Validate service account file
    results.append(("Service Account File", validate_service_account_file()))

    # Step 2: Validate libraries
    results.append(("Required Libraries", validate_libraries()))

    # Step 3: Validate API access (only if previous steps passed)
    if all(r[1] for r in results):
        results.append(("API Access", validate_api_access()))
    else:
        print("\n⏭️  Skipping API access test (prerequisites failed)")
        results.append(("API Access", False))

    # Step 4: Validate PresGen config
    results.append(("PresGen Configuration", validate_presgen_config()))

    # Summary
    print("\n" + "=" * 60)
    print("Validation Summary")
    print("=" * 60)

    all_passed = True
    for check, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {check}")
        if not passed:
            all_passed = False

    print("=" * 60)

    if all_passed:
        print("✅ All checks passed! Google service account authentication is fully operational.")
        sys.exit(0)
    else:
        print("❌ Some checks failed. Please fix the issues above.")
        sys.exit(1)

if __name__ == "__main__":
    main()
