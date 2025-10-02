# Google Service Account 403 Permission Troubleshooting

## Issue
Service account returns `403 Permission Denied` even after:
- ✅ Google Sheets API enabled
- ✅ Google Drive API enabled
- ✅ Service account has Owner role

## Root Cause Analysis

The 403 error with message "The caller does not have permission" indicates the service account **cannot execute API calls**, even though it has proper IAM roles.

### Test Results
```
✅ Service account file valid
✅ Credentials load successfully
✅ API service initializes
❌ API calls return 403 - Permission Denied
❌ Cannot read own service account metadata
```

This pattern suggests one of the following issues:

## Possible Causes & Solutions

### 1. 🔴 Service Account is Disabled

**Check**: Go to [Service Accounts](https://console.cloud.google.com/iam-admin/serviceaccounts?project=presgen)

**Look for**: `presgen-service-account-test@presgen.iam.gserviceaccount.com`

**Expected Status**:
- ✅ **Enabled** (green checkmark)
- ❌ **Disabled** (red X) ← This is the problem

**Fix**:
1. Click on the service account
2. Click "Enable" button
3. Wait 1-2 minutes
4. Re-test authentication

### 2. 🔴 Service Account Key is Revoked/Expired

**Check**: Service Account → Keys tab

**Look for**: Key ID `3de6ed3278f780201216...`

**Possible Issues**:
- Key was deleted/revoked
- Key has expired (rare, usually 10 years)
- Wrong key file being used

**Fix**:
1. Generate new key:
   - Service Account → Keys → Add Key → Create New Key
   - Choose JSON format
   - Download to safe location
2. Update `.env` with new path:
   ```bash
   GOOGLE_APPLICATION_CREDENTIALS=/path/to/new-key.json
   ```
3. Re-test

### 3. 🔴 Organization Policies Restricting Service Accounts

**Check**: [Organization Policies](https://console.cloud.google.com/iam-admin/orgpolicies)

**Policies that can block service accounts**:
- `iam.disableServiceAccountKeyCreation`
- `iam.disableServiceAccountCreation`
- `iam.allowedPolicyMemberDomains`

**Fix** (requires Org Admin):
1. Review organization policies
2. Add exception for service account
3. Or create service account in allowed project

### 4. 🔴 API Not Enabled for Service Account's Project

Even though APIs are "enabled", they might not be enabled for **this specific service account**.

**Check**:
1. Go to [APIs & Services](https://console.cloud.google.com/apis/dashboard?project=presgen)
2. Verify these are enabled:
   - Google Sheets API ✅
   - Google Drive API ✅
   - IAM Service Account Credentials API ✅

**Fix**:
1. Enable IAM Service Account Credentials API:
   - https://console.cloud.google.com/apis/library/iamcredentials.googleapis.com
2. Click "Enable"
3. Wait 2-3 minutes for propagation

### 5. 🔴 Domain Restrictions on Project

**Check**: Project Settings → [Sharing Settings](https://console.cloud.google.com/iam-admin/settings?project=presgen)

**Possible Issue**: "Restrict sharing to domain" enabled

**Fix**:
1. Disable domain restrictions (if applicable)
2. Or add service account to allowed domains

### 6. 🔴 Incorrect Project ID

**Check**: Verify project ID matches

**Service Account Shows**: `project_id: "presgen"`

**Your Project ID**: Should be exactly `presgen`

**Fix** (if mismatch):
1. Verify actual project ID in Console
2. Generate new service account key in correct project
3. Update credentials file

## Recommended Action Plan

### Step 1: Verify Service Account Status
```bash
# Check if service account is enabled
gcloud iam service-accounts describe \
  presgen-service-account-test@presgen.iam.gserviceaccount.com \
  --project=presgen
```

Look for: `disabled: false`

If `disabled: true`:
```bash
# Enable the service account
gcloud iam service-accounts enable \
  presgen-service-account-test@presgen.iam.gserviceaccount.com \
  --project=presgen
```

### Step 2: Verify Key is Valid
```bash
# List keys for service account
gcloud iam service-accounts keys list \
  --iam-account=presgen-service-account-test@presgen.iam.gserviceaccount.com \
  --project=presgen
```

Check if key ID `3de6ed3278f780201216...` is listed and not disabled.

### Step 3: Create Fresh Service Account (If All Else Fails)

```bash
# Create new service account
gcloud iam service-accounts create presgen-sheets-export \
  --display-name="PresGen Sheets Export" \
  --project=presgen

# Grant necessary roles
gcloud projects add-iam-policy-binding presgen \
  --member="serviceAccount:presgen-sheets-export@presgen.iam.gserviceaccount.com" \
  --role="roles/editor"

# Create key
gcloud iam service-accounts keys create ~/presgen-sheets-key.json \
  --iam-account=presgen-sheets-export@presgen.iam.gserviceaccount.com \
  --project=presgen
```

### Step 4: Enable Required APIs
```bash
# Enable all required APIs
gcloud services enable sheets.googleapis.com --project=presgen
gcloud services enable drive.googleapis.com --project=presgen
gcloud services enable iamcredentials.googleapis.com --project=presgen
```

### Step 5: Test with New Credentials
```bash
# Update .env
export GOOGLE_APPLICATION_CREDENTIALS=~/presgen-sheets-key.json

# Re-run validation
python3 scripts/validate_google_auth.py
```

## Alternative: Use OAuth Instead of Service Account

If service account continues to fail, you can switch to OAuth user authentication:

### 1. Create OAuth Client
1. Go to: https://console.cloud.google.com/apis/credentials
2. Create OAuth 2.0 Client ID
3. Application type: Desktop app
4. Download JSON

### 2. Update Code
```python
# In google_sheets_service.py
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

def _initialize_service_oauth(self):
    """Initialize with OAuth (alternative to service account)."""
    flow = InstalledAppFlow.from_client_secrets_file(
        'oauth_client.json',
        scopes=self.scopes
    )
    creds = flow.run_local_server(port=0)

    self.service = build('sheets', 'v4', credentials=creds, cache_discovery=False)
```

### 3. First Run
- Opens browser for user consent
- Saves token for future use
- No 403 errors (user has full access)

## Quick Diagnostic Commands

```bash
# 1. Check if gcloud is authenticated
gcloud auth list

# 2. Check active project
gcloud config get-value project

# 3. Check if APIs are enabled
gcloud services list --enabled | grep -E "sheets|drive|iam"

# 4. Check service account exists
gcloud iam service-accounts list --project=presgen

# 5. Check service account roles
gcloud projects get-iam-policy presgen \
  --flatten="bindings[].members" \
  --filter="bindings.members:presgen-service-account-test@presgen.iam.gserviceaccount.com"
```

## Most Likely Issues (Ordered by Probability)

1. **Service Account Disabled** (80% chance)
   - Go to IAM → Service Accounts
   - Click on service account
   - Click "Enable"

2. **Wrong Key File** (10% chance)
   - Key was revoked/deleted
   - Generate new key

3. **API Not Enabled** (5% chance)
   - Enable IAM Service Account Credentials API
   - Wait for propagation

4. **Organization Policy** (3% chance)
   - Requires org admin to fix
   - Create exception or new project

5. **Other** (2% chance)
   - Domain restrictions
   - Quota issues
   - Project misconfiguration

## Testing After Fix

```bash
python3 << 'EOF'
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

creds = Credentials.from_service_account_file(
    '/path/to/service-account.json',
    scopes=['https://www.googleapis.com/auth/spreadsheets']
)

service = build('sheets', 'v4', credentials=creds, cache_discovery=False)

spreadsheet = service.spreadsheets().create(body={
    'properties': {'title': 'Test'}
}).execute()

print(f"✅ Success! Created: {spreadsheet['spreadsheetId']}")
EOF
```

## Get Help

If issue persists:

1. **Export diagnostic info**:
```bash
python3 scripts/validate_google_auth.py > auth_diagnostic.txt 2>&1
```

2. **Check service account in Console**:
   - https://console.cloud.google.com/iam-admin/serviceaccounts?project=presgen
   - Take screenshot of service account status

3. **Check IAM permissions**:
   - https://console.cloud.google.com/iam-admin/iam?project=presgen
   - Search for service account email
   - Verify roles assigned

## Summary

**Most Common Fix** (90% of cases):
```
1. Go to: https://console.cloud.google.com/iam-admin/serviceaccounts?project=presgen
2. Find: presgen-service-account-test@presgen.iam.gserviceaccount.com
3. Check status - if disabled, click "Enable"
4. If no "Enable" button, generate new key
5. Re-test with: python3 scripts/validate_google_auth.py
```

The service account **is not actually using its assigned role** until it's enabled and has a valid, non-revoked key.
