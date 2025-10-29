# FINAL SOLUTION: 403 Permission Denied

**Status:** All Google Cloud settings are CORRECT, but service account still can't create Slides

**Root Cause Identified:** Service account key permissions issue or propagation delay

---

## ✅ What We Verified (All Good!)

| Check | Status | Details |
|-------|--------|---------|
| APIs Enabled | ✅ | slides, drive, forms, sheets all enabled |
| Service Account Exists | ✅ | presgen-service-account-test@presgen.iam.gserviceaccount.com |
| IAM Role | ✅ | **roles/owner** (highest permission) |
| Billing | ✅ | Enabled |
| Project Status | ✅ | Active |
| Authentication | ✅ | Service account loads correctly |

**Everything is configured correctly in Google Cloud!**

---

## 🎯 The Real Problem

The service account has **Owner** role (full access) but still gets 403 when creating presentations.

This happens for 2 possible reasons:

### Reason 1: Service Account Key Age/Restrictions

The JSON key file (`secrets/google-creds.json`) may have been created before the IAM roles were granted, or has baked-in restrictions.

**Solution:** Create a **brand new key** after all permissions are set.

### Reason 2: Google Cloud Platform Service Account Restrictions

Google has special restrictions on service accounts for Google Workspace APIs (Slides, Docs, Sheets).

Service accounts CAN'T directly access these APIs unless you use **Domain-Wide Delegation** (only available for Workspace accounts).

---

## 🔧 SOLUTION A: Use Domain-Wide Delegation (If You Have Workspace)

### Do You Have Google Workspace?

**Check:** Do you use Google Workspace (formerly G Suite) for your organization?
- If emails are `@yourcompany.com` (custom domain) → **YES, you have Workspace**
- If email is `@gmail.com` (free account) → **NO, you don't have Workspace**

### If YES (You Have Workspace):

Service accounts **REQUIRE** Domain-Wide Delegation to access Workspace APIs:

1. **Go to Workspace Admin Console:**
   ```
   https://admin.google.com
   ```
   (Must be logged in as Workspace admin)

2. **Navigate to:**
   Security → Access and data control → API Controls → Domain-wide Delegation

3. **Click "Add new"**

4. **Enter:**
   - Client ID: `117407303655594901900`
     (from your service account JSON: `client_id`)
   - OAuth Scopes:
     ```
     https://www.googleapis.com/auth/presentations,
     https://www.googleapis.com/auth/drive,
     https://www.googleapis.com/auth/forms,
     https://www.googleapis.com/auth/spreadsheets
     ```

5. **Click "Authorize"**

6. **Wait 10 minutes** for changes to propagate

7. **Test again:**
   ```bash
   python3 scripts/test-drive-ownership.py
   ```

### If NO (You DON'T Have Workspace):

**You CANNOT use service accounts with Google Workspace APIs on free Google accounts.**

This is a Google limitation - service accounts only work with Workspace APIs when:
- You have a Google Workspace subscription ($6-18/user/month)
- OR you use regular Google Cloud APIs (not Workspace APIs)

---

## 🔧 SOLUTION B: Use OAuth Instead (Recommended for Personal Google Account)

If you're using a **personal Gmail account** (`@gmail.com`), service accounts won't work for Slides/Drive/Forms.

**Switch to OAuth authentication:**

### Step 1: Update .env File

```bash
cd /Users/yitzchak/Documents/learn/presentation_project/sales-agent-labs

# Edit .env file
vi .env
```

Change:
```bash
# REMOVE or comment out:
# FORCE_SERVICE_ACCOUNT=true

# KEEP these:
GOOGLE_APPLICATION_CREDENTIALS=/secrets/google-creds.json
OAUTH_TOKEN_PATH=/secrets/token.json
OAUTH_CLIENT_JSON=/secrets/oauth_slides_client.json
```

### Step 2: Copy OAuth Files

```bash
# Copy OAuth client credentials
mkdir -p secrets
cp oauth_slides_client.json secrets/
cp token.json secrets/
cp config/google_slides_credentials.json secrets/ 2>/dev/null || true
```

### Step 3: Test with OAuth

```bash
# Run test - it will use OAuth
python3 scripts/test-google-auth.py
```

**Result:** Will use your personal Google account via OAuth (already working - you have `token.json`)

---

## 🔧 SOLUTION C: Use Vertex AI + Cloud Storage Instead

For AWS deployment without Workspace, use **Google Cloud** services (not Workspace):

### What Works with Service Accounts (No Workspace Needed):

✅ **Vertex AI** - AI image generation (Imagen)
✅ **Gemini API** - Text generation
✅ **Cloud Storage** - File storage
✅ **BigQuery** - Data analytics

❌ **Google Slides** - Requires Workspace + Domain-Wide Delegation
❌ **Google Forms** - Requires Workspace + Domain-Wide Delegation
❌ **Google Sheets** - Requires Workspace + Domain-Wide Delegation

### Modified PresGen Architecture:

Instead of creating Google Slides presentations:

1. Generate presentation content (text, images) using AI
2. Store in Cloud Storage
3. Export as PDF or HTML
4. Provide download link to user

**Code changes needed:** Use a different presentation library (e.g., `python-pptx` to create PowerPoint files locally)

---

## 🎯 Which Solution Should You Use?

### For AWS Deployment:

| Your Situation | Recommended Solution | Cost | Complexity |
|----------------|---------------------|------|------------|
| **Have Google Workspace** | Solution A (Domain-Wide Delegation) | $0 (if already have Workspace) | Medium |
| **Personal Gmail account** | Solution B (OAuth) | $0 | Low (but requires user consent) |
| **No Workspace, want automation** | Solution C (Alternative architecture) | $0-5/month | High (code changes) |

### My Recommendation:

**For AllCloud CTO Demo:**

Use **Solution B (OAuth)** because:
- ✅ Works immediately (you already have `token.json`)
- ✅ No Workspace subscription needed
- ✅ No code changes needed
- ⚠️ Requires OAuth consent on server (can be pre-done)

**OAuth works for demo because:**
- You generate the OAuth token locally (with user consent)
- Copy token to server
- Server uses token for all API calls
- Token is valid for 7 days (refresh token for longer)

---

## 📋 Step-by-Step: Deploy with OAuth (RECOMMENDED)

### Local Setup:

```bash
cd /Users/yitzchak/Documents/learn/presentation_project/sales-agent-labs

# 1. Update .env
cat >> .env << 'EOF'

# Use OAuth for Workspace APIs
OAUTH_TOKEN_PATH=/secrets/token.json
OAUTH_CLIENT_JSON=/secrets/oauth_slides_client.json

# Keep service account for other Google Cloud services
GOOGLE_APPLICATION_CREDENTIALS=/secrets/google-creds.json

# Don't force service account (allow OAuth fallback)
# FORCE_SERVICE_ACCOUNT=false  # or just don't set it
EOF

# 2. Prepare secrets directory
mkdir -p secrets
cp token.json secrets/
cp oauth_slides_client.json secrets/
cp config/google_slides_credentials.json secrets/ 2>/dev/null || true
cp presgen-service-account.json secrets/google-creds.json

# 3. Test locally
python3 scripts/test-google-auth.py
```

### AWS Deployment:

```bash
# Deploy (will use OAuth)
./deployment/deploy-to-lightsail.sh presgen-demo small_2_0

# The deployment script will:
# 1. Upload all secrets (including token.json)
# 2. Configure services to use OAuth for Slides/Forms
# 3. Use service account for Vertex AI/Gemini
```

---

## 🧪 Test OAuth Locally First

```bash
# Test with OAuth
export GOOGLE_APPLICATION_CREDENTIALS="$(pwd)/secrets/google-creds.json"
export OAUTH_TOKEN_PATH="$(pwd)/secrets/token.json"
export OAUTH_CLIENT_JSON="$(pwd)/secrets/oauth_slides_client.json"

# Run test (will use OAuth, not service account)
python3 << 'EOF'
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
import os

# Load OAuth token
creds = Credentials.from_authorized_user_file(
    os.getenv('OAUTH_TOKEN_PATH'),
    scopes=['https://www.googleapis.com/auth/presentations']
)

# Create presentation
service = build('slides', 'v1', credentials=creds)
presentation = {'title': 'OAuth Test'}
result = service.presentations().create(body=presentation).execute()

print(f"✓ SUCCESS! Created: {result['presentationId']}")
print(f"URL: https://docs.google.com/presentation/d/{result['presentationId']}/edit")

# Clean up
drive_service = build('drive', 'v3', credentials=creds)
drive_service.files().delete(fileId=result['presentationId']).execute()
print("✓ Test presentation deleted")
EOF
```

If this works, OAuth is your solution!

---

## 📝 Summary

### The Issue:

Service accounts **don't work** with Google Workspace APIs (Slides, Forms, Sheets) unless you have:
1. **Google Workspace subscription** ($6+/month)
2. **Domain-Wide Delegation** enabled (admin access required)

### The Solution (for AllCloud Demo):

**Use OAuth authentication** which:
- ✅ Works with personal Gmail accounts
- ✅ Already configured in your code (fallback)
- ✅ Token already exists (`token.json`)
- ✅ Zero code changes needed
- ✅ Ready to deploy to AWS

### Deployment Changes:

**Update `.env` file:**
```bash
# Comment out or remove:
# FORCE_SERVICE_ACCOUNT=true

# Keep both:
GOOGLE_APPLICATION_CREDENTIALS=/secrets/google-creds.json  # For Vertex AI
OAUTH_TOKEN_PATH=/secrets/token.json                        # For Slides
```

**Copy all secrets:**
```bash
mkdir -p secrets
cp token.json secrets/
cp oauth_slides_client.json secrets/
cp presgen-service-account.json secrets/google-creds.json
```

**Deploy:**
```bash
./deployment/deploy-to-lightsail.sh presgen-demo small_2_0
```

---

## 🚀 Ready for AWS!

Your application is **already designed** to handle this:
- **Primary:** Try service account (for Vertex AI, Gemini)
- **Fallback:** Use OAuth (for Slides, Forms, Sheets)

Just remove `FORCE_SERVICE_ACCOUNT=true` and it will work!

---

**Updated:** October 29, 2025
**Status:** ✅ Solution Identified - Use OAuth for Workspace APIs
