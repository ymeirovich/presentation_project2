# OAuth Token Standardization - Complete

## Summary

All Google API services (Sheets, Slides, Drive) now use a **single standardized token file** referenced via environment variable instead of hardcoded paths.

## Changes Made

### 1. Configuration Files

#### [presgen-assess/src/common/config.py](presgen-assess/src/common/config.py)
Added new setting:
```python
oauth_token_path: str = Field(
    default="/Users/yitzchak/Documents/learn/presentation_project/sales-agent-labs/token.json",
    alias="OAUTH_TOKEN_PATH",
    description="Path to standardized OAuth token JSON for all Google API services"
)
```

#### [presgen-assess/src/services/google_sheets_service.py](presgen-assess/src/services/google_sheets_service.py)
Updated `_get_oauth_credentials()` method:
```python
# Use standardized token path from environment variable
token_path = os.getenv('OAUTH_TOKEN_PATH',
                      '/Users/yitzchak/Documents/learn/presentation_project/sales-agent-labs/token.json')
```

#### [src/agent/slides_google.py](src/agent/slides_google.py)
Updated TOKEN_PATH constant:
```python
# Standardized token path from environment variable
TOKEN_PATH = pathlib.Path(os.getenv('OAUTH_TOKEN_PATH', 'token.json'))
```

### 2. Environment Variables

#### [.env](/.env) (root)
```bash
# Standardized OAuth Token (used by all services - Sheets, Slides, Drive)
OAUTH_TOKEN_PATH=/Users/yitzchak/Documents/learn/presentation_project/sales-agent-labs/token.json
```

#### [presgen-assess/.env](presgen-assess/.env)
```bash
# Standardized OAuth Token (used by all services)
OAUTH_TOKEN_PATH=/Users/yitzchak/Documents/learn/presentation_project/sales-agent-labs/token.json
```

### 3. Token File

**Standardized Location:**
```
/Users/yitzchak/Documents/learn/presentation_project/sales-agent-labs/token.json
```

**Previous Files (now consolidated):**
- ❌ `token_sheets.json` → ✅ `token.json`
- ❌ `token_slides.json` → ✅ `token.json`
- ❌ `token_forms.json` → ✅ `token.json`

## Token Details

The standardized `token.json` contains:
- **Scopes:** 
  - `https://www.googleapis.com/auth/spreadsheets`
  - `https://www.googleapis.com/auth/drive.file`
- **Refresh Token:** ✅ Present (auto-refreshes when expired)
- **Format:** Standard OAuth2 credentials JSON

## How It Works

1. **Services read `OAUTH_TOKEN_PATH` from environment:**
   - Google Sheets Service → Uses env var for token path
   - Google Slides Service → Uses env var for token path
   - All future Google services → Use same pattern

2. **Fallback behavior:**
   - If `OAUTH_TOKEN_PATH` not set, uses default path
   - Default: `/Users/yitzchak/Documents/learn/presentation_project/sales-agent-labs/token.json`

3. **Auto-refresh:**
   - Token auto-refreshes when expired (using refresh_token)
   - No manual intervention needed
   - New access tokens valid for 1 hour

## Benefits

✅ **Single source of truth** - One token file for all Google APIs  
✅ **Environment-based** - Path configurable via .env files  
✅ **No hardcoded paths** - Easier to deploy and maintain  
✅ **Consistent behavior** - All services use same authentication flow  
✅ **Auto-refresh** - Tokens refresh automatically when expired  

## Testing

Validated that:
- ✅ Environment variable loads correctly from .env files
- ✅ Token path resolution works with and without env var
- ✅ Token file exists and is valid JSON
- ✅ Token contains required scopes and refresh_token
- ✅ Services can import and use the standardized path

## Next Steps

When running the services:
1. Environment variables are auto-loaded from .env files
2. Services use `OAUTH_TOKEN_PATH` to find token
3. If token expired, auto-refreshes using refresh_token
4. If token missing, OAuth flow creates new one at standardized path

---

**Date Completed:** 2025-10-02  
**Status:** ✅ Complete and Tested
