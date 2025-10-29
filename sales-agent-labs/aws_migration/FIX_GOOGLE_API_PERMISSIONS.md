# Fix Google API Permissions

**Status:** ❌ Google Slides API not enabled
**Solution:** Enable APIs in Google Cloud Console (5 minutes)

---

## 📊 Test Results Summary

✅ **Working:**
- Dependencies installed
- Service account file found
- Authentication successful
- Google Drive API enabled

❌ **Needs Fix:**
- Google Slides API not enabled
- Environment variables not set

---

## 🔧 Fix #1: Enable Google Slides API (REQUIRED)

### Step-by-Step Instructions

1. **Open Google Cloud Console:**
   ```
   https://console.cloud.google.com/apis/library?project=presgen
   ```

2. **Search for "Google Slides API":**
   - Click in search box
   - Type: "Google Slides API"
   - Click on the result

3. **Enable the API:**
   - Click **"Enable"** button
   - Wait 30 seconds for activation

4. **Repeat for other APIs:**

   **Required APIs:**
   - ✅ Google Drive API (already enabled)
   - ❌ Google Slides API (needs enabling)
   - ❌ Google Forms API (for assess module)
   - ❌ Google Sheets API (for exports)
   - ❌ Vertex AI API (for image generation)

### Quick Enable All APIs

Visit these direct links (while logged into Google Cloud Console):

```bash
# Google Slides API
https://console.cloud.google.com/apis/library/slides.googleapis.com?project=presgen

# Google Forms API
https://console.cloud.google.com/apis/library/forms.googleapis.com?project=presgen

# Google Sheets API
https://console.cloud.google.com/apis/library/sheets.googleapis.com?project=presgen

# Vertex AI API
https://console.cloud.google.com/apis/library/aiplatform.googleapis.com?project=presgen
```

**For each link:**
1. Click **"Enable"**
2. Wait for confirmation
3. Move to next API

---

## 🔧 Fix #2: Set Environment Variables (OPTIONAL for local testing)

**For Local Testing Only:**

```bash
# In project root directory
cd /Users/yitzchak/Documents/learn/presentation_project/sales-agent-labs

# Set environment variables
export GOOGLE_APPLICATION_CREDENTIALS="$(pwd)/secrets/google-creds.json"
export GOOGLE_CLOUD_PROJECT=presgen
export FORCE_SERVICE_ACCOUNT=true

# Run test again
python3 scripts/test-google-auth.py
```

**For AWS Deployment:**
These will be set automatically in `.env` file (already configured in deployment scripts).

---

## ✅ Verify Fix

After enabling APIs, run the test again:

```bash
cd /Users/yitzchak/Documents/learn/presentation_project/sales-agent-labs

# Run test
python3 scripts/test-google-auth.py
```

**Expected Output:**
```
============================================================
Test Summary
============================================================
  Dependencies                   ✓ PASS
  Service Account File           ✓ PASS
  Authentication                 ✓ PASS
  Google Slides API              ✓ PASS  ← Should be fixed now
  Google Drive API               ✓ PASS
  Environment Variables          ✓ PASS  ← If env vars set
✅ ALL TESTS PASSED!
```

---

## 🎯 What You've Learned

### ✅ What Works
1. **Service account is valid** ✓
   - File: `secrets/google-creds.json`
   - Email: `presgen-service-account-test@presgen.iam.gserviceaccount.com`

2. **Authentication working** ✓
   - Successfully loads credentials
   - No OAuth needed

3. **Google Drive API enabled** ✓
   - Can list files
   - Ready for use

### ❌ What Needs Fixing
1. **Enable Google Slides API**
   - Go to Cloud Console
   - Click "Enable" button
   - Takes 30 seconds

2. **Enable other APIs** (for full functionality)
   - Forms, Sheets, Vertex AI

---

## 📝 Pre-Deployment Checklist

Before deploying to AWS, ensure:

- [ ] Google Slides API enabled
- [ ] Google Forms API enabled (for assess module)
- [ ] Google Sheets API enabled (for exports)
- [ ] Vertex AI API enabled (for image generation)
- [ ] Service account file copied to `secrets/google-creds.json` ✓
- [ ] Test passes: `python3 scripts/test-google-auth.py`

---

## 🚀 Ready for AWS Deployment

Once all APIs are enabled and test passes, you're ready to deploy:

```bash
# Update .env file (if not already done)
cat >> .env << EOF

# Google Cloud Authentication
GOOGLE_APPLICATION_CREDENTIALS=/secrets/google-creds.json
FORCE_SERVICE_ACCOUNT=true
GOOGLE_CLOUD_PROJECT=presgen
EOF

# Deploy to AWS
./deployment/deploy-to-lightsail.sh presgen-demo small_2_0
```

---

## 🆘 Troubleshooting

### Issue: "403 Permission Denied" persists after enabling API

**Solution:**
Wait 5 minutes for API activation to propagate, then try again.

```bash
# Wait 5 minutes, then:
python3 scripts/test-google-auth.py
```

### Issue: "Can't find project 'presgen'"

**Solution:**
Verify you're logged into the correct Google account:

```bash
# Check current project
gcloud config get-value project

# List all projects
gcloud projects list

# Set correct project
gcloud config set project presgen
```

### Issue: "Module not found" errors

**Solution:**
Reinstall dependencies:

```bash
pip3 install --user google-auth google-auth-oauthlib google-api-python-client
```

---

## 📞 Need Help?

If APIs are enabled but tests still fail:

1. **Check API status:**
   ```
   https://console.cloud.google.com/apis/dashboard?project=presgen
   ```

2. **Check service account permissions:**
   ```
   https://console.cloud.google.com/iam-admin/serviceaccounts?project=presgen
   ```

3. **Check quota usage:**
   ```
   https://console.cloud.google.com/apis/api/slides.googleapis.com/quotas?project=presgen
   ```

---

**Next Step:** Enable Google Slides API in Cloud Console, then re-run test! 🚀
