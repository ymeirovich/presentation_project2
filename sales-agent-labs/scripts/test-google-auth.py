#!/usr/bin/env python3
"""
Test Google Cloud Service Account Authentication
Tests connection to Google APIs using service account credentials
"""

import os
import sys
from pathlib import Path

# Colors for terminal output
GREEN = '\033[0;32m'
RED = '\033[0;31m'
YELLOW = '\033[1;33m'
BLUE = '\033[0;34m'
NC = '\033[0m'  # No Color

def print_info(msg):
    print(f"{GREEN}[INFO]{NC} {msg}")

def print_error(msg):
    print(f"{RED}[ERROR]{NC} {msg}")

def print_success(msg):
    print(f"{GREEN}[SUCCESS]{NC} {msg}")

def print_section(title):
    print(f"\n{BLUE}{'='*60}{NC}")
    print(f"{BLUE}{title}{NC}")
    print(f"{BLUE}{'='*60}{NC}\n")

def check_dependencies():
    """Check if required packages are installed"""
    print_section("1. Checking Dependencies")

    required_packages = {
        'google.auth': 'google-auth',
        'google.oauth2': 'google-auth',
        'googleapiclient': 'google-api-python-client',
    }

    missing_packages = []

    for module, package in required_packages.items():
        try:
            __import__(module)
            print_success(f"✓ {package} is installed")
        except ImportError:
            print_error(f"✗ {package} is NOT installed")
            missing_packages.append(package)

    if missing_packages:
        print_error("\nMissing packages detected!")
        print_info("Install with:")
        print(f"  pip3 install {' '.join(missing_packages)}")
        print_info("\nOr install all requirements:")
        print("  pip3 install -r requirements.txt")
        return False

    return True

def check_service_account_file():
    """Check if service account file exists"""
    print_section("2. Checking Service Account File")

    # Check multiple possible locations
    possible_paths = [
        Path('secrets/google-creds.json'),
        Path('presgen-service-account.json'),
        Path(os.getenv('GOOGLE_APPLICATION_CREDENTIALS', '')),
    ]

    for path in possible_paths:
        if path and path.exists():
            print_success(f"✓ Found service account file: {path}")
            return path

    print_error("✗ Service account file not found!")
    print_info("\nSearched locations:")
    for path in possible_paths:
        if path:
            print(f"  - {path}")

    print_info("\nPlease create secrets directory and copy service account:")
    print("  mkdir -p secrets")
    print("  cp presgen-service-account.json secrets/google-creds.json")

    return None

def test_service_account_authentication(credentials_path):
    """Test service account authentication"""
    print_section("3. Testing Service Account Authentication")

    try:
        from google.oauth2.service_account import Credentials

        scopes = [
            'https://www.googleapis.com/auth/presentations',
            'https://www.googleapis.com/auth/drive.file',
            'https://www.googleapis.com/auth/forms',
            'https://www.googleapis.com/auth/spreadsheets',
        ]

        print_info(f"Loading credentials from: {credentials_path}")
        creds = Credentials.from_service_account_file(
            str(credentials_path),
            scopes=scopes
        )

        print_success("✓ Service account loaded successfully")
        print_info(f"  Service account email: {creds.service_account_email}")
        print_info(f"  Project ID: {creds.project_id}")
        print_info(f"  Scopes: {len(scopes)} scopes configured")

        return creds

    except FileNotFoundError:
        print_error(f"✗ File not found: {credentials_path}")
        return None
    except Exception as e:
        print_error(f"✗ Failed to load service account: {e}")
        return None

def test_google_slides_api(creds):
    """Test Google Slides API access"""
    print_section("4. Testing Google Slides API")

    try:
        from googleapiclient.discovery import build
        from googleapiclient.errors import HttpError

        print_info("Building Google Slides service...")
        service = build('slides', 'v1', credentials=creds)

        print_success("✓ Google Slides API service created successfully")

        # Try to create a test presentation
        print_info("Creating test presentation...")
        presentation = {
            'title': 'PresGen Test - ' + str(os.getpid())
        }

        result = service.presentations().create(body=presentation).execute()
        presentation_id = result['presentationId']

        print_success(f"✓ Test presentation created successfully!")
        print_info(f"  Presentation ID: {presentation_id}")
        print_info(f"  URL: https://docs.google.com/presentation/d/{presentation_id}/edit")

        # Delete test presentation
        print_info("Cleaning up test presentation...")
        drive_service = build('drive', 'v3', credentials=creds)
        drive_service.files().delete(fileId=presentation_id).execute()
        print_success("✓ Test presentation deleted")

        return True

    except HttpError as e:
        print_error(f"✗ Google Slides API error: {e}")

        if e.resp.status == 403:
            print_error("\n⚠️  Permission denied!")
            print_info("Common causes:")
            print("  1. Google Slides API not enabled in Cloud Console")
            print("  2. Service account lacks permissions")
            print("\nTo fix:")
            print("  1. Go to: https://console.cloud.google.com/apis/library")
            print("  2. Search for 'Google Slides API'")
            print("  3. Click 'Enable'")

        return False

    except Exception as e:
        print_error(f"✗ Unexpected error: {e}")
        return False

def test_google_drive_api(creds):
    """Test Google Drive API access"""
    print_section("5. Testing Google Drive API")

    try:
        from googleapiclient.discovery import build
        from googleapiclient.errors import HttpError

        print_info("Building Google Drive service...")
        service = build('drive', 'v3', credentials=creds)

        print_success("✓ Google Drive API service created successfully")

        # List files (this tests read access)
        print_info("Testing Drive access (listing files)...")
        results = service.files().list(
            pageSize=10,
            fields="files(id, name, mimeType)"
        ).execute()

        files = results.get('files', [])
        print_success(f"✓ Drive access verified - found {len(files)} accessible files")

        return True

    except HttpError as e:
        print_error(f"✗ Google Drive API error: {e}")

        if e.resp.status == 403:
            print_error("\n⚠️  Permission denied!")
            print_info("To enable:")
            print("  1. Go to: https://console.cloud.google.com/apis/library")
            print("  2. Search for 'Google Drive API'")
            print("  3. Click 'Enable'")

        return False

    except Exception as e:
        print_error(f"✗ Unexpected error: {e}")
        return False

def test_environment_variables():
    """Test environment variable configuration"""
    print_section("6. Checking Environment Variables")

    env_vars = {
        'GOOGLE_APPLICATION_CREDENTIALS': 'Path to service account JSON',
        'GOOGLE_CLOUD_PROJECT': 'Google Cloud project ID',
        'FORCE_SERVICE_ACCOUNT': 'Force service account auth (should be "true")',
    }

    all_set = True

    for var, description in env_vars.items():
        value = os.getenv(var)
        if value:
            print_success(f"✓ {var} = {value}")
        else:
            print_error(f"✗ {var} not set ({description})")
            if var == 'GOOGLE_APPLICATION_CREDENTIALS':
                all_set = False

    if not all_set:
        print_info("\nRecommended .env configuration:")
        print("""
# Google Cloud Authentication
GOOGLE_APPLICATION_CREDENTIALS=/secrets/google-creds.json
FORCE_SERVICE_ACCOUNT=true
GOOGLE_CLOUD_PROJECT=presgen
        """)

    return all_set

def main():
    """Run all tests"""
    print(f"\n{BLUE}{'='*60}{NC}")
    print(f"{BLUE}Google Cloud Service Account Authentication Test{NC}")
    print(f"{BLUE}{'='*60}{NC}")

    # Test 1: Check dependencies
    if not check_dependencies():
        print_error("\n❌ FAILED: Missing dependencies")
        print_info("Run: pip3 install -r requirements.txt")
        return 1

    # Test 2: Check service account file
    credentials_path = check_service_account_file()
    if not credentials_path:
        print_error("\n❌ FAILED: Service account file not found")
        return 1

    # Test 3: Authenticate
    creds = test_service_account_authentication(credentials_path)
    if not creds:
        print_error("\n❌ FAILED: Could not authenticate with service account")
        return 1

    # Test 4: Test Google Slides API
    slides_ok = test_google_slides_api(creds)

    # Test 5: Test Google Drive API
    drive_ok = test_google_drive_api(creds)

    # Test 6: Check environment variables
    env_ok = test_environment_variables()

    # Summary
    print_section("Test Summary")

    results = {
        "Dependencies": True,
        "Service Account File": True,
        "Authentication": True,
        "Google Slides API": slides_ok,
        "Google Drive API": drive_ok,
        "Environment Variables": env_ok,
    }

    for test, passed in results.items():
        status = f"{GREEN}✓ PASS{NC}" if passed else f"{RED}✗ FAIL{NC}"
        print(f"  {test:30s} {status}")

    all_passed = all(results.values())

    if all_passed:
        print_success("\n✅ ALL TESTS PASSED!")
        print_info("Service account is ready for AWS deployment")
        return 0
    else:
        print_error("\n❌ SOME TESTS FAILED")
        print_info("Fix the issues above before deploying")
        return 1

if __name__ == '__main__':
    sys.exit(main())
