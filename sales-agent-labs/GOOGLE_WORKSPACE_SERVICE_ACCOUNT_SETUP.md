# Google Workspace Service Account Setup Guide

**Domain:** presgen.net
**Service Account:** presgen-service-account-test@presgen.iam.gserviceaccount.com
**Date:** October 30, 2025

---

## 📋 Overview

This guide shows how to configure Google Workspace to work with the PresGen service account for:
- Google Drive file access
- Google Slides creation and editing
- Google Forms integration (future)

---

## Part 1: Google Cloud Configuration (Already Done ✅)

Based on your previous work, you should already have:
- ✅ Service account created: `presgen-service-account-test@presgen.iam.gserviceaccount.com`
- ✅ Service account JSON key file downloaded
- ✅ APIs enabled: Google Drive API, Google Slides API, Google Forms API
- ✅ Google Drive folder shared with service account

---

## Part 2: Google Workspace Admin Configuration

### Step 1: Enable Domain-Wide Delegation

**Why:** Allows the service account to impersonate Workspace users and access their resources.

**Steps:**

1. **Go to Google Cloud Console**
   - URL: https://console.cloud.google.com
   - Select your project

2. **Navigate to Service Accounts**
   - Menu → IAM & Admin → Service Accounts
   - Find: `presgen-service-account-test@presgen.iam.gserviceaccount.com`

3. **Enable Domain-Wide Delegation**
   - Click on the service account
   - Go to "Details" tab
   - Scroll to "Domain-wide delegation"
   - Click "Enable Google Workspace Domain-wide Delegation"
   - **Copy the Client ID** (you'll need this for Step 2)
   - Example: `123456789012345678901`

4. **Save the Client ID**
   ```bash
   # Your service account Client ID
   CLIENT_ID=123456789012345678901
   ```

### Step 2: Configure Domain-Wide Delegation in Google Workspace

**Why:** Authorizes which Google Workspace APIs the service account can access.

**Steps:**

1. **Go to Google Workspace Admin Console**
   - URL: https://admin.google.com
   - Login with your presgen.net admin account

2. **Navigate to API Controls**
   - Menu → Security → Access and data control → API Controls
   - Or direct URL: https://admin.google.com/ac/owl/domainwidedelegation

3. **Manage Domain-Wide Delegation**
   - Click "MANAGE DOMAIN WIDE DELEGATION"
   - Click "Add new"

4. **Add Client ID and Scopes**
   - **Client ID:** [Paste the Client ID from Step 1]
   - **OAuth Scopes:** (paste ALL of these, comma-separated)

   ```
   https://www.googleapis.com/auth/drive,https://www.googleapis.com/auth/drive.file,https://www.googleapis.com/auth/presentations,https://www.googleapis.com/auth/presentations.readonly,https://www.googleapis.com/auth/forms,https://www.googleapis.com/auth/forms.body,https://www.googleapis.com/auth/spreadsheets
   ```

   **Or enter each scope on a separate line:**
   ```
   https://www.googleapis.com/auth/drive
   https://www.googleapis.com/auth/drive.file
   https://www.googleapis.com/auth/presentations
   https://www.googleapis.com/auth/presentations.readonly
   https://www.googleapis.com/auth/forms
   https://www.googleapis.com/auth/forms.body
   https://www.googleapis.com/auth/spreadsheets
   ```

5. **Click "Authorize"**

### Step 3: Create or Identify Admin User

**Why:** Service account needs to impersonate a Workspace user to access resources.

**Steps:**

1. **Go to Google Workspace Admin Console**
   - Menu → Directory → Users

2. **Create or Select Admin User**
   - Option A: Use existing admin (e.g., `admin@presgen.net`)
   - Option B: Create dedicated service user (e.g., `presgen-service@presgen.net`)

3. **Recommended: Create Dedicated Service User**
   ```
   Email: presgen-service@presgen.net
   First name: PresGen
   Last name: Service
   Password: [Generate secure password]
   ```

4. **Assign Super Admin Role** (if needed for full access)
   - Click on the user
   - Admin roles and privileges
   - Assign "Super Admin" or custom role with:
     - Drive and Docs privileges
     - Google Forms privileges

5. **Save the User Email**
   ```bash
   # User email for service account impersonation
   IMPERSONATE_USER=presgen-service@presgen.net
   ```

---

## Part 3: Google Drive Folder Configuration

### Verify Folder Sharing

1. **Check Folder Permissions**
   - Open Google Drive: https://drive.google.com
   - Navigate to "presgen-artifacts" folder
   - Right-click → Share → Manage access

2. **Verify Service Account Has Access**
   ```
   presgen-service-account-test@presgen.iam.gserviceaccount.com
   Role: Editor (or Owner)
   ```

3. **Get Folder ID**
   - Open the folder in Drive
   - Copy the ID from URL:
   ```
   https://drive.google.com/drive/folders/1a2b3c4d5e6f7g8h9i0j
                                           ^^^^^^^^^^^^^^^^^^^^^^^^
                                           This is the Folder ID
   ```

4. **Save Folder ID**
   ```bash
   DRIVE_FOLDER_ID=1a2b3c4d5e6f7g8h9i0j
   ```

### Alternative: Share with Entire Domain (Optional)

If you want all presgen.net users to access generated files:

1. **Share Folder with Domain**
   - Right-click folder → Share
   - Add `presgen.net` (not an email, just the domain)
   - Set role: Viewer or Editor
   - Click "Share"

---

## Part 4: Update PresGen Platform Configuration

### Step 1: Update Service Account Credentials File

You should already have the service account JSON key file. If not:

1. **Download Service Account Key**
   - Google Cloud Console → IAM & Admin → Service Accounts
   - Click on service account
   - Keys tab → Add Key → Create new key
   - Choose JSON → Create
   - Save as `google-creds.json`

2. **Verify Key File Structure**
   ```json
   {
     "type": "service_account",
     "project_id": "presgen-xxxx",
     "private_key_id": "...",
     "private_key": "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n",
     "client_email": "presgen-service-account-test@presgen.iam.gserviceaccount.com",
     "client_id": "123456789012345678901",
     "auth_uri": "https://accounts.google.com/o/oauth2/auth",
     "token_uri": "https://oauth2.googleapis.com/token",
     "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
     "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/..."
   }
   ```

3. **Place Credentials File**
   ```bash
   # For local testing
   cp google-creds.json /path/to/sales-agent-labs/secrets/google-creds.json

   # For AWS deployment
   # Upload to: /secrets/google-creds.json on the server
   ```

### Step 2: Update Environment Variables

**For Local Docker (docker-compose.yml):**

Already configured in your docker-compose.yml:
```yaml
environment:
  - GOOGLE_APPLICATION_CREDENTIALS=/secrets/google-creds.json
  - OAUTH_TOKEN_PATH=/secrets/google-oauth-token.json

volumes:
  - ./secrets:/secrets:ro
```

**For AWS Deployment (.env.production):**

Create or update `.env.production`:
```bash
# Google Service Account
GOOGLE_APPLICATION_CREDENTIALS=/secrets/google-creds.json
GOOGLE_SERVICE_ACCOUNT_IMPERSONATE_USER=presgen-service@presgen.net
GOOGLE_DRIVE_FOLDER_ID=1a2b3c4d5e6f7g8h9i0j

# Optional: Workspace Domain
GOOGLE_WORKSPACE_DOMAIN=presgen.net
GOOGLE_WORKSPACE_CUSTOMER_ID=C01xxxxxx

# Storage for generated files
STORAGE_PROVIDER=google_drive  # or 's3' for AWS
GOOGLE_DRIVE_ROOT_FOLDER=presgen-artifacts
```

### Step 3: Update Application Code (If Needed)

Check if the application code uses the impersonation user. Look for files that handle Google API authentication:

**File to check:** `presgen-assess/src/common/google_slides_import_v2.py` or similar

**Expected pattern:**
```python
from google.oauth2 import service_account

# Load service account credentials
credentials = service_account.Credentials.from_service_account_file(
    'path/to/google-creds.json',
    scopes=[
        'https://www.googleapis.com/auth/drive',
        'https://www.googleapis.com/auth/presentations'
    ]
)

# For domain-wide delegation (if needed)
credentials = credentials.with_subject('presgen-service@presgen.net')

# Build service
from googleapiclient.discovery import build
drive_service = build('drive', 'v3', credentials=credentials)
slides_service = build('slides', 'v1', credentials=credentials)
```

---

## Part 5: Testing the Integration

### Test 1: Service Account Can Access Drive

```bash
# Install Google client library (if not in requirements)
pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client

# Create test script: test_service_account.py
```

**test_service_account.py:**
```python
#!/usr/bin/env python3
"""Test Google Workspace Service Account Integration"""

from google.oauth2 import service_account
from googleapiclient.discovery import build
import os

# Configuration
CREDENTIALS_FILE = './secrets/google-creds.json'
IMPERSONATE_USER = 'presgen-service@presgen.net'  # UPDATE THIS
FOLDER_ID = '1a2b3c4d5e6f7g8h9i0j'  # UPDATE THIS

SCOPES = [
    'https://www.googleapis.com/auth/drive',
    'https://www.googleapis.com/auth/presentations'
]

def test_service_account():
    """Test service account access to Google Drive"""

    print("🔐 Loading service account credentials...")
    credentials = service_account.Credentials.from_service_account_file(
        CREDENTIALS_FILE,
        scopes=SCOPES
    )

    print(f"👤 Impersonating user: {IMPERSONATE_USER}")
    credentials = credentials.with_subject(IMPERSONATE_USER)

    print("🔨 Building Drive service...")
    drive_service = build('drive', 'v3', credentials=credentials)

    print(f"📁 Testing access to folder: {FOLDER_ID}")
    try:
        # List files in the shared folder
        results = drive_service.files().list(
            q=f"'{FOLDER_ID}' in parents",
            pageSize=10,
            fields="files(id, name, mimeType)"
        ).execute()

        files = results.get('files', [])

        print(f"\n✅ SUCCESS! Found {len(files)} files in folder:")
        for file in files:
            print(f"  - {file['name']} ({file['mimeType']})")

        # Try to create a test file
        print("\n📝 Creating test file...")
        file_metadata = {
            'name': 'PresGen Test File',
            'mimeType': 'application/vnd.google-apps.presentation',
            'parents': [FOLDER_ID]
        }

        test_file = drive_service.files().create(
            body=file_metadata,
            fields='id, name, webViewLink'
        ).execute()

        print(f"✅ Created test presentation!")
        print(f"  ID: {test_file['id']}")
        print(f"  Name: {test_file['name']}")
        print(f"  Link: {test_file['webViewLink']}")

        return True

    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        print("\nTroubleshooting:")
        print("1. Check domain-wide delegation is enabled")
        print("2. Verify OAuth scopes in Admin Console")
        print("3. Ensure impersonation user exists")
        print("4. Check folder is shared with service account")
        return False

if __name__ == '__main__':
    test_service_account()
```

**Run the test:**
```bash
# From project root
cd /Users/yitzchak/Documents/learn/presentation_project/sales-agent-labs
python3 test_service_account.py
```

### Test 2: Test Through Docker Container

```bash
# Copy test script to presgen-assess
docker cp test_service_account.py presgen-assess:/app/

# Run test inside container
docker exec -it presgen-assess python3 /app/test_service_account.py
```

### Test 3: Test Through API Endpoint

Once the service account is configured, test through the PresGen API:

```bash
# Test presentation generation endpoint
curl -u demo:demo -X POST http://localhost/api/v1/presentations/generate \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Test Presentation",
    "slides": [
      {"title": "Slide 1", "content": "Test content"}
    ]
  }'
```

---

## Part 6: Troubleshooting

### Issue 1: "Access Not Configured" Error

**Error:**
```
googleapiclient.errors.HttpError: 403 Access Not Configured
```

**Solution:**
1. Verify APIs are enabled in Google Cloud Console
2. Enable: Drive API, Slides API, Forms API
3. Wait 1-2 minutes for changes to propagate

### Issue 2: "Requested entity was not found"

**Error:**
```
googleapiclient.errors.HttpError: 404 Requested entity was not found
```

**Solution:**
1. Check folder ID is correct
2. Verify folder is shared with service account email
3. Ensure folder is not in trash

### Issue 3: "Forbidden" or "Insufficient Permission"

**Error:**
```
googleapiclient.errors.HttpError: 403 Forbidden
```

**Solutions:**
1. **Check Domain-Wide Delegation:**
   - Admin Console → Security → API Controls
   - Verify Client ID is authorized
   - Verify all scopes are added

2. **Check Service Account Permissions:**
   - Folder must be shared with service account email
   - Service account needs "Editor" or "Owner" role

3. **Check Impersonation User:**
   - User must exist in Workspace
   - User must have Drive access enabled
   - User must be in same domain (presgen.net)

### Issue 4: "Invalid Impersonation"

**Error:**
```
google.auth.exceptions.RefreshError: Invalid impersonation
```

**Solutions:**
1. Verify domain-wide delegation is enabled
2. Check OAuth scopes match what's in Admin Console
3. Ensure impersonation user email is correct
4. Wait 10-15 minutes after configuring domain-wide delegation

### Issue 5: Certificate/SSL Errors

**Error:**
```
ssl.SSLCertVerificationError
```

**Solution:**
```bash
# Update certificates
pip install --upgrade certifi google-auth

# Or set environment variable (not recommended for production)
export PYTHONHTTPSVERIFY=0
```

---

## Part 7: Security Best Practices

### 1. Service Account Key Security

```bash
# Never commit to git
echo "secrets/google-creds.json" >> .gitignore

# Restrict file permissions
chmod 600 secrets/google-creds.json

# For AWS, use AWS Secrets Manager instead of file
aws secretsmanager create-secret \
  --name presgen/google-service-account \
  --secret-string file://secrets/google-creds.json
```

### 2. Rotate Keys Regularly

- Rotate service account keys every 90 days
- Delete old keys after rotation
- Google Cloud Console → Service Account → Keys

### 3. Minimal Scopes

Only request scopes your app actually needs:
```python
# Minimal scopes for PresGen
SCOPES = [
    'https://www.googleapis.com/auth/drive.file',  # Create files only
    'https://www.googleapis.com/auth/presentations'  # Slides access
]
```

### 4. Monitor Usage

- Enable audit logs in Google Cloud Console
- Monitor API usage in Cloud Console → APIs & Services → Dashboard
- Set up billing alerts

---

## Part 8: Configuration Summary

### Checklist

- [ ] Service account created in Google Cloud
- [ ] Domain-wide delegation enabled for service account
- [ ] Client ID authorized in Workspace Admin Console
- [ ] OAuth scopes configured (Drive, Slides, Forms)
- [ ] Impersonation user created (presgen-service@presgen.net)
- [ ] Drive folder shared with service account
- [ ] google-creds.json file downloaded and secured
- [ ] Environment variables configured
- [ ] Test script runs successfully
- [ ] API endpoints working with service account

### Key Information to Save

```bash
# Service Account
SERVICE_ACCOUNT_EMAIL=presgen-service-account-test@presgen.iam.gserviceaccount.com
SERVICE_ACCOUNT_CLIENT_ID=123456789012345678901

# Workspace
WORKSPACE_DOMAIN=presgen.net
IMPERSONATE_USER=presgen-service@presgen.net

# Drive
DRIVE_FOLDER_ID=1a2b3c4d5e6f7g8h9i0j
DRIVE_FOLDER_NAME=presgen-artifacts

# Credentials Files
CREDENTIALS_FILE=/secrets/google-creds.json
```

---

## Part 9: Production Deployment Notes

### For AWS Lightsail:

1. **Upload Credentials Securely**
   ```bash
   # SSH to AWS instance
   ssh -i your-key.pem ubuntu@your-instance-ip

   # Create secrets directory
   sudo mkdir -p /var/www/presgen/secrets
   sudo chmod 700 /var/www/presgen/secrets

   # From local machine, upload key
   scp -i your-key.pem google-creds.json ubuntu@your-instance-ip:/tmp/

   # Back on server, move to secure location
   sudo mv /tmp/google-creds.json /var/www/presgen/secrets/
   sudo chmod 600 /var/www/presgen/secrets/google-creds.json
   sudo chown www-data:www-data /var/www/presgen/secrets/google-creds.json
   ```

2. **Update docker-compose.yml**
   ```yaml
   volumes:
     - /var/www/presgen/secrets:/secrets:ro
   ```

3. **Set Environment Variables**
   ```bash
   # In .env.production
   GOOGLE_APPLICATION_CREDENTIALS=/secrets/google-creds.json
   GOOGLE_SERVICE_ACCOUNT_IMPERSONATE_USER=presgen-service@presgen.net
   GOOGLE_DRIVE_FOLDER_ID=1a2b3c4d5e6f7g8h9i0j
   ```

---

## Support Resources

- **Google Workspace Admin Help:** https://support.google.com/a
- **Service Account Documentation:** https://cloud.google.com/iam/docs/service-accounts
- **Domain-Wide Delegation:** https://developers.google.com/identity/protocols/oauth2/service-account#delegatingauthority
- **Drive API Guide:** https://developers.google.com/drive/api/guides/about-sdk
- **Slides API Guide:** https://developers.google.com/slides/api/guides/concepts

---

**Last Updated:** October 30, 2025
**Status:** Ready for configuration
**Next Step:** Configure domain-wide delegation in Google Workspace Admin Console
