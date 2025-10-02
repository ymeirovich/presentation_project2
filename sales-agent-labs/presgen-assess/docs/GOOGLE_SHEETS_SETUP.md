# Google Sheets Service Account Setup Guide

This guide explains how to set up Google service account authentication for the PresGen-Assess Google Sheets export feature.

## Current Status

### ✅ Implemented Features
- Service account authentication in `GoogleSheetsService`
- Credentials loading from environment variable
- 4-tab export format implementation
- Comprehensive error handling and logging

### ⚠️ Setup Required
The service account authentication is **fully implemented** but requires Google Cloud Console configuration.

## Prerequisites

1. **Google Cloud Project**: Access to a Google Cloud project
2. **Service Account File**: JSON credentials file (already exists at `presgen-service-account2.json`)
3. **Environment Configuration**: `.env` file with credentials path (already configured)

## Setup Steps

### Step 1: Enable Google APIs

The service account needs the following APIs enabled in the Google Cloud project:

1. **Google Sheets API**
   - Go to: https://console.cloud.google.com/apis/library/sheets.googleapis.com
   - Select project: `presgen`
   - Click "Enable"

2. **Google Drive API**
   - Go to: https://console.cloud.google.com/apis/library/drive.googleapis.com
   - Select project: `presgen`
   - Click "Enable"

### Step 2: Verify Service Account Permissions

1. Go to: https://console.cloud.google.com/iam-admin/serviceaccounts
2. Select project: `presgen`
3. Find service account: `presgen-service-account-test@presgen.iam.gserviceaccount.com`
4. Verify it has one of these roles:
   - **Editor** (recommended for development)
   - **Owner** (full access)
   - **Custom role** with these permissions:
     - `sheets.spreadsheets.create`
     - `sheets.spreadsheets.update`
     - `drive.files.create`
     - `drive.files.delete`

### Step 3: Verify Configuration

Run the validation script:

```bash
python3 scripts/validate_google_auth.py
```

Expected output:
```
✅ PASS: Service Account File
✅ PASS: Required Libraries
✅ PASS: API Access
✅ PASS: PresGen Configuration
```

## Configuration Details

### Environment Variables

The following environment variables are configured in `.env`:

```bash
GOOGLE_APPLICATION_CREDENTIALS=/Users/yitzchak/Documents/learn/presentation_project/sales-agent-labs/presgen-service-account2.json
GOOGLE_CLOUD_PROJECT=presgen
```

### Service Account Details

- **Email**: `presgen-service-account-test@presgen.iam.gserviceaccount.com`
- **Project**: `presgen`
- **Type**: Service Account
- **Scopes**:
  - `https://www.googleapis.com/auth/spreadsheets` (create/edit spreadsheets)
  - `https://www.googleapis.com/auth/drive.file` (manage created files)

### Code Implementation

The service account authentication is implemented in:

**File**: `src/services/google_sheets_service.py`

```python
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

def _initialize_service(self):
    """Initialize Google Sheets API service with service account."""
    # Load service account credentials
    credentials = Credentials.from_service_account_file(
        self.credentials_path,
        scopes=self.scopes
    )

    # Build Sheets API service
    self.service = build('sheets', 'v4', credentials=credentials, cache_discovery=False)
```

## Testing

### Manual API Test

```python
import os
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

# Load credentials
creds = Credentials.from_service_account_file(
    os.environ['GOOGLE_APPLICATION_CREDENTIALS'],
    scopes=['https://www.googleapis.com/auth/spreadsheets']
)

# Build service
service = build('sheets', 'v4', credentials=creds, cache_discovery=False)

# Create test spreadsheet
spreadsheet = service.spreadsheets().create(body={
    'properties': {'title': 'Test Spreadsheet'}
}).execute()

print(f"Created: https://docs.google.com/spreadsheets/d/{spreadsheet['spreadsheetId']}")
```

### End-to-End Test

1. Complete an assessment workflow in PresGen-Assess
2. Navigate to Gap Analysis Dashboard
3. Click "Export to Sheets" button
4. Verify Google Sheets opens with 4 tabs:
   - Tab 1: Answers
   - Tab 2: Gap Analysis
   - Tab 3: Content Outlines
   - Tab 4: Recommended Courses

## Troubleshooting

### Issue: "Permission denied (403)"

**Cause**: Google Sheets API or Drive API not enabled

**Solution**:
1. Enable APIs as described in Step 1
2. Wait 1-2 minutes for propagation
3. Retry the operation

### Issue: "Service account file not found"

**Cause**: `GOOGLE_APPLICATION_CREDENTIALS` path incorrect

**Solution**:
1. Verify file exists: `ls -la $GOOGLE_APPLICATION_CREDENTIALS`
2. Update `.env` with correct absolute path
3. Restart application

### Issue: "Invalid credentials"

**Cause**: Service account JSON file corrupted or invalid

**Solution**:
1. Download fresh credentials from Google Cloud Console
2. Replace existing file
3. Verify JSON structure with validation script

### Issue: "Module not found: pydantic_settings"

**Cause**: Missing Python dependency

**Solution**:
```bash
pip install pydantic-settings
```

## Alternative: Mock Mode

If you cannot enable Google APIs, the system will operate in **mock mode**:

- Export returns mock response
- No actual Google Sheets created
- Useful for development/testing without API access

Mock response includes:
- Mock spreadsheet URL
- Setup instructions
- All data in JSON format

## Security Considerations

1. **Service Account Security**:
   - Never commit service account JSON to git
   - Use `.gitignore` to exclude credentials
   - Rotate keys regularly

2. **File Permissions**:
   - Service account file should have restricted permissions
   - Recommended: `chmod 600 presgen-service-account2.json`

3. **Production Deployment**:
   - Use secret management (e.g., Google Secret Manager)
   - Store credentials as environment variables
   - Use workload identity for GKE/Cloud Run

## API Quotas

Google Sheets API quotas (default):
- **Read requests**: 500 per 100 seconds per user
- **Write requests**: 500 per 100 seconds per user

For higher quotas, request increase in Google Cloud Console.

## Support

For issues with:
- **Google Cloud setup**: Check Google Cloud documentation
- **Service account**: Use validation script for diagnostics
- **API errors**: Check logs in `presgen-assess/src/logs/`

## References

- [Google Sheets API Documentation](https://developers.google.com/sheets/api)
- [Service Account Authentication](https://cloud.google.com/iam/docs/service-accounts)
- [Google Drive API](https://developers.google.com/drive/api)
- [Google Cloud Console](https://console.cloud.google.com)
