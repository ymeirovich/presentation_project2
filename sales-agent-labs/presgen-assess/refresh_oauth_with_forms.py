#!/usr/bin/env python3
"""
Re-authenticate Google OAuth to include Forms API scope.

This script will:
1. Delete the existing token.json
2. Prompt you to re-authenticate with Forms scope included
3. Save the new token with all required scopes
"""

import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

# All required scopes for PresGen
SCOPES = [
    'https://www.googleapis.com/auth/forms.body',  # Create and edit forms
    'https://www.googleapis.com/auth/drive.file',  # Access Drive files created by this app
    'https://www.googleapis.com/auth/presentations',  # Google Slides
    'https://www.googleapis.com/auth/spreadsheets',  # Google Sheets
    'https://www.googleapis.com/auth/script.projects',  # Apps Script
]

def main():
    # Paths
    token_path = Path(__file__).parent.parent / 'token.json'
    credentials_path = Path(__file__).parent.parent / 'oauth_slides_client.json'

    if not credentials_path.exists():
        print(f"❌ OAuth client credentials not found: {credentials_path}")
        print("Please ensure oauth_slides_client.json exists in the sales-agent-labs directory")
        sys.exit(1)

    print("🔐 Google OAuth Re-authentication for Forms API")
    print("=" * 60)
    print()
    print("Current scopes in token.json:")

    if token_path.exists():
        creds = Credentials.from_authorized_user_file(str(token_path))
        for scope in creds.scopes or []:
            print(f"  ✓ {scope}")
        print()
        print("Missing scope:")
        print(f"  ✗ https://www.googleapis.com/auth/forms.body")
        print()

        response = input("Delete existing token and re-authenticate? [y/N]: ")
        if response.lower() != 'y':
            print("Cancelled.")
            sys.exit(0)

        # Backup the old token
        backup_path = token_path.with_suffix('.json.backup')
        token_path.rename(backup_path)
        print(f"✓ Backed up old token to: {backup_path}")

    print()
    print("🌐 Starting OAuth flow with Forms scope...")
    print()
    print("Required scopes:")
    for scope in SCOPES:
        print(f"  • {scope}")
    print()

    # Start OAuth flow
    flow = InstalledAppFlow.from_client_secrets_file(
        str(credentials_path),
        scopes=SCOPES
    )

    creds = flow.run_local_server(port=0)

    # Save the credentials
    with open(token_path, 'w') as token_file:
        token_file.write(creds.to_json())

    print()
    print("=" * 60)
    print("✅ Authentication successful!")
    print(f"✓ New token saved to: {token_path}")
    print()
    print("New scopes:")
    for scope in creds.scopes:
        print(f"  ✓ {scope}")
    print()
    print("🎉 You can now create Google Forms!")
    print()
    print("Next steps:")
    print("  1. Restart the PresGen-Assess service")
    print("  2. Create a new assessment workflow")
    print("  3. The Google Form should be created successfully")

if __name__ == '__main__':
    main()
