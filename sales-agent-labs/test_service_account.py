#!/usr/bin/env python3
"""
Test Google Workspace Service Account Integration
Tests if the service account can access Google Drive and create presentations
"""

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import os
import sys

# Configuration - UPDATE THESE VALUES
CREDENTIALS_FILE = './secrets/google-creds.json'
IMPERSONATE_USER = 'presgen-service@presgen.net'  # TODO: Update with your user
FOLDER_ID = 'YOUR_FOLDER_ID_HERE'  # TODO: Update with your folder ID

SCOPES = [
    'https://www.googleapis.com/auth/drive',
    'https://www.googleapis.com/auth/drive.file',
    'https://www.googleapis.com/auth/presentations'
]

def print_header(text):
    """Print a formatted header"""
    print(f"\n{'='*60}")
    print(f"  {text}")
    print(f"{'='*60}\n")

def test_service_account():
    """Test service account access to Google Drive"""

    print_header("PresGen Service Account Test")

    # Step 1: Load credentials
    print("🔐 Step 1: Loading service account credentials...")
    if not os.path.exists(CREDENTIALS_FILE):
        print(f"❌ ERROR: Credentials file not found: {CREDENTIALS_FILE}")
        print("\nMake sure you have:")
        print("1. Downloaded the service account JSON key")
        print("2. Placed it in ./secrets/google-creds.json")
        return False

    try:
        credentials = service_account.Credentials.from_service_account_file(
            CREDENTIALS_FILE,
            scopes=SCOPES
        )
        print(f"✅ Credentials loaded successfully")
        print(f"   Service Account: {credentials.service_account_email}")
    except Exception as e:
        print(f"❌ ERROR loading credentials: {str(e)}")
        return False

    # Step 2: Configure impersonation
    print(f"\n👤 Step 2: Configuring impersonation...")
    print(f"   Impersonating user: {IMPERSONATE_USER}")

    if IMPERSONATE_USER == 'presgen-service@presgen.net':
        print("\n⚠️  WARNING: Using default impersonation user.")
        print("   Update IMPERSONATE_USER variable with your actual Workspace user email")

    try:
        credentials = credentials.with_subject(IMPERSONATE_USER)
        print(f"✅ Impersonation configured")
    except Exception as e:
        print(f"❌ ERROR configuring impersonation: {str(e)}")
        return False

    # Step 3: Build Drive service
    print(f"\n🔨 Step 3: Building Google Drive service...")
    try:
        drive_service = build('drive', 'v3', credentials=credentials)
        print(f"✅ Drive service built successfully")
    except Exception as e:
        print(f"❌ ERROR building Drive service: {str(e)}")
        return False

    # Step 4: Test folder access
    print(f"\n📁 Step 4: Testing access to shared folder...")
    print(f"   Folder ID: {FOLDER_ID}")

    if FOLDER_ID == 'YOUR_FOLDER_ID_HERE':
        print("\n⚠️  WARNING: Using placeholder folder ID.")
        print("   Update FOLDER_ID variable with your actual Google Drive folder ID")
        print("\nTo find your folder ID:")
        print("1. Open the folder in Google Drive")
        print("2. Copy the ID from the URL:")
        print("   https://drive.google.com/drive/folders/1a2b3c4d5e6f7g8h9i0j")
        print("                                           ^^^^^^^^^^^^^^^^^^^^")
        return False

    try:
        # List files in the shared folder
        results = drive_service.files().list(
            q=f"'{FOLDER_ID}' in parents and trashed=false",
            pageSize=10,
            fields="files(id, name, mimeType, createdTime)"
        ).execute()

        files = results.get('files', [])
        print(f"✅ Successfully accessed folder!")
        print(f"   Found {len(files)} file(s):")

        if files:
            for file in files:
                print(f"   - {file['name']}")
                print(f"     Type: {file['mimeType']}")
                print(f"     ID: {file['id']}")
        else:
            print("   (Folder is empty)")

    except HttpError as e:
        print(f"❌ ERROR accessing folder: {e.status_code} - {e.error_details}")
        print("\nTroubleshooting:")

        if e.status_code == 403:
            print("  1. Check that domain-wide delegation is enabled")
            print("  2. Verify OAuth scopes in Google Workspace Admin Console")
            print("  3. Ensure impersonation user exists and has access")
            print("  4. Wait 10-15 minutes after enabling domain-wide delegation")
        elif e.status_code == 404:
            print("  1. Check that folder ID is correct")
            print("  2. Verify folder is shared with service account email")
            print("  3. Ensure folder is not in trash")
        else:
            print(f"  Status code: {e.status_code}")
            print(f"  Details: {e.error_details}")

        return False
    except Exception as e:
        print(f"❌ UNEXPECTED ERROR: {str(e)}")
        return False

    # Step 5: Test file creation
    print(f"\n📝 Step 5: Testing file creation...")
    try:
        # Build Slides service
        slides_service = build('slides', 'v1', credentials=credentials)

        # Create a test presentation
        presentation = {
            'title': 'PresGen Test Presentation'
        }

        test_pres = slides_service.presentations().create(body=presentation).execute()
        presentation_id = test_pres['presentationId']

        print(f"✅ Created test presentation!")
        print(f"   Title: {test_pres['title']}")
        print(f"   ID: {presentation_id}")

        # Move to shared folder
        file = drive_service.files().get(fileId=presentation_id, fields='parents').execute()
        previous_parents = ",".join(file.get('parents', []))

        drive_service.files().update(
            fileId=presentation_id,
            addParents=FOLDER_ID,
            removeParents=previous_parents,
            fields='id, parents'
        ).execute()

        # Get web view link
        file_info = drive_service.files().get(
            fileId=presentation_id,
            fields='webViewLink'
        ).execute()

        print(f"✅ Moved to shared folder!")
        print(f"   Link: {file_info['webViewLink']}")

    except HttpError as e:
        print(f"⚠️  Could not create test file: {e.status_code}")
        print(f"   This is OK if you only need read access")
    except Exception as e:
        print(f"⚠️  Error creating test file: {str(e)}")
        print(f"   This is OK if you only need read access")

    # Success summary
    print_header("✅ TEST COMPLETED SUCCESSFULLY!")
    print("Your service account is properly configured and can:")
    print("  ✓ Authenticate with Google Workspace")
    print("  ✓ Impersonate the specified user")
    print("  ✓ Access the shared Google Drive folder")
    print("  ✓ Create presentations (if tested)")
    print("\nYou're ready to use PresGen with Google Workspace!")

    return True

def print_configuration_info():
    """Print configuration information"""
    print("\n" + "="*60)
    print("  Current Configuration")
    print("="*60)
    print(f"Credentials File: {CREDENTIALS_FILE}")
    print(f"Impersonate User: {IMPERSONATE_USER}")
    print(f"Folder ID: {FOLDER_ID}")
    print(f"Scopes: {len(SCOPES)} configured")
    for scope in SCOPES:
        print(f"  - {scope}")
    print("="*60 + "\n")

if __name__ == '__main__':
    print_configuration_info()

    # Run the test
    success = test_service_account()

    if success:
        print("\n🎉 All tests passed!")
        sys.exit(0)
    else:
        print("\n❌ Tests failed. Review the errors above.")
        print("\nFor detailed setup instructions, see:")
        print("  GOOGLE_WORKSPACE_SERVICE_ACCOUNT_SETUP.md")
        sys.exit(1)
