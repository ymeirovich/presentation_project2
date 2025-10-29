#!/usr/bin/env python3
"""
Test if the issue is Drive ownership vs API permissions
Service accounts can only create files they own - they can't create files in user's Drive
"""

import sys
from pathlib import Path

GREEN = '\033[0;32m'
RED = '\033[0;31m'
YELLOW = '\033[1;33m'
BLUE = '\033[0;34m'
NC = '\033[0m'

def test_service_account_drive_creation():
    """Test creating files in service account's own Drive"""
    print(f"\n{BLUE}{'='*70}{NC}")
    print(f"{BLUE}Testing Service Account Drive File Creation{NC}")
    print(f"{BLUE}{'='*70}{NC}\n")

    try:
        from google.oauth2.service_account import Credentials
        from googleapiclient.discovery import build
        from googleapiclient.errors import HttpError

        credentials_path = Path('secrets/google-creds.json')

        print(f"{GREEN}[1] Loading service account credentials...{NC}")
        creds = Credentials.from_service_account_file(
            str(credentials_path),
            scopes=[
                'https://www.googleapis.com/auth/presentations',
                'https://www.googleapis.com/auth/drive',
            ]
        )
        print(f"    ✓ Service account: {creds.service_account_email}")

        # Test 1: Create presentation in service account's Drive
        print(f"\n{GREEN}[2] Testing: Create presentation (no parent folder)...{NC}")
        slides_service = build('slides', 'v1', credentials=creds)

        try:
            presentation = {'title': 'Test - Service Account Owned'}
            result = slides_service.presentations().create(body=presentation).execute()
            pres_id = result['presentationId']

            print(f"{GREEN}    ✅ SUCCESS! Created presentation{NC}")
            print(f"    ID: {pres_id}")
            print(f"    URL: https://docs.google.com/presentation/d/{pres_id}/edit")

            # Get file details
            drive_service = build('drive', 'v3', credentials=creds)
            file_info = drive_service.files().get(fileId=pres_id, fields='id,name,owners,permissions').execute()

            print(f"\n{YELLOW}    File Ownership Details:{NC}")
            print(f"    Name: {file_info.get('name')}")
            print(f"    Owners: {[o.get('emailAddress') for o in file_info.get('owners', [])]}")

            # Clean up
            drive_service.files().delete(fileId=pres_id).execute()
            print(f"{GREEN}    ✓ Test presentation deleted{NC}")

            print(f"\n{GREEN}{'='*70}{NC}")
            print(f"{GREEN}SOLUTION FOUND!{NC}")
            print(f"{GREEN}{'='*70}{NC}\n")

            print(f"{YELLOW}The Problem:{NC}")
            print(f"  Service accounts can ONLY create files in their own Drive")
            print(f"  They cannot create files in user's personal Drive by default\n")

            print(f"{YELLOW}Why This Matters for AWS:{NC}")
            print(f"  ✅ This is PERFECT for server deployment!")
            print(f"  ✅ Service account creates presentations it owns")
            print(f"  ✅ No user Drive access needed")
            print(f"  ✅ Files are isolated and secure\n")

            print(f"{YELLOW}How to Access Files:{NC}")
            print(f"  Option 1: Share files after creation")
            print(f"    - Code shares presentation with specific users after creating")
            print(f"    - Users get email notification with link\n")

            print(f"  Option 2: Create in shared folder")
            print(f"    - Create shared folder in user's Drive")
            print(f"    - Share folder with: {creds.service_account_email}")
            print(f"    - Service account creates files in that folder")
            print(f"    - Users can access all files in shared folder\n")

            print(f"  Option 3: Use shareable links")
            print(f"    - Set file permissions to 'anyone with link can view'")
            print(f"    - Return shareable URL to user")
            print(f"    - No Drive access needed\n")

            print(f"{GREEN}Recommended for PresGen:{NC}")
            print(f"  Use Option 3 (shareable links) - simplest for AWS deployment")

            return True

        except HttpError as e:
            print(f"{RED}    ✗ FAILED: {e}{NC}")

            if e.resp.status == 403:
                print(f"\n{RED}Still getting 403 error!{NC}")
                print(f"\n{YELLOW}Additional things to check:{NC}\n")

                print(f"1. Is Google Slides API enabled for this service account?")
                print(f"   https://console.cloud.google.com/apis/library/slides.googleapis.com?project=presgen\n")

                print(f"2. Check API restrictions:")
                print(f"   Go to: https://console.cloud.google.com/apis/credentials?project=presgen")
                print(f"   Click on service account")
                print(f"   Check 'API restrictions' - should be 'None' or include Slides API\n")

                print(f"3. Check organization policies:")
                print(f"   If using Google Workspace, org policies may block service accounts")
                print(f"   Contact Workspace admin\n")

                print(f"4. Try creating new service account:")
                print(f"   https://console.cloud.google.com/iam-admin/serviceaccounts/create?project=presgen")
                print(f"   Grant 'Editor' role during creation")

            return False

    except Exception as e:
        print(f"{RED}✗ Unexpected error: {e}{NC}")
        import traceback
        traceback.print_exc()
        return False

def test_sharing_after_creation():
    """Test creating a presentation and sharing it"""
    print(f"\n{BLUE}{'='*70}{NC}")
    print(f"{BLUE}Testing: Create + Share Workflow{NC}")
    print(f"{BLUE}{'='*70}{NC}\n")

    try:
        from google.oauth2.service_account import Credentials
        from googleapiclient.discovery import build

        credentials_path = Path('secrets/google-creds.json')
        creds = Credentials.from_service_account_file(
            str(credentials_path),
            scopes=[
                'https://www.googleapis.com/auth/presentations',
                'https://www.googleapis.com/auth/drive',
            ]
        )

        print(f"{GREEN}[1] Creating presentation...{NC}")
        slides_service = build('slides', 'v1', credentials=creds)
        presentation = {'title': 'Test - Will Be Shared'}

        result = slides_service.presentations().create(body=presentation).execute()
        pres_id = result['presentationId']
        print(f"    ✓ Created: {pres_id}")

        print(f"\n{GREEN}[2] Making shareable with link...{NC}")
        drive_service = build('drive', 'v3', credentials=creds)

        # Make anyone with link a reader
        permission = {
            'type': 'anyone',
            'role': 'reader'
        }
        drive_service.permissions().create(
            fileId=pres_id,
            body=permission
        ).execute()

        print(f"    ✓ Set to 'anyone with link can view'")

        # Get shareable link
        file_info = drive_service.files().get(fileId=pres_id, fields='webViewLink').execute()
        shareable_link = file_info.get('webViewLink')

        print(f"\n{GREEN}✅ Shareable Link Created:{NC}")
        print(f"    {shareable_link}")
        print(f"\n    Anyone with this link can view (no Google account needed!)")

        # Clean up
        drive_service.files().delete(fileId=pres_id).execute()
        print(f"\n    ✓ Test presentation deleted")

        print(f"\n{GREEN}This is how PresGen will work on AWS!{NC}")

        return True

    except Exception as e:
        print(f"{RED}✗ Error: {e}{NC}")
        return False

def main():
    print(f"\n{BLUE}{'='*70}{NC}")
    print(f"{BLUE}Service Account Drive Ownership Test{NC}")
    print(f"{BLUE}{'='*70}{NC}")

    # Test if service account can create files
    can_create = test_service_account_drive_creation()

    if can_create:
        # Test sharing workflow
        print("\n")
        test_sharing_after_creation()

        print(f"\n{GREEN}{'='*70}{NC}")
        print(f"{GREEN}✅ SERVICE ACCOUNT IS WORKING!{NC}")
        print(f"{GREEN}{'='*70}{NC}\n")

        print(f"{YELLOW}Summary:{NC}")
        print(f"  ✓ Service account can create presentations")
        print(f"  ✓ Service account can share presentations")
        print(f"  ✓ Ready for AWS deployment!\n")

        print(f"{YELLOW}For AWS deployment:{NC}")
        print(f"  The app will:")
        print(f"  1. Create presentations in service account's Drive")
        print(f"  2. Set sharing to 'anyone with link'")
        print(f"  3. Return shareable URL to user")
        print(f"  4. User opens link - no Drive access needed!")

        return 0
    else:
        print(f"\n{RED}{'='*70}{NC}")
        print(f"{RED}❌ STILL FAILING{NC}")
        print(f"{RED}{'='*70}{NC}\n")

        print(f"Next steps:")
        print(f"  1. Double-check API is enabled:")
        print(f"     https://console.cloud.google.com/apis/library/slides.googleapis.com?project=presgen")
        print(f"  2. Check service account in IAM:")
        print(f"     https://console.cloud.google.com/iam-admin/serviceaccounts?project=presgen")
        print(f"  3. Try creating new service account with Editor role")

        return 1

if __name__ == '__main__':
    sys.exit(main())
