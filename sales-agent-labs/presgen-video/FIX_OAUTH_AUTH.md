# Fix PresGen-Video OAuth Authentication Error

## Error
```
2025-10-02 10:43:18 - service - ERROR - Google Slides authentication failed: ('invalid_client: Unauthorized', {'error': 'invalid_client', 'error_description': 'Unauthorized'})
```

## Root Cause

The OAuth client credentials in `oauth_slides_client.json` are **invalid or revoked**.

**Client ID**: `247572193615-3q5babgbb76lhn8sf3do3fgnaldkgdl1.apps.googleusercontent.com`
**Status**: ❌ Unauthorized (revoked or deleted in Google Cloud Console)

## Solution Options

### Option 1: Use Service Account Only (Recommended)

Since service account authentication is already implemented in `slides_google.py`, force it to use only service account:

**Update `.env`**:
```bash
# Force service account auth (no OAuth fallback)
GOOGLE_APPLICATION_CREDENTIALS=/Users/yitzchak/Documents/learn/presentation_project/sales-agent-labs/presgen-service-account2.json
FORCE_SERVICE_ACCOUNT=true
```

**Update `src/agent/slides_google.py`**:
```python
def _load_credentials() -> Credentials:
    SCOPES = [SLIDES_SCOPE, DRIVE_SCOPE, SCRIPT_SCOPE]

    # Force service account if env var set
    force_service_account = os.getenv("FORCE_SERVICE_ACCOUNT") == "true"

    # Try service account first (or only, if forced)
    service_account_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    if service_account_path and pathlib.Path(service_account_path).exists():
        try:
            log.info(f"Using service account authentication: {service_account_path}")
            creds = ServiceAccountCredentials.from_service_account_file(
                service_account_path,
                scopes=SCOPES
            )
            log.info("✅ Service account authenticated successfully")
            return creds
        except Exception as e:
            if force_service_account:
                log.error(f"Service account authentication failed and no fallback allowed: {e}")
                raise
            log.warning(f"Service account failed: {e}. Trying OAuth fallback.")

    # OAuth fallback (only if not forced to use service account)
    if force_service_account:
        raise RuntimeError("Service account required but authentication failed")

    # ... rest of OAuth code ...
```

### Option 2: Create New OAuth Client Credentials

If you need OAuth for user-specific operations:

1. **Go to Google Cloud Console**:
   - https://console.cloud.google.com/apis/credentials?project=presgen

2. **Create New OAuth 2.0 Client ID**:
   - Click "Create Credentials" → "OAuth client ID"
   - Application type: "Desktop app"
   - Name: "PresGen Video OAuth"
   - Click "Create"

3. **Download Credentials**:
   - Click download button (↓) next to the new client
   - Save as `oauth_slides_client_new.json`

4. **Update Code**:
   ```python
   OAUTH_CLIENT_JSON = pathlib.Path("oauth_slides_client_new.json")
   ```

5. **Delete Old Token**:
   ```bash
   rm token_slides.json
   ```

6. **Test Authentication**:
   - Run PresGen-Video
   - Browser opens for new consent
   - Grant permissions
   - New token saved

### Option 3: Disable OAuth Fallback

If service account works, remove OAuth entirely:

**Update `src/agent/slides_google.py`**:
```python
def _load_credentials() -> Credentials:
    SCOPES = [SLIDES_SCOPE, DRIVE_SCOPE, SCRIPT_SCOPE]

    service_account_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    if not service_account_path or not pathlib.Path(service_account_path).exists():
        raise RuntimeError(
            f"Service account not found: {service_account_path}\n"
            "Set GOOGLE_APPLICATION_CREDENTIALS environment variable"
        )

    log.info(f"Using service account: {service_account_path}")
    creds = ServiceAccountCredentials.from_service_account_file(
        service_account_path,
        scopes=SCOPES
    )
    log.info("✅ Service account authenticated")
    return creds
```

## Quick Fix (Immediate)

**Add to presgen-video/.env**:
```bash
# Disable OAuth, use service account only
FORCE_SERVICE_ACCOUNT=true
GOOGLE_APPLICATION_CREDENTIALS=/Users/yitzchak/Documents/learn/presentation_project/sales-agent-labs/presgen-service-account2.json
```

**Then update slides_google.py line 58**:
```python
# Fallback to OAuth flow (skip if forced to use service account)
force_service_account = os.getenv("FORCE_SERVICE_ACCOUNT") == "true"
if force_service_account:
    raise RuntimeError("Service account required but not available")

force_consent = os.getenv("FORCE_OAUTH_CONSENT") == "1"
# ... rest of OAuth code ...
```

## Why OAuth Client is Invalid

Possible reasons:
1. **OAuth client was deleted** in Google Cloud Console
2. **Client secret was regenerated** (invalidates old credentials)
3. **OAuth consent screen not configured** properly
4. **Project was deleted/recreated** (invalidates old client IDs)

## Testing After Fix

**Test with service account**:
```bash
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/presgen-service-account2.json
export FORCE_SERVICE_ACCOUNT=true
python -c "from src.agent.slides_google import _load_credentials; creds = _load_credentials(); print('✅ Auth successful')"
```

**Expected output**:
```
Using service account: /path/to/presgen-service-account2.json
✅ Service account authenticated
✅ Auth successful
```

## Recommendation

**Use Option 1 (Service Account Only)** because:
- ✅ Service account is already set up
- ✅ No browser interaction needed
- ✅ Works in automated/headless environments
- ✅ OAuth client is broken anyway

If you need OAuth for user-specific features, create fresh OAuth credentials (Option 2).
