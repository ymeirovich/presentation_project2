# Complete Fix for UI Not Loading RAG Resources

## Problem Summary

The UI doesn't load RAG resources even after clicking refresh because the **file_management router was never registered** in the API router.

## Root Causes Identified

### 1. ✅ File Registry In-Memory Only (FIXED)
- **Problem**: FileRegistry stored data only in RAM, lost on restart
- **Fix**: Modified to persist to `knowledge_base_documents` table
- **Status**: ✅ Complete - tested and working

### 2. ❌ File Management Router Not Registered (FIXED - NEEDS RESTART)
- **Problem**: `file_management.router` was never added to main API router
- **Fix**: Added to `/src/service/api/v1/router.py`
- **Status**: ⚠️ Code fixed, but **backend needs restart**

### 3. ⚠️ Database Empty (FIXED)
- **Problem**: `knowledge_base_documents` table was empty
- **Fix**: Ran migration script - 4 files migrated successfully
- **Status**: ✅ Complete

## Files Modified

### 1. [src/service/file_upload_service.py](src/service/file_upload_service.py)
**Changes**: Database-backed FileRegistry (lines 339-527)
- Added `_save_to_database()` method
- Added `_load_from_database()` method
- Updated all methods to sync with database

### 2. [src/service/api/v1/router.py](src/service/api/v1/router.py) ⚠️ **NEW**
**Changes**:
```python
# Line 20: Added import
from src.service.api.v1.endpoints import (
    ...
    file_management  # NEW
)

# Lines 116-121: Registered router
api_router.include_router(
    file_management.router,
    prefix="/presgen-assess",  # Matches UI path
    tags=["file_management", "rag-resources"]
)
```

### 3. [migrate_uploaded_files.py](migrate_uploaded_files.py)
**Changes**: Created migration script - already executed successfully

## How to Apply the Fix

### Step 1: Restart the Backend Server ⚠️ **CRITICAL**

The code changes are in place, but the backend server must be restarted to load them.

```bash
# Navigate to presgen-assess directory
cd /Users/yitzchak/Documents/learn/presentation_project/sales-agent-labs/presgen-assess

# Stop the current backend server (Ctrl+C or kill process)

# Restart with:
source venv/bin/activate
python -m uvicorn src.service.app:app --host 0.0.0.0 --port 8000 --reload
```

### Step 2: Verify the Endpoint is Available

Test the endpoint manually:

```bash
curl http://localhost:8000/api/v1/presgen-assess/files/profile/455dae60-065c-4038-b3df-6d769b955dbb
```

**Expected Response**:
```json
{
  "files": [
    {
      "file_id": "ad4276da-cf72-40c3-a8d6-1a9b985fee36",
      "original_filename": "aws-ml-specialty-exam-guide.txt",
      "resource_type": "exam_guide",
      ...
    },
    ...
  ],
  "total_count": 4
}
```

**Current Response** (before restart):
```json
{
  "detail": "Not Found"
}
```

### Step 3: Test in UI

1. Navigate to AWS Machine Learning Specialty certification profile
2. Click "Refresh" or reload the page
3. RAG resources should now appear (4 files)

## Complete API Path Breakdown

### UI Request Path:
```
Frontend → /api/presgen-assess/files/profile?profileId=455dae60-...
  ↓
Next.js API Route → /api/v1/presgen-assess/files/profile/455dae60-...
  ↓
Backend FastAPI
```

### Backend Route Resolution:
```
http://localhost:8000/api/v1/presgen-assess/files/profile/{cert_profile_id}
                       │         │           │      │
                       │         │           │      └─ Endpoint: /profile/{cert_profile_id}
                       │         │           └──────── Router prefix: /files
                       │         └──────────────────── API router prefix: /presgen-assess
                       └────────────────────────────── App prefix: /api/v1
```

## Expected Database State

### certification_profiles
```sql
SELECT name, LENGTH(assessment_prompt), LENGTH(presentation_prompt)
FROM certification_profiles
WHERE id = '455dae60065c4038b3df6d769b955dbb';

-- AWS Machine Learning Specialty | 702 | 10647
```

### knowledge_base_documents
```sql
SELECT COUNT(*) FROM knowledge_base_documents
WHERE certification_profile_id = '455dae60-065c-4038-b3df-6d769b955dbb';

-- Expected: 4 rows
```

## Troubleshooting

### Issue: Still getting 404 after restart

**Check 1**: Verify router is imported
```bash
grep "file_management" src/service/api/v1/router.py
# Should show: from src.service.api.v1.endpoints import (... file_management ...)
# Should show: api_router.include_router(file_management.router, ...)
```

**Check 2**: Check FastAPI docs
Visit: `http://localhost:8000/docs`
Look for `/api/v1/presgen-assess/files` endpoints

**Check 3**: Check startup logs
```bash
# Should see:
INFO: Application startup complete.
```

### Issue: 401 Unauthorized

The endpoint requires authentication. Options:

**Option A**: Get a demo token
```bash
curl -X POST http://localhost:8000/api/v1/auth/demo-token
# Returns: {"access_token": "...", "token_type": "bearer"}
```

**Option B**: Disable auth for this endpoint (development only)
Remove `current_user: User = Depends(get_current_user)` from the endpoint

### Issue: Empty files list even though endpoint works

**Check**: Is file_registry loading from database?
```bash
cd /Users/yitzchak/Documents/learn/presentation_project/sales-agent-labs/presgen-assess
source venv/bin/activate
python test_file_registry.py
# Should show: Found 4 files
```

## Summary

### What Was Wrong:
1. ❌ File registry was in-memory only → **FIXED**
2. ❌ Database was empty → **FIXED** (migration run)
3. ❌ Router not registered → **FIXED** (code updated)
4. ⚠️ Backend not restarted → **ACTION NEEDED**

### What Needs to Happen:
1. **Restart the backend server** with the updated code
2. Verify endpoint returns 200 OK with 4 files
3. Test in UI - resources should load

### Test Commands:
```bash
# 1. Test endpoint
curl http://localhost:8000/api/v1/presgen-assess/files/profile/455dae60-065c-4038-b3df-6d769b955dbb

# 2. Test file registry directly
python test_file_registry.py

# 3. Check database
sqlite3 test_database.db "SELECT COUNT(*) FROM knowledge_base_documents;"
# Should return: 4
```

---

**The fix is complete. Just needs backend restart to take effect!**
