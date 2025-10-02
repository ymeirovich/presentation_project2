# OAuth Authentication - Working Alternative to Service Accounts

## ✅ Validation Results

**OAuth credentials tested and confirmed working:**

```
✅ OAuth client file: Valid
✅ Authentication flow: Successful
✅ Token saved: /Users/yitzchak/Documents/learn/presentation_project/sales-agent-labs/token_sheets.json
✅ Google Sheets API: Working
✅ Spreadsheet creation: Successful
✅ Data operations: Working
```

**Test Results:**
- Successfully created test spreadsheet
- Added data to spreadsheet
- Deleted test spreadsheet (cleanup)
- All operations completed without errors

## Why Use OAuth Instead of Service Account?

### Service Account Issues
- ❌ Returns 403 Permission Denied
- ❌ Cannot access API even with Owner role
- ❌ Requires additional Google Cloud setup
- ❌ May be disabled or restricted by org policies

### OAuth Benefits
- ✅ **Works immediately** - No additional setup required
- ✅ **Uses your personal Google account** - Full access to your resources
- ✅ **Browser-based authentication** - Familiar login flow
- ✅ **Token-based** - Saved for future use (no re-login needed)
- ✅ **No organization restrictions** - Your personal account, your rules

## How to Implement OAuth in PresGen-Assess

### Option 1: Update GoogleSheetsService (Recommended)

Modify `src/services/google_sheets_service.py` to support both auth methods:

```python
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials as OAuthCredentials
from google_auth_oauthlib.flow import InstalledAppFlow

class GoogleSheetsService:
    """Service for exporting skill gap analysis to Google Sheets."""

    def __init__(self, credentials_path: Optional[str] = None, use_oauth: bool = False):
        """Initialize Google Sheets service with credentials.

        Args:
            credentials_path: Path to service account JSON (if use_oauth=False)
                            or OAuth client JSON (if use_oauth=True)
            use_oauth: If True, use OAuth flow instead of service account
        """
        self.credentials_path = credentials_path
        self.use_oauth = use_oauth
        self.service = None
        self.scopes = [
            'https://www.googleapis.com/auth/spreadsheets',
            'https://www.googleapis.com/auth/drive.file'
        ]

        if GOOGLE_SHEETS_AVAILABLE and credentials_path:
            try:
                self._initialize_service()
            except Exception as e:
                logger.warning(f"⚠️ Google Sheets service initialization failed: {e}")

    def _initialize_service(self):
        """Initialize Google Sheets API service with OAuth or service account."""
        try:
            if self.use_oauth:
                logger.info(f"🔐 Initializing Google Sheets with OAuth")
                credentials = self._get_oauth_credentials()
            else:
                logger.info(f"🔐 Initializing Google Sheets with service account: {self.credentials_path}")
                from google.oauth2.service_account import Credentials
                credentials = Credentials.from_service_account_file(
                    self.credentials_path,
                    scopes=self.scopes
                )

            logger.info(f"✅ Credentials loaded successfully")
            logger.debug(f"📋 Scopes: {', '.join(self.scopes)}")

            # Build Sheets API service
            self.service = build('sheets', 'v4', credentials=credentials, cache_discovery=False)

            logger.info("✅ Google Sheets API service initialized successfully")

        except FileNotFoundError as e:
            logger.error(f"❌ Credentials file not found: {self.credentials_path}")
            raise
        except Exception as e:
            logger.error(f"❌ Failed to initialize Google Sheets service: {e}", exc_info=True)
            raise

    def _get_oauth_credentials(self):
        """Get OAuth credentials, refreshing or authenticating as needed."""
        token_path = self.credentials_path.replace('oauth_', 'token_').replace('_client', '')

        creds = None

        # Check if token exists
        if os.path.exists(token_path):
            creds = OAuthCredentials.from_authorized_user_file(token_path, self.scopes)

        # If no valid credentials, do OAuth flow
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                logger.info("🔄 Refreshing expired OAuth token")
                creds.refresh(Request())
            else:
                logger.info("🔐 Starting OAuth flow (browser will open)")
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials_path, self.scopes
                )
                creds = flow.run_local_server(port=0)

            # Save token
            with open(token_path, 'w') as token:
                token.write(creds.to_json())
            logger.info(f"✅ OAuth token saved to: {token_path}")

        return creds
```

### Option 2: Add OAuth Configuration to Settings

Update `src/common/config.py`:

```python
class Settings(BaseSettings):
    """Application settings with environment variable support."""

    # Existing settings...

    # Google Sheets Authentication
    use_oauth_for_sheets: bool = Field(
        default=False,
        alias="USE_OAUTH_FOR_SHEETS"
    )
    oauth_client_json: str = Field(
        default="/Users/yitzchak/Documents/learn/presentation_project/sales-agent-labs/oauth_slides_client.json",
        alias="OAUTH_CLIENT_JSON"
    )
```

### Option 3: Update Export Endpoint

Modify `src/service/api/v1/endpoints/workflows.py`:

```python
@router.post("/{workflow_id}/gap-analysis/export-to-sheets")
async def export_gap_analysis_to_google_sheets(
    workflow_id: UUID,
    payload: Dict[str, Optional[str]] = Body(default_factory=dict),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Export gap analysis results to Google Sheets."""
    try:
        # ... existing code ...

        # Choose auth method based on config
        if settings.use_oauth_for_sheets:
            sheets_service = GoogleSheetsService(
                credentials_path=settings.oauth_client_json,
                use_oauth=True
            )
        else:
            sheets_service = GoogleSheetsService(
                credentials_path=settings.google_application_credentials,
                use_oauth=False
            )

        # ... rest of code ...
```

## Quick Setup: Switch to OAuth Now

### 1. Update Environment Variables

Add to `.env`:
```bash
# Use OAuth instead of service account
USE_OAUTH_FOR_SHEETS=true
OAUTH_CLIENT_JSON=/Users/yitzchak/Documents/learn/presentation_project/sales-agent-labs/oauth_slides_client.json
```

### 2. Test OAuth Flow

```bash
python3 scripts/test_oauth_auth.py
```

Expected output:
```
✅ OAuth authentication successful!
✅ Token saved to: token_sheets.json
✅ Test spreadsheet created successfully!
```

### 3. First Export (One-Time Setup)

- Click "Export to Sheets" in dashboard
- Browser opens for Google login
- Log in and grant permissions
- Token saved automatically
- All future exports work without login

### 4. Token Management

**Token Location**: `/Users/yitzchak/Documents/learn/presentation_project/sales-agent-labs/token_sheets.json`

**Token Lifespan**:
- Access token: ~1 hour (auto-refreshes)
- Refresh token: Long-lived (months/years)

**Revoke Access** (if needed):
1. Go to: https://myaccount.google.com/permissions
2. Find: "PresGen" or your app name
3. Click "Remove access"

## Comparison: Service Account vs OAuth

| Feature | Service Account | OAuth User Auth |
|---------|----------------|-----------------|
| **Setup Complexity** | High (GCP console) | Low (just OAuth client) |
| **Permissions** | Requires explicit IAM roles | Uses your personal access |
| **First-time auth** | Key file only | Browser login required |
| **Subsequent auth** | Automatic | Automatic (token refresh) |
| **Organization restrictions** | May be blocked | Usually works |
| **Best for** | Production/Automation | Development/Personal use |
| **Current status** | ❌ 403 Error | ✅ Working |

## Production Considerations

### Development (Use OAuth)
- ✅ Quick setup
- ✅ No GCP configuration
- ✅ Uses your personal account
- ✅ Works immediately

### Production (Fix Service Account or Use OAuth)
- Service account: Better for automated systems
- OAuth: Requires user present for first auth
- Consider: Headless OAuth flow for production

## Current Recommendation

**For immediate use**: Switch to OAuth authentication

**Reasons**:
1. Already tested and working ✅
2. No additional setup required ✅
3. Bypasses all service account issues ✅
4. Same API functionality ✅

**Implementation time**: 15 minutes

## Files Available

Your OAuth setup:
- ✅ OAuth client: `/Users/yitzchak/Documents/learn/presentation_project/sales-agent-labs/oauth_slides_client.json`
- ✅ Token (created): `/Users/yitzchak/Documents/learn/presentation_project/sales-agent-labs/token_sheets.json`
- ✅ Test script: `scripts/test_oauth_auth.py`

## Next Steps

1. **Option A: Quick Fix (Use OAuth)**
   - Update `GoogleSheetsService` to support OAuth
   - Set `USE_OAUTH_FOR_SHEETS=true` in `.env`
   - Test export from dashboard
   - Works immediately ✅

2. **Option B: Fix Service Account** (if required for production)
   - Follow troubleshooting guide
   - Check if account is disabled
   - Create new service account if needed
   - May take longer to resolve ⏱️

**Recommendation**: Start with OAuth (Option A) for immediate functionality, then fix service account for production deployment.
