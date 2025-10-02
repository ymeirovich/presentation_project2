#!/usr/bin/env python3
"""Test OAuth authentication for Google Sheets."""

import os
import sys
from pathlib import Path

# OAuth credentials path
OAUTH_CLIENT_PATH = '/Users/yitzchak/Documents/learn/presentation_project/sales-agent-labs/oauth_slides_client.json'
TOKEN_PATH = '/Users/yitzchak/Documents/learn/presentation_project/sales-agent-labs/token_sheets.json'

def test_oauth():
    """Test OAuth authentication flow."""
    print("=" * 70)
    print("OAuth Authentication Test for Google Sheets")
    print("=" * 70)

    # Check if OAuth client file exists
    if not os.path.exists(OAUTH_CLIENT_PATH):
        print(f"❌ OAuth client file not found: {OAUTH_CLIENT_PATH}")
        return False

    print(f"✅ OAuth client file found: {OAUTH_CLIENT_PATH}")

    try:
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from googleapiclient.discovery import build
        from googleapiclient.errors import HttpError

        SCOPES = [
            'https://www.googleapis.com/auth/spreadsheets',
            'https://www.googleapis.com/auth/drive.file'
        ]

        creds = None

        # Check if token already exists
        if os.path.exists(TOKEN_PATH):
            print(f"✅ Found existing token: {TOKEN_PATH}")
            creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)

        # If no valid credentials, do OAuth flow
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                print("🔄 Refreshing expired token...")
                creds.refresh(Request())
                print("✅ Token refreshed successfully")
            else:
                print("\n🔐 Starting OAuth flow...")
                print("   → Browser will open for authentication")
                print("   → Log in with your Google account")
                print("   → Grant access to Google Sheets and Drive")

                flow = InstalledAppFlow.from_client_secrets_file(
                    OAUTH_CLIENT_PATH, SCOPES
                )
                creds = flow.run_local_server(port=0)  # Auto-select available port
                print("✅ OAuth authentication successful!")

            # Save token for future use
            with open(TOKEN_PATH, 'w') as token:
                token.write(creds.to_json())
            print(f"✅ Token saved to: {TOKEN_PATH}")
        else:
            print("✅ Using valid existing credentials")

        # Test API access
        print("\n🧪 Testing Google Sheets API access...")

        service = build('sheets', 'v4', credentials=creds, cache_discovery=False)

        # Create test spreadsheet
        spreadsheet_body = {
            'properties': {
                'title': 'OAuth-Test-PresGen'
            }
        }

        spreadsheet = service.spreadsheets().create(body=spreadsheet_body).execute()
        spreadsheet_id = spreadsheet['spreadsheetId']
        spreadsheet_url = f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}"

        print(f"✅ Test spreadsheet created successfully!")
        print(f"   📊 ID: {spreadsheet_id}")
        print(f"   🔗 URL: {spreadsheet_url}")

        # Add some test data
        values = [
            ['OAuth Authentication Test'],
            ['Status', 'Working ✓'],
            ['Created', 'Successfully']
        ]

        body = {
            'values': values
        }

        service.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id,
            range='A1',
            valueInputOption='RAW',
            body=body
        ).execute()

        print(f"✅ Test data added to spreadsheet")

        # Clean up - delete test spreadsheet
        drive_service = build('drive', 'v3', credentials=creds, cache_discovery=False)
        drive_service.files().delete(fileId=spreadsheet_id).execute()
        print(f"✅ Test spreadsheet deleted (cleanup)")

        print("\n" + "=" * 70)
        print("✅ OAuth Authentication Test: PASSED")
        print("=" * 70)
        print("\n📝 Summary:")
        print(f"   • OAuth client: Valid")
        print(f"   • Token saved: {TOKEN_PATH}")
        print(f"   • API access: Working")
        print(f"   • Spreadsheet creation: Successful")
        print(f"   • Data operations: Working")
        print("\n💡 OAuth authentication is fully operational!")
        print("   You can use this as an alternative to service accounts.")

        return True

    except ImportError as e:
        print(f"❌ Missing library: {e}")
        print("💡 Install with: pip install google-auth-oauthlib google-auth-httplib2")
        return False
    except HttpError as e:
        print(f"❌ API Error: {e}")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = test_oauth()
    sys.exit(0 if success else 1)
