# Bug Fix: File Upload Not Appearing in UI

## Date
October 19, 2025

## Problem Statement
Files uploaded to certification profiles (specifically ACC ICF Certification) were not appearing in the Resources section of the UI, even though the upload appeared to succeed.

## Root Cause Analysis

### Issue 1: Invalid File ID Format
- **Mock Storage** generated file IDs like `file_1760861521466_qti9d31m1`
- **Backend Database** requires proper UUID format (e.g., `2400125a-ab49-42bd-ac4a-041573364f70`)
- Backend's `_load_from_database()` method failed silently when trying to convert invalid UUIDs

### Issue 2: No Database Persistence
- Files uploaded via frontend Next.js API routes used **mock storage** as fallback
- Mock storage saved files to `/tmp/presgen-mock-storage.json` (in-memory + file)
- Files were **NEVER** saved to backend `knowledge_base_documents` database table
- Frontend requested files → Backend responded HTTP 200 with empty list
- Mock fallback never triggered because backend didn't return an error

### Issue 3: Wrong Backend URL
- Frontend upload route called: `/api/v1/presgen-assess/files`
- Correct endpoint should be: `/api/v1/presgen-assess/files/upload`
- Backend returned 404, triggering mock storage fallback

### Issue 4: Mock Storage Design Flaws
- Mock storage was single-process only (not shared across Next.js serverless functions)
- File persistence to `/tmp/` unreliable across deployments
- Creates sync issues between frontend state and backend database
- No single source of truth

## Immediate Workaround Applied
Manually inserted 5 existing files into `knowledge_base_documents` table with proper UUIDs:
```sql
INSERT INTO knowledge_base_documents (id, certification_profile_id, original_filename, ...)
VALUES
('2400125aab4942bdac4a041573364f70', '36b361410f79449fa6bfb2ec59fddcd1', 'ACC Exam Preparation Study Guide.docx', ...),
...
```

This made the existing 5 files appear, but **new uploads still fail**.

---

## Permanent Solution Implementation Plan

### Phase 1: Fix Backend Upload Endpoint ✅ PENDING
**File:** `presgen-assess/src/service/api/v1/endpoints/file_management.py`

**Tasks:**
1. Verify `/upload` route generates proper UUIDs
2. Ensure database persistence works
3. Fix any async/database session issues
4. Add comprehensive logging

### Phase 2: Remove Mock Storage from Frontend ✅ PENDING
**Files to Update:**

#### A. `src/app/api/presgen-assess/files/upload/route.ts`
- Fix backend URL: Add `/upload` to path
- Remove mock storage fallback (lines 43-75)
- Remove mock storage imports

#### B. `src/app/api/presgen-assess/files/profile/route.ts`
- Remove mock storage fallback (lines 45-58)
- Return empty array on backend error

#### C. `src/app/api/presgen-assess/files/[fileId]/route.ts`
- Remove mock storage fallback for DELETE operation
- Return proper errors

#### D. `src/app/api/presgen-assess/files/[fileId]/download/route.ts`
- Remove mock storage fallback
- Return proper errors

#### E. `src/app/api/presgen-assess/files/debug/route.ts`
- **DELETE** - Only used for debugging mock storage

### Phase 3: Remove Mock Storage Infrastructure ✅ PENDING
1. Delete `src/lib/mock-file-storage.ts`
2. Delete `/tmp/presgen-mock-storage.json`
3. Remove all imports

### Phase 4: Testing ✅ PENDING
- Upload new file → appears immediately
- Refresh page → file persists
- Delete file → removed from UI
- Download file → works correctly

---

## Database Schema Reference

### `knowledge_base_documents` Table
```sql
CREATE TABLE knowledge_base_documents (
    id UUID NOT NULL,                           -- Proper UUID format required
    certification_profile_id UUID NOT NULL,     -- Links to certification profile
    original_filename VARCHAR(500) NOT NULL,
    stored_path TEXT NOT NULL,
    document_type VARCHAR(50) NOT NULL,         -- MIME type
    content_classification VARCHAR(50) NOT NULL, -- exam_guide|transcript|supplemental
    file_size_bytes INTEGER NOT NULL,
    processing_status VARCHAR(50),              -- pending|processing|completed|failed
    chunk_count INTEGER,
    embedding_model VARCHAR(100),
    processed_at DATETIME,
    checksum VARCHAR(64),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id)
);
```

### UUID Format Examples
- ✅ **Correct:** `2400125a-ab49-42bd-ac4a-041573364f70` (with dashes)
- ✅ **Correct:** `2400125aab4942bdac4a041573364f70` (without dashes - SQLite accepts both)
- ❌ **Wrong:** `file_1760861521466_qti9d31m1` (mock storage format)

---

## Architecture Decision: Single Source of Truth

### Before (PROBLEMATIC)
```
Upload Flow:
Frontend → Next.js API → Backend (fails) → Mock Storage → /tmp/presgen-mock-storage.json
                                                         ↓
                                                    UI shows file

Retrieval Flow:
Frontend → Next.js API → Backend → Database (empty) → Returns []
                                                     ↓
                                            UI shows no files (Mock never triggered!)
```

### After (CORRECT)
```
Upload Flow:
Frontend → Next.js API → Backend → Database → knowledge_base_documents table
                                             ↓
                                        Returns file metadata
                                             ↓
                                        UI shows file

Retrieval Flow:
Frontend → Next.js API → Backend → Database → knowledge_base_documents table
                                             ↓
                                        Returns file list
                                             ↓
                                        UI shows files
```

**Key Principle:** Backend database is the **ONLY** source of truth. No fallbacks, no sync issues.

---

## Files Modified (To Be Completed)

### Backend (Python)
- [ ] `presgen-assess/src/service/api/v1/endpoints/file_management.py` - Verify upload endpoint

### Frontend (TypeScript)
- [ ] `presgen-ui/src/app/api/presgen-assess/files/upload/route.ts` - Fix URL, remove mock
- [ ] `presgen-ui/src/app/api/presgen-assess/files/profile/route.ts` - Remove mock fallback
- [ ] `presgen-ui/src/app/api/presgen-assess/files/[fileId]/route.ts` - Remove mock fallback
- [ ] `presgen-ui/src/app/api/presgen-assess/files/[fileId]/download/route.ts` - Remove mock fallback
- [ ] `presgen-ui/src/app/api/presgen-assess/files/debug/route.ts` - DELETE FILE
- [ ] `presgen-ui/src/lib/mock-file-storage.ts` - DELETE FILE

### Database
- [x] Manual insert of 5 existing ACC ICF files (COMPLETED)

---

## Testing Checklist

### Before Implementation
- [x] Existing 5 files appear in ACC ICF profile
- [ ] New file upload FAILS to appear
- [x] Mock storage has files in `/tmp/presgen-mock-storage.json`
- [x] Database has 5 ACC ICF files with proper UUIDs

### After Implementation
- [ ] Upload new file → appears immediately in UI
- [ ] Refresh page → uploaded files persist
- [ ] Delete file → removed from UI and database
- [ ] Download file → file downloads correctly
- [ ] Backend down → proper error message (no silent failures)
- [ ] No mock storage files remain
- [ ] All file IDs are proper UUIDs

---

## Success Criteria
1. ✅ All new file uploads appear in UI immediately
2. ✅ All file IDs use proper UUID format
3. ✅ Files persist in backend database
4. ✅ No mock storage code remains
5. ✅ Clear error handling when backend unavailable

---

## Related Issues
- Mock storage was introduced as temporary development fallback
- Should have been removed before production use
- Caused hidden sync bugs between frontend and backend

## Lessons Learned
1. **Single Source of Truth:** Always use one authoritative data source
2. **Fallbacks Must Sync:** If using fallbacks, they must sync with primary storage
3. **UUID Validation:** Enforce proper UUID format at boundaries
4. **Integration Testing:** Test full end-to-end flows, not just unit tests
5. **Remove Temp Code:** Development fallbacks should be removed before deployment
