# Enable Service Account Authentication - Step-by-Step Guide

**Date:** 2025-11-03
**Status:** Ready to Enable
**Service Account:** presgen-service-account-test@presgen.iam.gserviceaccount.com

---

## Current Status ✅

Your local configuration is **already set up correctly**:

- ✅ Service account JSON file exists: `presgen-service-account.json`
- ✅ `.env` has `GOOGLE_APPLICATION_CREDENTIALS` set
- ✅ `.env` has `GOOGLE_SERVICE_ACCOUNT_IMPERSONATE_USER=presgen-service@presgen.net`
- ✅ `.env` has `DRIVE_FOLDER_ID=14eRckmEzL-4FgXU4mn3u3-EP2GKNJX2p`
- ✅ Test script is ready to run

**What's Missing:** Google Workspace Admin Console configuration (domain-wide delegation)

---

## Why Service Account Failed Previously

Looking at your code in [slides_google.py:56-82](src/agent/slides_google.py#L56-L82), the service account authentication tries to:

1. Load credentials from `GOOGLE_APPLICATION_CREDENTIALS`
2. Enable domain-wide delegation (impersonate a user)
3. Apply quota project

**It failed because:**
- Domain-wide delegation is **not yet enabled** in Google Workspace Admin Console
- Without delegation, the service account can't impersonate `presgen-service@presgen.net`
- Your code has `FORCE_SERVICE_ACCOUNT=false`, so it fell back to OAuth

---

## Step 1: Enable Domain-Wide Delegation in Google Workspace Admin Console

### 1.1 Get Your Service Account Client ID

First, retrieve the Client ID for your service account:

```bash
cd /Users/yitzchak/Documents/learn/presentation_project/sales-agent-labs

# Extract Client ID from service account JSON
python3 -c "import json; print('Client ID:', json.load(open('presgen-service-account.json'))['client_id'])"
```

**Save this Client ID** - you'll need it in the next step.

### 1.2 Navigate to Google Workspace Admin Console

1. **Open:** https://admin.google.com
2. **Login with:** Your Google Workspace admin account for `presgen.net` domain

### 1.3 Go to API Controls

**Option A - Direct Link:**
- https://admin.google.com/ac/owl/domainwidedelegation

**Option B - Navigate:**
1. Click **Security** in the left menu
2. Click **Access and data control**
3. Click **API Controls**
4. Scroll down to **Domain-wide delegation** section
5. Click **MANAGE DOMAIN WIDE DELEGATION**

### 1.4 Add Service Account Authorization

1. Click **Add new** (blue button)

2. **Fill in the form:**

   **Client ID:** (paste the Client ID from Step 1.1)

   **OAuth Scopes:** (copy-paste this entire line)
   ```
   https://www.googleapis.com/auth/drive,https://www.googleapis.com/auth/drive.file,https://www.googleapis.com/auth/presentations,https://www.googleapis.com/auth/script.projects
   ```

3. Click **Authorize**

4. You should see a confirmation: "Client ID [your-client-id] has been authorized"

### 1.5 ⏰ WAIT 10-15 Minutes

**CRITICAL:** Google needs time to propagate these changes across their infrastructure.

- ✅ DO: Wait at least 10 minutes before testing
- ❌ DON'T: Test immediately (it will fail with 403 errors)

**Set a timer!** While you wait, continue reading the rest of this guide.

---

## Step 2: Verify Impersonation User Exists

The service account will impersonate `presgen-service@presgen.net` to access resources.

### 2.1 Check User Exists in Workspace

1. Go to: https://admin.google.com
2. Click **Directory** → **Users**
3. Search for: `presgen-service@presgen.net`

**Options:**

- ✅ **If user exists:** Great! Verify they have access to Google Drive/Slides
- ❌ **If user doesn't exist:** Either:
  - Create the user `presgen-service@presgen.net`, OR
  - Update `.env` to use an existing admin user:
    ```bash
    GOOGLE_SERVICE_ACCOUNT_IMPERSONATE_USER=admin@presgen.net
    ```

### 2.2 Verify User Has Required Permissions

The impersonation user needs:
- Google Drive enabled
- Google Slides enabled
- Part of `presgen.net` domain

---

## Step 3: Verify Google Drive Folder Sharing

Your service account needs access to folder `14eRckmEzL-4FgXU4mn3u3-EP2GKNJX2p`.

### 3.1 Share Folder with Service Account (If Not Already Shared)

1. Open Google Drive: https://drive.google.com
2. Find folder ID `14eRckmEzL-4FgXU4mn3u3-EP2GKNJX2p` in the URL
3. Right-click the folder → **Share**
4. Add email: `presgen-service-account-test@presgen.iam.gserviceaccount.com`
5. Set role: **Editor** (or **Owner** if you want full control)
6. Click **Share**

**Note:** With domain-wide delegation, the service account impersonates your user, so this step might not be strictly necessary, but it's good practice.

---

## Step 4: Test Service Account Authentication

After waiting 10-15 minutes from Step 1.5, run the test:

### 4.1 Run Test Script

```bash
cd /Users/yitzchak/Documents/learn/presentation_project/sales-agent-labs

# Install dependencies if needed
pip3 install google-auth google-auth-oauthlib google-api-python-client

# Run the test
python3 test_service_account.py
```

### 4.2 Expected Output (Success)

```
============================================================
  Current Configuration
============================================================
Credentials File: ./presgen-service-account.json
Impersonate User: presgen-service@presgen.net
Folder ID: 14eRckmEzL-4FgXU4mn3u3-EP2GKNJX2p
Scopes: 3 configured
  - https://www.googleapis.com/auth/drive
  - https://www.googleapis.com/auth/drive.file
  - https://www.googleapis.com/auth/presentations
============================================================

============================================================
  PresGen Service Account Test
============================================================

🔐 Step 1: Loading service account credentials...
✅ Credentials loaded successfully
   Service Account: presgen-service-account-test@presgen.iam.gserviceaccount.com

👤 Step 2: Configuring impersonation...
   Impersonating user: presgen-service@presgen.net
✅ Impersonation configured

🔨 Step 3: Building Google Drive service...
✅ Drive service built successfully

📁 Step 4: Testing access to shared folder...
   Folder ID: 14eRckmEzL-4FgXU4mn3u3-EP2GKNJX2p
✅ Successfully accessed folder!
   Found X file(s):
   - [list of files]

📝 Step 5: Testing file creation...
✅ Created test presentation!
   Title: PresGen Test Presentation
   ID: [presentation-id]
✅ Moved to shared folder!
   Link: https://docs.google.com/presentation/d/...

============================================================
  ✅ TEST COMPLETED SUCCESSFULLY!
============================================================
Your service account is properly configured and can:
  ✓ Authenticate with Google Workspace
  ✓ Impersonate the specified user
  ✓ Access the shared Google Drive folder
  ✓ Create presentations (if tested)

You're ready to use PresGen with Google Workspace!

🎉 All tests passed!
```

### 4.3 Common Errors and Solutions

#### Error: `403 Forbidden` - "Access Not Configured"

**Cause:** Domain-wide delegation not yet propagated

**Solution:**
- Wait longer (try 15-20 minutes)
- Verify you added the correct Client ID in Admin Console
- Verify scopes are correct
- Double-check you clicked "Authorize"

#### Error: `403 Forbidden` - "Insufficient Permission"

**Cause:** Scopes not authorized or wrong scopes

**Solution:**
1. Go back to Admin Console → API Controls → Domain-wide delegation
2. Find your Client ID entry
3. Click **Edit**
4. Verify scopes exactly match:
   ```
   https://www.googleapis.com/auth/drive,https://www.googleapis.com/auth/drive.file,https://www.googleapis.com/auth/presentations,https://www.googleapis.com/auth/script.projects
   ```
5. Click **Authorize**
6. Wait another 10 minutes

#### Error: `404 Not Found` - Folder access

**Cause:** Folder not shared or wrong ID

**Solution:**
- Verify folder ID `14eRckmEzL-4FgXU4mn3u3-EP2GKNJX2p` is correct
- Share folder with service account email
- Verify folder is not in trash

#### Error: "Invalid impersonation prn email address"

**Cause:** Impersonation user doesn't exist

**Solution:**
- Create user `presgen-service@presgen.net` in Workspace, OR
- Change `IMPERSONATE_USER` to an existing admin user

---

## Step 5: Enable Service Account for PresGen

Once the test passes, you can enable service account authentication for PresGen.

### 5.1 Optional: Force Service Account (Disable OAuth Fallback)

If you want to **require** service account authentication (no OAuth fallback):

```bash
# Edit .env file
nano .env

# Change this line:
FORCE_SERVICE_ACCOUNT=false

# To:
FORCE_SERVICE_ACCOUNT=true
```

**Warning:** If service account fails for any reason, your app will crash instead of falling back to OAuth.

**Recommendation:** Keep `FORCE_SERVICE_ACCOUNT=false` until you're confident everything works.

### 5.2 Restart PresGen Services

```bash
# If running directly
cd /Users/yitzchak/Documents/learn/presentation_project/sales-agent-labs
# Restart your Python processes

# If running via Docker
docker-compose restart presgen-assess presgen-core
```

### 5.3 Verify Service Account is Being Used

Check the logs for this message:

```
✅ Successfully authenticated with service account
```

Instead of:

```
⚠️ OAuth fallback enabled - OAuth client may be invalid/revoked
```

---

## Step 6: Monitor and Troubleshoot

### 6.1 Check Logs for Authentication Method

Your [slides_google.py:76](src/agent/slides_google.py#L76) logs when service account succeeds:

```python
log.info("✅ Successfully authenticated with service account")
```

And [slides_google.py:82](src/agent/slides_google.py#L82) logs when it falls back to OAuth:

```python
log.warning(f"Service account authentication failed: {e}. Falling back to OAuth.")
```

### 6.2 Common Production Issues

**Issue:** "storageQuotaExceeded 403 Permission Denied"

**From your notes:** [Google OAuth-Service Account Auth Problems.txt:1-5](Google OAuth-Service Account Auth Problems.txt#L1-L5)

**Solution:**
- Service account hit storage quota
- Temporarily use OAuth while you clean up storage
- Set `FORCE_SERVICE_ACCOUNT=false` to allow fallback

---

## Summary Checklist

Use this checklist to track your progress:

### Google Workspace Admin Console Setup
- [ ] Retrieved service account Client ID
- [ ] Logged into https://admin.google.com as Workspace admin
- [ ] Navigated to API Controls → Domain-wide delegation
- [ ] Added new client authorization with Client ID and scopes
- [ ] Clicked "Authorize"
- [ ] **Waited 10-15 minutes** for propagation

### User and Folder Setup
- [ ] Verified `presgen-service@presgen.net` user exists in Workspace
- [ ] Verified user has Drive/Slides access
- [ ] Shared folder `14eRckmEzL-4FgXU4mn3u3-EP2GKNJX2p` with service account (optional)

### Testing
- [ ] Installed Python dependencies (`google-auth`, `google-api-python-client`)
- [ ] Ran `python3 test_service_account.py`
- [ ] Test passed successfully
- [ ] Created test presentation visible in Google Drive

### Production Deployment
- [ ] (Optional) Set `FORCE_SERVICE_ACCOUNT=true` to disable OAuth fallback
- [ ] Restarted PresGen services
- [ ] Verified logs show "Successfully authenticated with service account"
- [ ] Tested creating presentations via PresGen API

---

## Quick Reference

**Service Account Email:**
```
presgen-service-account-test@presgen.iam.gserviceaccount.com
```

**Impersonation User:**
```
presgen-service@presgen.net
```

**Required Scopes:**
```
https://www.googleapis.com/auth/drive
https://www.googleapis.com/auth/drive.file
https://www.googleapis.com/auth/presentations
https://www.googleapis.com/auth/script.projects
```

**Key Files:**
- Service account credentials: `presgen-service-account.json`
- Configuration: `.env`
- Test script: `test_service_account.py`
- Authentication code: `src/agent/slides_google.py` (lines 44-124)

---

## Need Help?

If you encounter issues:

1. **Check the logs** in `src/agent/slides_google.py` for specific error messages
2. **Review** [GOOGLE_WORKSPACE_STATUS.md](GOOGLE_WORKSPACE_STATUS.md) for known issues
3. **Verify** all steps in this guide were completed
4. **Wait longer** - Google can take up to 30 minutes to propagate changes
5. **Try OAuth fallback** by keeping `FORCE_SERVICE_ACCOUNT=false`

---

**Status:** ✅ Ready to enable service account authentication!
**Next Step:** Follow Step 1 to enable domain-wide delegation in Google Workspace Admin Console
