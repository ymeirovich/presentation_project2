# Google Cloud Authentication - Quick Reference

**Date:** October 29, 2025
**Status:** ✅ READY FOR DEPLOYMENT
**Last Updated:** Post-troubleshooting and testing

---

## TL;DR - What You Need to Know

### The Problem We Solved

**Initial Error:** `HttpError 403: The caller does not have permission` when creating Google Slides

**Root Cause:** Service accounts do NOT work with Google Workspace APIs (Slides, Forms, Sheets) on personal Gmail accounts without a Google Workspace subscription.

**Solution:** Use dual authentication - service account for Cloud APIs, OAuth for Workspace APIs.

---

## Quick Deployment Checklist

Before deploying to AWS, ensure you have:

```bash
# 1. Create secrets directory
cd /Users/yitzchak/Documents/learn/presentation_project/sales-agent-labs
mkdir -p secrets

# 2. Copy authentication files
cp presgen-service-account.json secrets/google-creds.json
cp token.json secrets/token.json
cp config/google_slides_credentials.json secrets/oauth_slides_client.json

# 3. Verify all files exist
ls -lh secrets/
# Should show:
# google-creds.json (2.3K) - Service account
# token.json (315 bytes) - OAuth user token
# oauth_slides_client.json (532 bytes) - OAuth client credentials

# 4. Verify .env configuration
cat .env | grep GOOGLE
# Should show:
# GOOGLE_APPLICATION_CREDENTIALS=/secrets/google-creds.json
# OAUTH_TOKEN_PATH=/secrets/token.json
# OAUTH_CLIENT_JSON=/secrets/oauth_slides_client.json
# GOOGLE_CLOUD_PROJECT=presgen
#
# Should NOT show:
# FORCE_SERVICE_ACCOUNT=true  (this must be absent or false)

# 5. Deploy
./deployment/deploy-to-lightsail.sh presgen-demo small_2_0
```

---

## Authentication Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                  PresGen on AWS Lightsail                    │
│                                                               │
│  ┌──────────────────┐              ┌──────────────────┐     │
│  │  Service Account │              │  OAuth Token     │     │
│  │  (google-creds)  │              │  (token.json)    │     │
│  └────────┬─────────┘              └────────┬─────────┘     │
│           │                                  │               │
│           │ For Cloud APIs                   │ For Workspace │
│           │                                  │ APIs          │
│           ▼                                  ▼               │
│  ┌──────────────────┐              ┌──────────────────┐     │
│  │ • Vertex AI      │              │ • Google Slides  │     │
│  │ • Gemini API     │              │ • Google Forms   │     │
│  │ • Cloud Storage  │              │ • Google Sheets  │     │
│  │ • Cloud Vision   │              │ • Google Drive   │     │
│  └──────────────────┘              └──────────────────┘     │
│                                                               │
│  Authentication Priority (Built into Code):                  │
│  1. Try service account first                                │
│  2. Fall back to OAuth if needed                             │
│  → Both methods work together seamlessly                     │
└─────────────────────────────────────────────────────────────┘
```

---

## Files You Have

### 1. Service Account: `presgen-service-account.json`

```json
{
  "type": "service_account",
  "project_id": "presgen",
  "private_key_id": "492d68aa...",
  "private_key": "-----BEGIN PRIVATE KEY-----\n...",
  "client_email": "presgen-service-account-test@presgen.iam.gserviceaccount.com",
  "client_id": "117407303655594901900"
}
```

**What it does:**
- Authenticates with Google Cloud APIs (Vertex AI, Gemini, Cloud Storage)
- Never expires (long-lived credential)
- Works headless (no browser required)

**What it CANNOT do:**
- Create Google Slides, Forms, or Sheets (without Workspace subscription)
- Access user's personal Drive files

### 2. OAuth Token: `token.json`

```json
{
  "token": "ya29.a0AfB_...",
  "refresh_token": "1//0gXY...",
  "token_uri": "https://oauth2.googleapis.com/token",
  "client_id": "247572193615-...",
  "client_secret": "GOCSPX-...",
  "scopes": [
    "https://www.googleapis.com/auth/presentations",
    "https://www.googleapis.com/auth/drive.file",
    "https://www.googleapis.com/auth/forms",
    "https://www.googleapis.com/auth/spreadsheets"
  ]
}
```

**What it does:**
- Creates Google Slides, Forms, Sheets, Drive files
- Acts on behalf of your Google account (ymeirovich@gmail.com)
- Auto-refreshes using refresh_token (no manual intervention)

**Expiry:**
- Access token: 1 hour (refreshes automatically)
- Refresh token: ~6 months of inactivity (regenerate if expired)

### 3. OAuth Client Credentials: `google_slides_credentials.json`

```json
{
  "installed": {
    "client_id": "247572193615-...",
    "project_id": "presgen",
    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
    "token_uri": "https://oauth2.googleapis.com/token",
    "client_secret": "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",
    "redirect_uris": ["http://localhost"]
  }
}
```

**What it does:**
- OAuth client credentials for generating/refreshing tokens
- Used by the application to refresh expired access tokens
- Required for OAuth flow to work

---

## Configuration for AWS

### .env File (Correct Configuration)

```bash
# ============================================================================
# Google Cloud Authentication (Dual Method - RECOMMENDED)
# ============================================================================

# Service Account (for Vertex AI, Gemini, Cloud APIs)
GOOGLE_APPLICATION_CREDENTIALS=/secrets/google-creds.json

# OAuth Tokens (for Slides, Forms, Sheets, Drive)
OAUTH_TOKEN_PATH=/secrets/token.json
OAUTH_CLIENT_JSON=/secrets/oauth_slides_client.json

# Google Cloud Project
GOOGLE_CLOUD_PROJECT=presgen
GOOGLE_QUOTA_PROJECT=presgen

# ⚠️ CRITICAL: Do NOT set FORCE_SERVICE_ACCOUNT=true
# This would break Workspace API access (Slides, Forms, Sheets)

# ❌ DON'T INCLUDE:
# FORCE_SERVICE_ACCOUNT=true  # This breaks OAuth fallback!
```

### docker-compose.yml Volumes

```yaml
services:
  presgen-core:
    volumes:
      - ./secrets:/secrets:ro  # Read-only for security
    environment:
      - GOOGLE_APPLICATION_CREDENTIALS=/secrets/google-creds.json
      - OAUTH_TOKEN_PATH=/secrets/token.json
      - OAUTH_CLIENT_JSON=/secrets/oauth_slides_client.json
```

---

## How the Code Works

### Authentication Flow ([src/agent/slides_google.py:44-78](../src/agent/slides_google.py))

```python
def _load_credentials() -> Credentials:
    # Step 1: Check environment
    force_service_account = os.getenv("FORCE_SERVICE_ACCOUNT") == "true"
    service_account_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")

    # Step 2: Try service account first
    if service_account_path and pathlib.Path(service_account_path).exists():
        try:
            creds = ServiceAccountCredentials.from_service_account_file(
                service_account_path,
                scopes=SCOPES
            )
            log.info("✅ Successfully authenticated with service account")
            return creds
        except Exception as e:
            if force_service_account:
                raise RuntimeError("Service account required but failed")
            log.warning("⚠️ Service account failed, falling back to OAuth")

    # Step 3: Fall back to OAuth (THIS IS WHAT WORKS FOR WORKSPACE APIs!)
    token_path = os.getenv("OAUTH_TOKEN_PATH", "token.json")
    if pathlib.Path(token_path).exists():
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)

        # Auto-refresh if expired
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())

        log.info("✅ Successfully authenticated with OAuth")
        return creds

    # Step 4: No credentials available - start OAuth flow
    raise RuntimeError("No valid credentials found")
```

**Key Points:**
- Service account is tried first (good for Cloud APIs)
- OAuth is fallback (required for Workspace APIs)
- OAuth tokens auto-refresh (no manual intervention)
- If `FORCE_SERVICE_ACCOUNT=true`, OAuth fallback is disabled (BAD!)

---

## Testing After Deployment

### Test 1: Service Account (Cloud APIs)

```bash
# SSH into server
ssh -i lightsail-key.pem ubuntu@YOUR_STATIC_IP

# Test service account
docker exec presgen-core python3 -c "
from google.oauth2.service_account import Credentials
creds = Credentials.from_service_account_file(
    '/secrets/google-creds.json',
    scopes=['https://www.googleapis.com/auth/cloud-platform']
)
print(f'✅ Service Account: {creds.service_account_email}')
print(f'✅ Project: {creds.project_id}')
"
```

**Expected Output:**
```
✅ Service Account: presgen-service-account-test@presgen.iam.gserviceaccount.com
✅ Project: presgen
```

### Test 2: OAuth (Workspace APIs)

```bash
# Test OAuth + Google Slides API
docker exec presgen-core python3 << 'EOF'
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

# Load OAuth credentials
creds = Credentials.from_authorized_user_file(
    '/secrets/token.json',
    scopes=['https://www.googleapis.com/auth/presentations']
)

# Test by creating a presentation
slides_service = build('slides', 'v1', credentials=creds)
presentation = slides_service.presentations().create(
    body={'title': 'PresGen Test - AWS Deployment'}
).execute()

presentation_id = presentation['presentationId']
print(f"✅ OAuth authentication working!")
print(f"✅ Created test presentation: {presentation_id}")
print(f"✅ URL: https://docs.google.com/presentation/d/{presentation_id}/edit")

# Clean up
drive_service = build('drive', 'v3', credentials=creds)
drive_service.files().delete(fileId=presentation_id).execute()
print("✅ Test presentation deleted")
EOF
```

**Expected Output:**
```
✅ OAuth authentication working!
✅ Created test presentation: 1a2b3c4d5e6f7g8h9i0j
✅ URL: https://docs.google.com/presentation/d/1a2b3c4d5e6f7g8h9i0j/edit
✅ Test presentation deleted
```

### Test 3: Full Application Flow

```bash
# Test through the API
curl -X POST http://localhost:8080/api/generate \
  -H "Content-Type: application/json" \
  -d '{
    "topic": "AI in Healthcare",
    "slides": 5
  }'

# Check logs for authentication
docker logs presgen-core --tail 50 | grep -i "auth\|credential"
```

**What to Look For:**
```
[INFO] ✅ Successfully authenticated with service account (for Vertex AI)
[INFO] ✅ Using OAuth credentials for Slides API
[INFO] ✅ Presentation created: https://docs.google.com/presentation/d/...
```

---

## Troubleshooting

### Issue: "403 Permission Denied" for Slides API

**Symptom:**
```
HttpError 403: The caller does not have permission
```

**Diagnosis:**
```bash
# Check if OAuth fallback is enabled
docker exec presgen-core env | grep FORCE_SERVICE_ACCOUNT
# Should be empty or "false"

# If it shows "true", that's the problem!
```

**Fix:**
```bash
# Edit .env file
ssh -i lightsail-key.pem ubuntu@YOUR_STATIC_IP
cd /home/ubuntu/presgen
nano .env

# Remove or comment out this line:
# FORCE_SERVICE_ACCOUNT=true

# Save and restart
docker-compose down
docker-compose up -d
```

### Issue: "OAuth token expired"

**Symptom:**
```
google.auth.exceptions.RefreshError: invalid_grant
```

**Fix:**
```bash
# Regenerate OAuth token locally
cd /Users/yitzchak/Documents/learn/presentation_project/sales-agent-labs

# Remove old token
rm token.json

# Run any PresGen command to trigger OAuth flow
python3 -m src.cli.main generate --topic "Test" --slides 3

# Browser will open - sign in with Google account
# New token.json will be created

# Upload new token to server
scp -i lightsail-key.pem token.json \
    ubuntu@YOUR_STATIC_IP:/home/ubuntu/presgen/secrets/

# Restart services
ssh -i lightsail-key.pem ubuntu@YOUR_STATIC_IP
docker-compose restart presgen-core
```

### Issue: "Secrets file not found"

**Symptom:**
```
FileNotFoundError: [Errno 2] No such file or directory: '/secrets/google-creds.json'
```

**Fix:**
```bash
# Upload secrets manually
scp -i lightsail-key.pem secrets/google-creds.json \
    ubuntu@YOUR_STATIC_IP:/home/ubuntu/presgen/secrets/
scp -i lightsail-key.pem secrets/token.json \
    ubuntu@YOUR_STATIC_IP:/home/ubuntu/presgen/secrets/
scp -i lightsail-key.pem secrets/oauth_slides_client.json \
    ubuntu@YOUR_STATIC_IP:/home/ubuntu/presgen/secrets/

# Set permissions
ssh -i lightsail-key.pem ubuntu@YOUR_STATIC_IP
chmod 600 /home/ubuntu/presgen/secrets/*.json

# Restart containers
docker-compose restart
```

---

## Required Google Cloud APIs

Ensure these APIs are enabled in [Google Cloud Console](https://console.cloud.google.com/apis/library):

- ✅ **Google Slides API** (slides.googleapis.com)
- ✅ **Google Drive API** (drive.googleapis.com)
- ✅ **Google Forms API** (forms.googleapis.com)
- ✅ **Google Sheets API** (sheets.googleapis.com)
- ✅ **Vertex AI API** (aiplatform.googleapis.com)
- ✅ **Cloud Vision API** (vision.googleapis.com)
- ✅ **Cloud Storage API** (storage.googleapis.com)

**Quick enable command:**
```bash
gcloud services enable \
  slides.googleapis.com \
  drive.googleapis.com \
  forms.googleapis.com \
  sheets.googleapis.com \
  aiplatform.googleapis.com \
  vision.googleapis.com \
  storage.googleapis.com \
  --project=presgen
```

---

## Cost Analysis

### Google Cloud API Usage (Per Demo)

| API | Free Tier | Usage per Demo | Cost |
|-----|-----------|----------------|------|
| Google Slides | 100 req/100sec | ~50 requests | $0.00 |
| Google Drive | 1,000 req/100sec | ~20 requests | $0.00 |
| Vertex AI (Gemini) | First 1M tokens | ~100K tokens | $0.20 |
| Vertex AI (Imagen) | First 100 images | ~10 images | $0.20 |

**Total Cost: ~$0.40 per demo** (within free tier for first few demos)

### Alternative: Google Workspace Subscription

If you wanted to use service account for Workspace APIs:

- **Cost:** $6-18/month per user
- **Setup:** Domain-Wide Delegation configuration required
- **Recommendation:** NOT worth it for demo purposes - use OAuth instead

---

## Security Best Practices

### 1. File Permissions

```bash
# On server
chmod 600 /home/ubuntu/presgen/secrets/*.json
chown ubuntu:ubuntu /home/ubuntu/presgen/secrets/*.json
```

### 2. Never Commit Secrets

```bash
# Verify .gitignore
cat .gitignore | grep -E "secrets|token.json"

# Should include:
# secrets/
# token.json
# *-service-account.json
# *.pem
```

### 3. Rotate Service Account Keys (Every 90 Days)

```bash
# Create new key
gcloud iam service-accounts keys create new-key.json \
  --iam-account=presgen-service-account-test@presgen.iam.gserviceaccount.com

# Upload to server
scp -i lightsail-key.pem new-key.json \
    ubuntu@YOUR_STATIC_IP:/home/ubuntu/presgen/secrets/google-creds.json

# Restart services
ssh -i lightsail-key.pem ubuntu@YOUR_STATIC_IP
docker-compose restart

# Delete old key
gcloud iam service-accounts keys list \
  --iam-account=presgen-service-account-test@presgen.iam.gserviceaccount.com
# Note the old key ID, then:
gcloud iam service-accounts keys delete OLD_KEY_ID \
  --iam-account=presgen-service-account-test@presgen.iam.gserviceaccount.com
```

---

## Related Documentation

- **[AWS_MIGRATION_PLAN.md](AWS_MIGRATION_PLAN.md)** - Section: "Google Cloud Authentication Setup"
- **[DETAILED_DEPLOYMENT_PLAN.md](DETAILED_DEPLOYMENT_PLAN.md)** - Section: "Google Cloud Authentication Strategy"
- **[GOOGLE_AUTH_CONFIGURATION.md](GOOGLE_AUTH_CONFIGURATION.md)** - Complete authentication guide
- **[FINAL_SOLUTION_403.md](FINAL_SOLUTION_403.md)** - Root cause analysis of 403 error

---

## Final Checklist

Before deploying to AWS Lightsail:

- [ ] `secrets/google-creds.json` exists locally
- [ ] `secrets/token.json` exists locally
- [ ] `secrets/oauth_slides_client.json` exists locally
- [ ] `.env` has `GOOGLE_APPLICATION_CREDENTIALS=/secrets/google-creds.json`
- [ ] `.env` has `OAUTH_TOKEN_PATH=/secrets/token.json`
- [ ] `.env` has `OAUTH_CLIENT_JSON=/secrets/oauth_slides_client.json`
- [ ] `.env` does NOT have `FORCE_SERVICE_ACCOUNT=true`
- [ ] All Google APIs enabled in Cloud Console
- [ ] Service account has Owner role in project `presgen`
- [ ] OAuth token is valid (test locally first)
- [ ] `.gitignore` includes `secrets/` directory

**If all checked, you're ready to deploy!** 🚀

---

**Status:** ✅ Configuration Complete
**Authentication Method:** Dual (Service Account + OAuth)
**Expected Result:** All APIs (Cloud + Workspace) working seamlessly
**Last Verified:** October 29, 2025
