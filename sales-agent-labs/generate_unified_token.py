#!/usr/bin/env python3
"""Generate unified OAuth token with all required scopes for all services."""

import os
import sys
from pathlib import Path

# All scopes needed by all services
ALL_SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',      # Google Sheets
    'https://www.googleapis.com/auth/drive.file',         # Google Drive
    'https://www.googleapis.com/auth/presentations',      # Google Slides
    'https://www.googleapis.com/auth/script.projects'     # Apps Script
]

OAUTH_CLIENT_PATH = '/Users/yitzchak/Documents/learn/presentation_project/sales-agent-labs/oauth_slides_client.json'
TOKEN_PATH = '/Users/yitzchak/Documents/learn/presentation_project/sales-agent-labs/token.json'

def generate_token():
    """Generate unified OAuth token with all scopes."""
    print("=" * 70)
    print("Unified OAuth Token Generator")
    print("=" * 70)
    print(f"\n📋 Scopes to be included:")
    for scope in ALL_SCOPES:
        print(f"   • {scope}")

    # Check OAuth client exists
    if not os.path.exists(OAUTH_CLIENT_PATH):
        print(f"\n❌ OAuth client not found: {OAUTH_CLIENT_PATH}")
        return False

    print(f"\n✅ OAuth client found: {OAUTH_CLIENT_PATH}")

    try:
        from google_auth_oauthlib.flow import InstalledAppFlow

        print("\n🔐 Starting OAuth flow...")
        print("   → Browser will open for authentication")
        print("   → Log in with your Google account")
        print("   → Grant access to ALL scopes (Sheets, Drive, Slides, Script)")
        print()

        flow = InstalledAppFlow.from_client_secrets_file(
            OAUTH_CLIENT_PATH,
            ALL_SCOPES
        )

        # Force consent to ensure all scopes are granted
        creds = flow.run_local_server(port=0, prompt='consent')

        print("✅ OAuth authentication successful!")

        # Save token
        with open(TOKEN_PATH, 'w') as token:
            token.write(creds.to_json())

        print(f"✅ Unified token saved to: {TOKEN_PATH}")

        # Verify scopes
        print(f"\n📋 Token scopes verified:")
        import json
        with open(TOKEN_PATH) as f:
            token_data = json.load(f)
            saved_scopes = token_data.get('scopes', [])
            for scope in saved_scopes:
                print(f"   ✓ {scope}")

        # Check all required scopes are present
        missing_scopes = set(ALL_SCOPES) - set(saved_scopes)
        if missing_scopes:
            print(f"\n⚠️  Warning: Missing scopes:")
            for scope in missing_scopes:
                print(f"   ✗ {scope}")
            return False

        print("\n" + "=" * 70)
        print("✅ Unified OAuth Token Generation: SUCCESS")
        print("=" * 70)
        print("\n📝 Summary:")
        print(f"   • Token saved to: {TOKEN_PATH}")
        print(f"   • Total scopes: {len(saved_scopes)}")
        print(f"   • All services ready: Sheets, Drive, Slides, Script")
        print(f"   • Has refresh_token: {'refresh_token' in token_data}")
        print("\n💡 All services can now use this unified token!")

        return True

    except ImportError as e:
        print(f"❌ Missing library: {e}")
        print("💡 Install with: pip install google-auth-oauthlib")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = generate_token()
    sys.exit(0 if success else 1)
