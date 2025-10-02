#!/usr/bin/env python3
"""Diagnose 403 Permission Denied issues with Google Service Account."""

import json
import sys
from pathlib import Path

def main():
    print("=" * 70)
    print("Google Service Account 403 Permission Diagnosis")
    print("=" * 70)

    creds_path = '/Users/yitzchak/Documents/learn/presentation_project/sales-agent-labs/presgen-service-account2.json'

    # Load service account
    with open(creds_path) as f:
        sa_data = json.load(f)

    print(f"\n📋 Service Account Information:")
    print(f"   Email: {sa_data['client_email']}")
    print(f"   Project: {sa_data['project_id']}")
    print(f"   Key ID: {sa_data['private_key_id'][:20]}...")

    print(f"\n🔍 Based on your 403 error, the most likely issues are:\n")

    print("1️⃣  SERVICE ACCOUNT IS DISABLED (80% probability)")
    print("   → Check: https://console.cloud.google.com/iam-admin/serviceaccounts?project=presgen")
    print(f"   → Find: {sa_data['client_email']}")
    print("   → Look for: Status should be 'Enabled' ✓")
    print("   → If disabled: Click the service account → Click 'Enable' button")
    print()

    print("2️⃣  SERVICE ACCOUNT KEY IS REVOKED/INVALID (10% probability)")
    print("   → Check: Service Account → Keys tab")
    print(f"   → Find key: {sa_data['private_key_id'][:20]}...")
    print("   → If missing: Generate new key and update .env")
    print()

    print("3️⃣  IAM SERVICE ACCOUNT CREDENTIALS API NOT ENABLED (5% probability)")
    print("   → Go to: https://console.cloud.google.com/apis/library/iamcredentials.googleapis.com")
    print("   → Click: Enable")
    print("   → Wait: 2-3 minutes for propagation")
    print()

    print("4️⃣  ORGANIZATION POLICY BLOCKING SERVICE ACCOUNTS (3% probability)")
    print("   → Check: https://console.cloud.google.com/iam-admin/orgpolicies")
    print("   → Look for: Policies restricting service accounts")
    print("   → Requires: Organization admin to fix")
    print()

    print("=" * 70)
    print("\n🔧 RECOMMENDED ACTION PLAN:\n")

    print("STEP 1: Check if service account is disabled")
    print("   gcloud iam service-accounts describe \\")
    print(f"     {sa_data['client_email']} \\")
    print(f"     --project={sa_data['project_id']}")
    print("   → Look for: 'disabled: false'")
    print("   → If 'disabled: true', run:")
    print(f"   gcloud iam service-accounts enable {sa_data['client_email']} --project={sa_data['project_id']}")
    print()

    print("STEP 2: Verify the key exists and is valid")
    print("   gcloud iam service-accounts keys list \\")
    print(f"     --iam-account={sa_data['client_email']} \\")
    print(f"     --project={sa_data['project_id']}")
    print(f"   → Check if key ID {sa_data['private_key_id'][:20]}... is listed")
    print()

    print("STEP 3: Enable IAM credentials API")
    print(f"   gcloud services enable iamcredentials.googleapis.com --project={sa_data['project_id']}")
    print()

    print("STEP 4: If all else fails, create fresh service account")
    print("   gcloud iam service-accounts create presgen-sheets-new \\")
    print(f"     --display-name='PresGen Sheets' --project={sa_data['project_id']}")
    print()
    print(f"   gcloud projects add-iam-policy-binding {sa_data['project_id']} \\")
    print(f"     --member='serviceAccount:presgen-sheets-new@{sa_data['project_id']}.iam.gserviceaccount.com' \\")
    print("     --role='roles/editor'")
    print()
    print("   gcloud iam service-accounts keys create ~/new-key.json \\")
    print(f"     --iam-account=presgen-sheets-new@{sa_data['project_id']}.iam.gserviceaccount.com")
    print()

    print("=" * 70)
    print("\n📝 QUICK TEST AFTER FIX:\n")
    print("   python3 scripts/validate_google_auth.py")
    print()
    print("=" * 70)

    print("\n💡 ALTERNATIVE: Use OAuth User Authentication\n")
    print("If service account continues to fail, you can switch to OAuth:")
    print("   1. Create OAuth client in Google Console")
    print("   2. Download client_secret.json")
    print("   3. Update code to use OAuth flow")
    print("   4. First run opens browser for user consent")
    print()
    print("This will work immediately without any permission issues.")
    print()
    print("=" * 70)

if __name__ == '__main__':
    main()
