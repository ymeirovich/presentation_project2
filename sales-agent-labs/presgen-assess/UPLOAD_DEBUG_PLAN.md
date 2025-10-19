# Upload Endpoint HTTP 500 Debug Plan

## Possible Causes for HTTP 500 Errors

### 1. **Database Session Issues** (Most Likely)
- ✅ `AsyncSession` from `get_db()` dependency may not be properly configured
- ✅ Database queries might be using synchronous `.query()` instead of async
- ✅ Session might not be committed/closed properly
- ✅ File registry uses synchronous database operations with async endpoint

### 2. **File Upload Service Issues**
- ⚠️ `save_uploaded_file()` is async but may have blocking operations
- ⚠️ File path directories may not exist (`uploads/exam_guides`, etc.)
- ⚠️ File permissions issues when writing to disk
- ⚠️ `aiofiles` import may be missing or not installed

### 3. **File Registry Issues**
- ⚠️ `file_registry.register_file()` uses synchronous DB operations
- ⚠️ UUID conversion issues between string and UUID object
- ⚠️ `_save_to_database()` may fail silently
- ⚠️ Database schema mismatch (e.g., missing columns)

### 4. **Import/Dependency Issues**
- ⚠️ Missing imports (aiofiles, uuid, sqlalchemy)
- ⚠️ ChromaDB initialization failures
- ⚠️ Document processor not properly initialized

### 5. **Resource Type Validation**
- ⚠️ ResourceType enum may not match form data
- ⚠️ Invalid resource_type values being passed

### 6. **Background Task Issues**
- ⚠️ `process_file_background()` function may have errors
- ⚠️ Collection manager not initialized
- ⚠️ Even though `process_immediately=false`, background task setup might fail

---

## Enhanced Logging Plan

### Step 1: Add Entry Point Logging
```python
@router.post("/upload", response_model=FileUploadResponse)
async def upload_file(...):
    print("="*80)
    print("🔵 UPLOAD ENDPOINT CALLED")
    print(f"📄 File: {file.filename if file else 'None'}")
    print(f"📋 Profile ID: {cert_profile_id}")
    print(f"🏷️ Resource Type: {resource_type}")
    print(f"⚡ Process Immediately: {process_immediately}")
    print("="*80)
```

### Step 2: Add File Service Logging
```python
async def save_uploaded_file(...):
    print(f"📥 Saving file: {file.filename}")
    print(f"📁 File ID: {file_id}")
    print(f"💾 Storage path: {file_path}")

    try:
        # ... existing code
        print(f"✅ File saved successfully: {file_size} bytes")
    except Exception as e:
        print(f"❌ File save failed: {type(e).__name__}: {str(e)}")
        raise
```

### Step 3: Add Registry Logging
```python
def register_file(self, file_metadata: FileMetadata):
    print(f"📝 Registering file: {file_metadata.file_id}")
    print(f"📋 Profile: {file_metadata.cert_profile_id}")

    try:
        self._save_to_database(file_metadata)
        print(f"✅ File registered in database")
    except Exception as e:
        print(f"❌ Registry failed: {type(e).__name__}: {str(e)}")
        raise
```

### Step 4: Add Exception Catching
```python
try:
    # Main upload logic
    ...
except HTTPException as he:
    print(f"❌ HTTP Exception: {he.status_code} - {he.detail}")
    raise
except Exception as e:
    print(f"❌ UNEXPECTED ERROR: {type(e).__name__}")
    print(f"❌ Error message: {str(e)}")
    import traceback
    traceback.print_exc()
    raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")
```

---

## Implementation Plan

### Phase 1: Add Comprehensive Logging
1. Add entry point logging to track function entry
2. Add logging before each major operation:
   - File validation
   - File save
   - File registration
   - Background task scheduling
3. Add exception logging with full stack traces
4. Log all database operations

### Phase 2: Fix Known Issues
1. Ensure upload directories exist
2. Fix async/sync database mixing
3. Add proper error handling
4. Validate ResourceType enum conversion

### Phase 3: Test & Debug
1. Trigger upload with test file
2. Review console logs for exact error
3. Fix identified issue
4. Repeat until successful

### Phase 4: Verify Database Persistence
1. Check `knowledge_base_documents` table after upload
2. Verify file appears in UI
3. Test end-to-end flow

---

## Quick Diagnostic Commands

```bash
# Check if upload directories exist
ls -la /Users/yitzchak/Documents/learn/presentation_project/sales-agent-labs/presgen-assess/uploads/

# Check database schema
sqlite3 test_database.db ".schema knowledge_base_documents"

# Check recent backend logs
tail -100 src/logs/presgen_assess_combined.log | grep -A 10 "upload\|ERROR"

# Check if aiofiles is installed
python3 -c "import aiofiles; print('aiofiles OK')"

# Test resource type enum
python3 -c "from src.service.file_upload_service import ResourceType; print(ResourceType.SUPPLEMENTAL)"
```

---

## Expected Log Output (Success)

```
================================================================================
🔵 UPLOAD ENDPOINT CALLED
📄 File: test-upload.txt
📋 Profile ID: 36b36141-0f79-449f-a6bf-b2ec59fddcd1
🏷️ Resource Type: supplemental
⚡ Process Immediately: False
================================================================================
📥 Saving file: test-upload.txt
📁 File ID: a1b2c3d4-e5f6-7890-abcd-ef1234567890
💾 Storage path: uploads/supplemental/a1b2c3d4-e5f6-7890-abcd-ef1234567890.txt
✅ File saved successfully: 37 bytes
📝 Registering file: a1b2c3d4-e5f6-7890-abcd-ef1234567890
📋 Profile: 36b36141-0f79-449f-a6bf-b2ec59fddcd1
✅ File registered in database
✅ UPLOAD SUCCESSFUL
```

---

## Next Steps
1. Implement enhanced logging in upload endpoint
2. Run test upload and capture logs
3. Identify exact failure point
4. Fix issue and verify
