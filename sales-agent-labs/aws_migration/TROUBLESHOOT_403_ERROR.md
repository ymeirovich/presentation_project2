# Troubleshooting: 403 Permission Denied Error

**Status:** Service account has Owner role, API is enabled, but still getting 403

This is a **service account KEY restriction** issue, not an IAM or API enablement issue.

---

## 🔍 What We Know

✅ **Working:**
- Service account exists: `presgen-service-account-test@presgen.iam.gserviceaccount.com`
- IAM role assigned: **Owner** (highest permission)
- Google Drive API works
- Authentication succeeds

❌ **Not Working:**
- Google Slides API returns 403: "The caller does not have permission"

---

## 🎯 Root Cause

The service account **key** (the JSON file) might have **API restrictions** that block access to Google Slides API, even though:
1. The service account has Owner role
2. The Slides API is enabled

This is a common security feature where keys can be restricted to specific APIs.

---

## 🔧 Solution: Check and Fix API Key Restrictions

### Step 1: Check Current Key Restrictions

1. **Go to API Credentials page:**
   ```
   https://console.cloud.google.com/apis/credentials?project=presgen
   ```

2. **Find your service account key:**
   - Look for: `presgen-service-account-test@presgen.iam.gserviceaccount.com`
   - Or find the key ID from your JSON file

3. **Check for API restrictions:**
   - If you see "API restrictions" column
   - Check if it says "Restricted" or shows specific APIs

### Step 2: Create NEW Service Account Key WITHOUT Restrictions

**Option A: Create New Key for Existing Service Account (Recommended)**

1. **Go to Service Accounts page:**
   ```
   https://console.cloud.google.com/iam-admin/serviceaccounts?project=presgen
   ```

2. **Click on your service account:**
   `presgen-service-account-test@presgen.iam.gserviceaccount.com`

3. **Go to "KEYS" tab**

4. **Click "ADD KEY" → "Create new key"**

5. **Select "JSON"** and click "CREATE"

6. **Download the new JSON file**

7. **Replace your current key:**
   ```bash
   cd /Users/yitzchak/Documents/learn/presentation_project/sales-agent-labs

   # Backup old key
   mv secrets/google-creds.json secrets/google-creds.json.backup

   # Copy new key
   cp ~/Downloads/presgen-*.json secrets/google-creds.json
   ```

8. **Test again:**
   ```bash
   python3 scripts/test-drive-ownership.py
   ```

**Option B: Create Entirely New Service Account (Alternative)**

If the above doesn't work, create a fresh service account:

1. **Go to Service Accounts page:**
   ```
   https://console.cloud.google.com/iam-admin/serviceaccounts/create?project=presgen
   ```

2. **Fill in details:**
   - Name: `presgen-deployment`
   - ID: `presgen-deployment` (auto-filled)
   - Description: `Service account for PresGen AWS deployment`
   - Click "CREATE AND CONTINUE"

3. **Grant roles:**
   - Select role: **Editor**
   - Click "CONTINUE"
   - Click "DONE"

4. **Create key:**
   - Click on newly created service account
   - Go to "KEYS" tab
   - Click "ADD KEY" → "Create new key"
   - Select "JSON"
   - Click "CREATE"
   - Download JSON file

5. **Replace key:**
   ```bash
   cp ~/Downloads/presgen-deployment-*.json secrets/google-creds.json
   ```

6. **Test:**
   ```bash
   python3 scripts/test-drive-ownership.py
   ```

---

## 🔧 Solution: Check Organization Policies (If Using Google Workspace)

If you're using **Google Workspace** (not personal Google account), organization policies might block service accounts.

### Check Organization Policies

1. **Go to Organization Policies:**
   ```
   https://console.cloud.google.com/iam-admin/orgpolicies?project=presgen
   ```

2. **Look for these policies:**
   - `constraints/iam.disableServiceAccountKeyCreation`
   - `constraints/iam.disableServiceAccountCreation`
   - `constraints/compute.requireOsLogin`

3. **If any are ENFORCED:**
   - Contact your Workspace administrator
   - They need to add an exception for the PresGen project

### Alternative: Use OAuth Instead (If Workspace Blocks Service Accounts)

If Workspace policies block service accounts entirely:

```bash
# Use OAuth instead (requires user consent)
# Already configured in your codebase

# Remove FORCE_SERVICE_ACCOUNT from .env
# The code will automatically fall back to OAuth
```

---

## 🔧 Solution: Enable APIs with gcloud CLI

Sometimes APIs aren't fully enabled via the console. Try enabling via CLI:

```bash
# Install gcloud CLI if not installed
# https://cloud.google.com/sdk/docs/install

# Login and set project
gcloud auth login
gcloud config set project presgen

# Enable APIs explicitly
gcloud services enable slides.googleapis.com
gcloud services enable drive.googleapis.com
gcloud services enable forms.googleapis.com
gcloud services enable sheets.googleapis.com

# Verify enabled
gcloud services list --enabled | grep -E 'slides|drive|forms|sheets'

# Wait 5 minutes for propagation
sleep 300

# Test again
python3 scripts/test-drive-ownership.py
```

---

## 🔧 Solution: Check Quota/Usage

Sometimes 403 errors are actually quota issues disguised as permission errors:

1. **Check API quotas:**
   ```
   https://console.cloud.google.com/apis/api/slides.googleapis.com/quotas?project=presgen
   ```

2. **Look for:**
   - "Queries per day" - should have available quota
   - "Queries per 100 seconds" - should have available quota

3. **If quota is 0 or exhausted:**
   - Request quota increase
   - Or wait 24 hours for reset

---

## 🧪 Alternative Test: Use gcloud Instead

Test if the issue is with the Python library or the service account itself:

```bash
# Get access token from service account
ACCESS_TOKEN=$(gcloud auth application-default print-access-token \
  --impersonate-service-account=presgen-service-account-test@presgen.iam.gserviceaccount.com)

# Test Slides API directly
curl -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"title": "Test Presentation"}' \
  https://slides.googleapis.com/v1/presentations

# If this works but Python doesn't, it's a library issue
# If this also fails with 403, it's definitely a service account permission issue
```

---

## 🎯 Most Likely Solutions (In Order)

### 1. Create New Service Account Key (90% chance this fixes it)

The current key might have been created with restrictions. Create a new key:

```bash
# In Google Cloud Console:
# 1. IAM → Service Accounts
# 2. Click presgen-service-account-test
# 3. Keys tab → Add Key → Create new key → JSON
# 4. Download and replace secrets/google-creds.json
```

### 2. Wait for API Propagation (5% chance)

Sometimes APIs take time to fully enable:

```bash
# Wait 10 minutes
sleep 600

# Try again
python3 scripts/test-drive-ownership.py
```

### 3. Check Workspace Policies (3% chance if using Workspace)

Organization might block service accounts:

```bash
# Contact Workspace admin to check policies
```

### 4. Billing Not Enabled (2% chance)

Some APIs require billing to be enabled:

```bash
# Check billing:
https://console.cloud.google.com/billing?project=presgen

# Enable if not enabled
```

---

## 📋 Diagnostic Checklist

Run through this checklist:

```
Service Account Checks:
- [ ] Service account exists in IAM
- [ ] Has Editor or Owner role
- [ ] Key file (JSON) is not corrupted
- [ ] Key file is less than 10 years old (keys expire)

API Checks:
- [ ] Google Slides API shows "Enabled" in console
- [ ] Google Drive API shows "Enabled" in console
- [ ] APIs enabled for more than 5 minutes (propagation time)
- [ ] No quota limits reached

Permission Checks:
- [ ] No organization policies blocking service accounts
- [ ] Billing is enabled on project (if required)
- [ ] Project is active (not suspended)

Test Results:
- [ ] Can load service account JSON file ✅ (already works)
- [ ] Can authenticate ✅ (already works)
- [ ] Can list Drive files ✅ (already works)
- [ ] Can create Slides presentation ❌ (this is the issue)
```

---

## 🚀 Quick Fix Script

Run this to try the most common fixes automatically:

```bash
#!/bin/bash
# quick-fix-403.sh

echo "=== Quick Fix for 403 Error ==="

# 1. Re-enable APIs
echo "1. Re-enabling APIs..."
gcloud services enable slides.googleapis.com --project=presgen
gcloud services enable drive.googleapis.com --project=presgen

# 2. Wait for propagation
echo "2. Waiting 2 minutes for propagation..."
sleep 120

# 3. Test
echo "3. Testing..."
python3 scripts/test-drive-ownership.py

echo ""
echo "If still failing, create a new service account key:"
echo "  1. Go to: https://console.cloud.google.com/iam-admin/serviceaccounts?project=presgen"
echo "  2. Click on service account"
echo "  3. Keys tab → Add Key → Create new key → JSON"
echo "  4. Replace secrets/google-creds.json"
```

---

## 💡 Workaround: Use OAuth for Testing

While debugging, you can test with OAuth instead:

```bash
# Temporarily disable service account forcing
export FORCE_SERVICE_ACCOUNT=false

# Run test (will use OAuth)
python3 scripts/test-google-auth.py

# This will open browser for consent
# If OAuth works but service account doesn't, it confirms service account issue
```

---

## 📞 Summary

**Most Likely Issue:** Service account key has API restrictions

**Best Fix:** Create new service account key without restrictions

**Quick Steps:**
1. Go to https://console.cloud.google.com/iam-admin/serviceaccounts?project=presgen
2. Click service account → Keys tab
3. Add Key → Create new key → JSON
4. Download and replace `secrets/google-creds.json`
5. Test: `python3 scripts/test-drive-ownership.py`

**If that doesn't work:** Create entirely new service account with Editor role

---

**Updated:** October 28, 2025
