# Google Authentication Configuration for PresGen AWS Deployment

**Date:** October 28, 2025
**Status:** ✅ You have everything you need!

---

## 📋 Summary: What You Have

### ✅ Google Service Account (READY)

**File:** [presgen-service-account.json](../presgen-service-account.json)

```json
{
  "type": "service_account",
  "project_id": "presgen",
  "client_email": "presgen-service-account-test@presgen.iam.gserviceaccount.com",
  ...
}
```

**Status:** ✅ **This is what you need for AWS deployment**

### ✅ OAuth User Token (OPTIONAL for AWS)

**File:** [token.json](../token.json)

**Purpose:** User-specific access (acts on behalf of a specific Google account)

**Status:** ✅ You have it, but **NOT required for AWS deployment**

---

## 🎯 Answer to Your Question

### Do I have a Google service account?

**YES!** You have a valid Google service account:
- **File:** `presgen-service-account.json`
- **Email:** `presgen-service-account-test@presgen.iam.gserviceaccount.com`
- **Project:** `presgen`

### Do I need to make changes to work without OAuth?

**NO! PresGen is already designed to work WITHOUT OAuth.** Here's how:

---

## 🔧 How Authentication Currently Works

### Authentication Priority (Built into Code)

Your code ([src/agent/slides_google.py:44-78](../src/agent/slides_google.py)) uses this priority:

```
1. FIRST: Try Service Account (GOOGLE_APPLICATION_CREDENTIALS)
   ✅ Works without user interaction
   ✅ Perfect for server deployment
   ✅ No OAuth consent needed

2. FALLBACK: Try OAuth (OAUTH_TOKEN_PATH)
   ⚠️ Requires user consent
   ⚠️ Only used if service account fails
   ⚠️ Can be disabled
```

### Code Flow

```python
# From src/agent/slides_google.py:44-78

def _load_credentials() -> Credentials:
    # Step 1: Check if service account is forced
    force_service_account = os.getenv("FORCE_SERVICE_ACCOUNT") == "true"

    # Step 2: Try service account first
    service_account_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    if service_account_path and pathlib.Path(service_account_path).exists():
        try:
            creds = ServiceAccountCredentials.from_service_account_file(
                service_account_path,
                scopes=SCOPES
            )
            log.info("✅ Successfully authenticated with service account")
            return creds  # SUCCESS - No OAuth needed!
        except Exception as e:
            if force_service_account:
                raise RuntimeError("Service account required but failed")
            log.warning("Service account failed. Falling back to OAuth.")

    # Step 3: Fallback to OAuth (only if service account not available)
    # ... OAuth flow code ...
```

---

## ✅ What You Need to Do for AWS Deployment

### Option A: Use Service Account ONLY (Recommended)

**Configuration:**

```bash
# .env file
GOOGLE_APPLICATION_CREDENTIALS=/home/ubuntu/presgen/secrets/google-creds.json
FORCE_SERVICE_ACCOUNT=true  # ← Disable OAuth fallback

# Do NOT set OAUTH_TOKEN_PATH (not needed)
```

**Deployment Files:**

```bash
# Copy service account to secrets directory
cp presgen-service-account.json secrets/google-creds.json

# Deploy - script will upload to server
./deployment/deploy-to-lightsail.sh presgen-demo small_2_0
```

**Result:**
- ✅ No OAuth consent needed
- ✅ Works completely headless
- ✅ Service account authenticates automatically
- ✅ No user interaction required

---

### Option B: Use Service Account with OAuth Fallback (Not Recommended for AWS)

**Configuration:**

```bash
# .env file
GOOGLE_APPLICATION_CREDENTIALS=/home/ubuntu/presgen/secrets/google-creds.json
OAUTH_TOKEN_PATH=/home/ubuntu/presgen/secrets/token.json

# FORCE_SERVICE_ACCOUNT not set (allows fallback)
```

**Why NOT recommended for AWS:**
- OAuth tokens expire and require manual renewal
- Can't open browser on server for consent flow
- Adds unnecessary complexity

---

## 🔍 What Each Authentication Method Does

### Service Account Authentication

**What it is:**
- A "robot" account that acts on behalf of your application
- No user consent needed
- Perfect for server-to-server communication

**When it works:**
- Creating presentations in a shared folder
- Reading/writing to Drive files the service account has access to
- Calling Google Cloud APIs (Vertex AI, etc.)

**Limitations:**
- Cannot access user's personal Drive files directly
- Requires explicit sharing with service account email

**How to use:**
```bash
# 1. Share Google Drive folder with service account
# Share with: presgen-service-account-test@presgen.iam.gserviceaccount.com

# 2. Service account can now create/read files in that folder
# No OAuth needed!
```

---

### OAuth User Token Authentication

**What it is:**
- Acts on behalf of a specific Google user (e.g., ymeirovich@gmail.com)
- Requires user to click "Allow" during consent flow
- Token expires and needs renewal

**When it works:**
- Accessing user's personal files
- Creating presentations in user's Drive
- Acting as the user in all Google services

**Limitations:**
- Requires browser access for initial consent
- Token expires (need manual refresh)
- Not suitable for unattended server operation

---

## 📋 Required Configuration for AWS Deployment

### 1. Environment Variables

**Update `.env` file:**

```bash
# ============================================================================
# Google Cloud Authentication (AWS Deployment)
# ============================================================================

# Service Account (PRIMARY - Required)
GOOGLE_APPLICATION_CREDENTIALS=/home/ubuntu/presgen/secrets/google-creds.json

# Force Service Account (Disable OAuth Fallback)
FORCE_SERVICE_ACCOUNT=true

# OAuth Token (NOT NEEDED for AWS - leave commented out)
# OAUTH_TOKEN_PATH=/home/ubuntu/presgen/secrets/token.json

# Google Cloud Project (for quota tracking)
GOOGLE_CLOUD_PROJECT=presgen
GOOGLE_QUOTA_PROJECT=presgen
```

### 2. Prepare Secrets Directory

```bash
# In your local project directory
cd /Users/yitzchak/Documents/learn/presentation_project/sales-agent-labs

# Create secrets directory
mkdir -p secrets

# Copy service account with standard name
cp presgen-service-account.json secrets/google-creds.json

# Verify
ls -lh secrets/google-creds.json
# Should show: secrets/google-creds.json
```

### 3. Deploy (Automatic Upload)

The deployment script will automatically upload secrets:

```bash
./deployment/deploy-to-lightsail.sh presgen-demo small_2_0

# Script will:
# 1. Upload secrets/google-creds.json to server
# 2. Set GOOGLE_APPLICATION_CREDENTIALS in .env
# 3. Configure services to use service account
```

---

## 🔐 Service Account Permissions Checklist

### What Your Service Account Needs Access To

#### Google Slides API
- ✅ Create presentations
- ✅ Update slides
- ✅ Add images, text, charts

#### Google Drive API
- ✅ Create folders
- ✅ Upload files
- ✅ Share files
- ⚠️ **Important:** Share target Drive folder with service account

#### Google Forms API (for Assess module)
- ✅ Create forms
- ✅ Add questions
- ✅ Read responses

#### Google Sheets API (for exports)
- ✅ Create spreadsheets
- ✅ Write data

#### Vertex AI (for image generation)
- ✅ Generate images with Imagen
- ✅ Use Gemini API

### How to Grant Access

#### Option 1: Share Drive Folder (Recommended)

```
1. Create a folder in Google Drive: "PresGen Outputs"
2. Right-click → Share
3. Add: presgen-service-account-test@presgen.iam.gserviceaccount.com
4. Role: Editor
5. Click "Share"
```

Now all presentations will be created in this shared folder!

#### Option 2: Enable Domain-Wide Delegation (Advanced)

If you're using Google Workspace:

```
1. Go to: admin.google.com
2. Security → API Controls → Domain-wide Delegation
3. Add service account client ID: 117407303655594901900
4. Scopes:
   - https://www.googleapis.com/auth/presentations
   - https://www.googleapis.com/auth/drive.file
   - https://www.googleapis.com/auth/forms
   - https://www.googleapis.com/auth/spreadsheets
```

---

## 🧪 Testing Authentication

### Test Locally (Before Deployment)

```bash
# Set environment
export GOOGLE_APPLICATION_CREDENTIALS=/Users/yitzchak/Documents/learn/presentation_project/sales-agent-labs/secrets/google-creds.json
export FORCE_SERVICE_ACCOUNT=true

# Test service account
cd /Users/yitzchak/Documents/learn/presentation_project/sales-agent-labs
python3 << EOF
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

creds = Credentials.from_service_account_file(
    'secrets/google-creds.json',
    scopes=['https://www.googleapis.com/auth/presentations']
)

service = build('slides', 'v1', credentials=creds)
print("✅ Service account authentication SUCCESS!")
print(f"Service account: {creds.service_account_email}")
EOF
```

**Expected Output:**
```
✅ Service account authentication SUCCESS!
Service account: presgen-service-account-test@presgen.iam.gserviceaccount.com
```

### Test on AWS (After Deployment)

```bash
# SSH into server
ssh -i lightsail-key.pem ubuntu@YOUR_STATIC_IP

# Check environment
docker exec presgen-core env | grep GOOGLE

# Should show:
# GOOGLE_APPLICATION_CREDENTIALS=/secrets/google-creds.json
# FORCE_SERVICE_ACCOUNT=true

# Test authentication
docker exec presgen-core python3 << EOF
import os
from google.oauth2.service_account import Credentials

creds = Credentials.from_service_account_file(
    os.getenv('GOOGLE_APPLICATION_CREDENTIALS'),
    scopes=['https://www.googleapis.com/auth/presentations']
)

print(f"✅ Authenticated as: {creds.service_account_email}")
EOF
```

---

## 🚨 Common Issues & Solutions

### Issue 1: "Service account has no access to Drive folder"

**Error:**
```
HttpError 403: The caller does not have permission
```

**Solution:**
```bash
# Share Drive folder with service account
# Add email: presgen-service-account-test@presgen.iam.gserviceaccount.com
# Role: Editor
```

### Issue 2: "Service account file not found"

**Error:**
```
FileNotFoundError: [Errno 2] No such file or directory: '/secrets/google-creds.json'
```

**Solution:**
```bash
# Check if file exists on server
ssh -i lightsail-key.pem ubuntu@YOUR_STATIC_IP
ls -lh /home/ubuntu/presgen/secrets/google-creds.json

# If missing, upload manually
scp -i lightsail-key.pem secrets/google-creds.json \
    ubuntu@YOUR_STATIC_IP:/home/ubuntu/presgen/secrets/
```

### Issue 3: "OAuth consent required"

**Error:**
```
Please visit this URL to authorize: https://accounts.google.com/...
```

**Solution:**
```bash
# This means service account is NOT being used
# Fix: Set FORCE_SERVICE_ACCOUNT=true in .env

# Rebuild and restart
docker-compose down
docker-compose up -d --build
```

### Issue 4: "API not enabled"

**Error:**
```
HttpError 403: Google Slides API has not been used in project presgen
```

**Solution:**
```bash
# Enable APIs in Google Cloud Console
# Visit: https://console.cloud.google.com/apis/library

# Enable these APIs:
# 1. Google Slides API
# 2. Google Drive API
# 3. Google Forms API
# 4. Google Sheets API
# 5. Vertex AI API
```

---

## 📝 Updated Deployment Configuration

### Updated `.env` File (For AWS)

```bash
# ============================================================================
# Sales Agent Labs - AWS Production Configuration
# ============================================================================

# ----------------------------------------------------------------------------
# Service Ports Configuration
# ----------------------------------------------------------------------------
PRESGEN_ASSESS_PORT=8000
PRESGEN_CORE_PORT=8080
PRESGEN_UI_PORT=3000

# ----------------------------------------------------------------------------
# Service URLs (Docker Network)
# ----------------------------------------------------------------------------
PRESGEN_ASSESS_URL=http://presgen-assess:8000
PRESGEN_CORE_URL=http://presgen-core:8080

# ----------------------------------------------------------------------------
# Database Configuration
# ----------------------------------------------------------------------------
DATABASE_URL=sqlite+aiosqlite:////app/data/presgen_assess.db
REDIS_URL=redis://redis:6379/0

# ----------------------------------------------------------------------------
# OpenAI Configuration
# ----------------------------------------------------------------------------
OPENAI_API_KEY=sk-your-key-here

# ----------------------------------------------------------------------------
# Google Cloud Authentication (SERVICE ACCOUNT ONLY)
# ----------------------------------------------------------------------------
GOOGLE_APPLICATION_CREDENTIALS=/secrets/google-creds.json
FORCE_SERVICE_ACCOUNT=true

# Google Cloud Project
GOOGLE_CLOUD_PROJECT=presgen
GOOGLE_QUOTA_PROJECT=presgen

# ⚠️ OAuth NOT NEEDED for AWS deployment - leave commented out
# OAUTH_TOKEN_PATH=/secrets/token.json
# OAUTH_CLIENT_JSON=/secrets/oauth_slides_client.json

# ----------------------------------------------------------------------------
# AWS Configuration
# ----------------------------------------------------------------------------
AWS_REGION=us-east-1
S3_BUCKET=presgen-demo-files-TIMESTAMP
STORAGE_PROVIDER=s3

# ----------------------------------------------------------------------------
# PresGen Configuration
# ----------------------------------------------------------------------------
PRESGEN_USE_MOCK=false
PRESGEN_CORE_MAX_SLIDES=40
PRESGEN_AVATAR_MAX_SLIDES=40
USE_AI_IMAGES=true
GPU_ENABLED=false

# ----------------------------------------------------------------------------
# Logging Configuration
# ----------------------------------------------------------------------------
LOG_LEVEL=INFO
DEBUG=false
ENVIRONMENT=production
```

---

## ✅ Final Checklist

Before deploying to AWS, verify:

- [ ] `secrets/google-creds.json` exists locally
- [ ] `.env` file has `GOOGLE_APPLICATION_CREDENTIALS=/secrets/google-creds.json`
- [ ] `.env` file has `FORCE_SERVICE_ACCOUNT=true`
- [ ] `OAUTH_TOKEN_PATH` is NOT set (or commented out)
- [ ] Service account has access to target Drive folder
- [ ] All Google APIs are enabled in Cloud Console
- [ ] Service account email is: `presgen-service-account-test@presgen.iam.gserviceaccount.com`

If all checked, you're ready to deploy! 🚀

---

## 🎯 TL;DR - Quick Answer

**Q: Do I have a Google service account?**
**A: YES** - `presgen-service-account.json` ✅

**Q: Do I need to make changes for AWS?**
**A: NO** - Just set `FORCE_SERVICE_ACCOUNT=true` and you're good! ✅

**Q: What about OAuth?**
**A: NOT NEEDED** - Service account works without OAuth ✅

**Q: What do I need to do?**
**A:**
1. Copy `presgen-service-account.json` to `secrets/google-creds.json`
2. Set `FORCE_SERVICE_ACCOUNT=true` in `.env`
3. Deploy: `./deployment/deploy-to-lightsail.sh presgen-demo small_2_0`
4. Done! ✅

---

**Status:** ✅ Ready to Deploy
**Authentication Method:** Service Account (No OAuth required)
**Last Updated:** October 28, 2025



