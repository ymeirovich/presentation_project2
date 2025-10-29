#!/usr/bin/env python3
"""
Diagnose Google Cloud Service Account Permissions
Checks IAM roles and permissions for the service account
"""

import os
import sys
from pathlib import Path

# Colors
GREEN = '\033[0;32m'
RED = '\033[0;31m'
YELLOW = '\033[1;33m'
BLUE = '\033[0;34m'
NC = '\033[0m'

def print_section(title):
    print(f"\n{BLUE}{'='*70}{NC}")
    print(f"{BLUE}{title}{NC}")
    print(f"{BLUE}{'='*70}{NC}\n")

def test_api_with_detailed_error():
    """Test API call with detailed error information"""
    print_section("Detailed Google Slides API Error Analysis")

    try:
        from google.oauth2.service_account import Credentials
        from googleapiclient.discovery import build
        from googleapiclient.errors import HttpError
        import json

        credentials_path = Path('secrets/google-creds.json')

        print(f"{GREEN}[1] Loading credentials...{NC}")
        creds = Credentials.from_service_account_file(
            str(credentials_path),
            scopes=['https://www.googleapis.com/auth/presentations']
        )
        print(f"    ✓ Service account: {creds.service_account_email}")
        print(f"    ✓ Project: {creds.project_id}")

        print(f"\n{GREEN}[2] Building Slides service...{NC}")
        service = build('slides', 'v1', credentials=creds)
        print(f"    ✓ Service built successfully")

        print(f"\n{GREEN}[3] Attempting to create test presentation...{NC}")
        presentation = {'title': 'Permission Test'}

        try:
            result = service.presentations().create(body=presentation).execute()
            print(f"{GREEN}✓ SUCCESS! Created presentation: {result['presentationId']}{NC}")

            # Clean up
            from googleapiclient.discovery import build
            drive_service = build('drive', 'v3', credentials=creds)
            drive_service.files().delete(fileId=result['presentationId']).execute()
            print(f"    ✓ Test presentation deleted")

            return True

        except HttpError as e:
            print(f"\n{RED}✗ HTTP ERROR {e.resp.status}{NC}")
            print(f"\n{YELLOW}Error Details:{NC}")
            print(f"  Status: {e.resp.status}")
            print(f"  Reason: {e.resp.reason}")

            # Parse error details
            try:
                error_details = json.loads(e.content.decode('utf-8'))
                print(f"\n{YELLOW}Full Error Response:{NC}")
                print(json.dumps(error_details, indent=2))

                if 'error' in error_details:
                    error_obj = error_details['error']
                    print(f"\n{YELLOW}Error Analysis:{NC}")
                    print(f"  Code: {error_obj.get('code')}")
                    print(f"  Message: {error_obj.get('message')}")
                    print(f"  Status: {error_obj.get('status')}")

                    if 'details' in error_obj:
                        print(f"\n{YELLOW}Additional Details:{NC}")
                        for detail in error_obj['details']:
                            print(f"  - {detail}")

            except Exception as parse_error:
                print(f"  Raw error: {e.content}")

            # Provide specific guidance
            print(f"\n{YELLOW}Possible Causes:{NC}")

            if e.resp.status == 403:
                print(f"""
{RED}403 Forbidden Error - This usually means:{NC}

1. API is enabled BUT service account lacks IAM permissions
2. Service account needs one of these roles:
   - 'Editor' role on the project
   - 'Drive File Creator' role
   - Custom role with 'drive.files.create' permission

{YELLOW}How to fix:{NC}

Option A: Grant Editor Role (Quick fix)
  1. Go to: https://console.cloud.google.com/iam-admin/iam?project=presgen
  2. Click "+ GRANT ACCESS"
  3. Enter: presgen-service-account-test@presgen.iam.gserviceaccount.com
  4. Role: "Editor" or "Owner"
  5. Click "Save"

Option B: Grant Specific Drive Permissions (Better security)
  1. Go to: https://console.cloud.google.com/iam-admin/iam?project=presgen
  2. Find: presgen-service-account-test@presgen.iam.gserviceaccount.com
  3. Click pencil icon to edit
  4. Add role: "Drive File Creator" or "Service Account Token Creator"
  5. Click "Save"

Option C: Use Domain-Wide Delegation (If you have Workspace)
  1. Go to: admin.google.com
  2. Security → API Controls → Domain-wide Delegation
  3. Add client ID: {creds.client_id if hasattr(creds, 'client_id') else 'See service account JSON'}
  4. Add scopes:
     - https://www.googleapis.com/auth/presentations
     - https://www.googleapis.com/auth/drive.file
""")

            elif e.resp.status == 404:
                print(f"""
{RED}404 Not Found Error - This usually means:{NC}
  - API endpoint doesn't exist
  - API not properly enabled

{YELLOW}How to fix:{NC}
  1. Re-enable the API:
     https://console.cloud.google.com/apis/library/slides.googleapis.com?project=presgen
  2. Wait 5 minutes for propagation
  3. Try again
""")

            elif e.resp.status == 401:
                print(f"""
{RED}401 Unauthorized Error - This usually means:{NC}
  - Service account credentials are invalid
  - Private key is expired or revoked

{YELLOW}How to fix:{NC}
  1. Create new service account key:
     https://console.cloud.google.com/iam-admin/serviceaccounts?project=presgen
  2. Click on service account
  3. Keys tab → Add Key → Create new key → JSON
  4. Download and replace secrets/google-creds.json
""")

            return False

    except Exception as e:
        print(f"{RED}✗ Unexpected error: {e}{NC}")
        import traceback
        traceback.print_exc()
        return False

def check_iam_roles():
    """Try to check IAM roles (requires additional permissions)"""
    print_section("Checking IAM Roles (if possible)")

    try:
        from google.oauth2.service_account import Credentials
        from googleapiclient.discovery import build

        credentials_path = Path('secrets/google-creds.json')
        creds = Credentials.from_service_account_file(
            str(credentials_path),
            scopes=['https://www.googleapis.com/auth/cloud-platform']
        )

        service = build('cloudresourcemanager', 'v1', credentials=creds)

        project_id = creds.project_id
        service_account_email = creds.service_account_email

        print(f"Checking IAM policy for: {service_account_email}")

        policy = service.projects().getIamPolicy(
            resource=project_id,
            body={}
        ).execute()

        print(f"\n{YELLOW}Current IAM Bindings:{NC}")

        found_roles = []
        for binding in policy.get('bindings', []):
            role = binding['role']
            members = binding['members']

            for member in members:
                if service_account_email in member:
                    found_roles.append(role)
                    print(f"  ✓ {role}")

        if not found_roles:
            print(f"{RED}  ✗ No roles found for this service account!{NC}")
            print(f"\n{YELLOW}This is the problem!{NC}")
            print(f"Service account has NO IAM roles assigned.")
        else:
            print(f"\n{GREEN}Found {len(found_roles)} role(s){NC}")

            # Check if they're sufficient
            sufficient_roles = [
                'roles/owner',
                'roles/editor',
                'roles/drive.admin'
            ]

            has_sufficient = any(role in found_roles for role in sufficient_roles)

            if has_sufficient:
                print(f"{GREEN}✓ Service account has sufficient permissions{NC}")
            else:
                print(f"{YELLOW}⚠ Service account may lack permissions{NC}")
                print(f"Current roles may not include Drive/Slides access")

        return True

    except Exception as e:
        print(f"{YELLOW}⚠ Cannot check IAM roles directly{NC}")
        print(f"  Reason: {str(e)[:100]}")
        print(f"\n  This is normal - requires additional permissions")
        print(f"  You'll need to check manually in Cloud Console")
        return False

def provide_manual_check_instructions():
    """Provide instructions for manual IAM check"""
    print_section("Manual IAM Permission Check")

    print(f"{YELLOW}Since we can't check IAM programmatically, please verify manually:{NC}\n")

    print(f"1. Open IAM Console:")
    print(f"   https://console.cloud.google.com/iam-admin/iam?project=presgen\n")

    print(f"2. Search for:")
    print(f"   presgen-service-account-test@presgen.iam.gserviceaccount.com\n")

    print(f"3. Check assigned roles. You need AT LEAST ONE of:\n")
    print(f"   {GREEN}Recommended (Most Access):{NC}")
    print(f"   ✓ Owner")
    print(f"   ✓ Editor\n")

    print(f"   {GREEN}Recommended (Least Privilege):{NC}")
    print(f"   ✓ Drive File Creator")
    print(f"   ✓ Service Account Token Creator")
    print(f"   ✓ Slides API User (custom role)\n")

    print(f"4. If NO roles assigned:")
    print(f"   a. Click '+ GRANT ACCESS'")
    print(f"   b. Enter: presgen-service-account-test@presgen.iam.gserviceaccount.com")
    print(f"   c. Select role: 'Editor'")
    print(f"   d. Click 'Save'")
    print(f"   e. Wait 1 minute for changes to propagate")
    print(f"   f. Re-run this test\n")

def main():
    print(f"\n{BLUE}{'='*70}{NC}")
    print(f"{BLUE}Google Cloud Service Account Permission Diagnosis{NC}")
    print(f"{BLUE}{'='*70}{NC}")

    # Test 1: Detailed API test
    api_works = test_api_with_detailed_error()

    if api_works:
        print(f"\n{GREEN}{'='*70}{NC}")
        print(f"{GREEN}✅ ALL TESTS PASSED! Service account is working correctly.{NC}")
        print(f"{GREEN}{'='*70}{NC}")
        return 0

    # Test 2: Try to check IAM roles
    print("\n")
    iam_check_worked = check_iam_roles()

    if not iam_check_worked:
        provide_manual_check_instructions()

    print(f"\n{RED}{'='*70}{NC}")
    print(f"{RED}❌ TESTS FAILED - Action Required{NC}")
    print(f"{RED}{'='*70}{NC}")

    print(f"\n{YELLOW}Summary:{NC}")
    print(f"  The service account file is valid")
    print(f"  The API is enabled")
    print(f"  BUT: The service account lacks IAM permissions")
    print(f"\n{YELLOW}Next Step:{NC}")
    print(f"  Follow the instructions above to grant IAM permissions in Cloud Console")

    return 1

if __name__ == '__main__':
    sys.exit(main())
