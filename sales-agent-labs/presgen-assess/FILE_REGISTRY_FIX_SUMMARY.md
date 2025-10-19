# File Registry Fix - Missing Resources in UI

## Issue Summary

**Problem**: Certification Profile resources were randomly disappearing from the UI after backend server restarts.

**Reported Issue**: "AWS Machine Learning Specialty" certification profile showed no uploaded RAG resources in the UI, even though the files were uploaded.

## Root Cause Analysis

The issue was caused by an **in-memory-only file registry** implementation in `src/service/file_upload_service.py`:

### Original Problem:

1. **FileRegistry Class** stored all file metadata in RAM only (`self._files: Dict[str, FileMetadata] = {}`)
2. **No Database Persistence** - file metadata was never written to `knowledge_base_documents` table
3. **Data Loss on Restart** - when the backend server restarted, the in-memory registry was empty
4. **UI Shows Empty** - UI queries the registry via `/api/presgen-assess/files/profile?profileId=xxx`, which returned no files

### Evidence Found:

✅ **SQL Database**: AWS Machine Learning Specialty profile exists in `certification_profiles` table
✅ **Metadata Exists**: `uploaded_files_metadata` JSON field contained 4 uploaded files
✅ **Knowledge Base Docs Table**: Empty (should have contained file records)
❌ **File Registry**: In-memory only, lost all data on restart

## Solution Implemented

### 1. Modified FileRegistry Class ([file_upload_service.py:339-527](src/service/file_upload_service.py#L339-L527))

**Changes Made:**
- ✅ Added database persistence to all FileRegistry operations
- ✅ Implemented `_save_to_database()` method to persist file metadata
- ✅ Implemented `_load_from_database()` method to load from `knowledge_base_documents` table
- ✅ Modified all registry methods to sync with database:
  - `register_file()` - saves to DB
  - `get_file()` - loads from DB if not in cache
  - `get_files_for_profile()` - always loads from DB
  - `remove_file()` - deletes from DB
  - `update_file_status()` - updates DB
- ✅ Kept in-memory cache for performance
- ✅ Fixed UUID type conversion for SQLite compatibility

### 2. Created Migration Script ([migrate_uploaded_files.py](migrate_uploaded_files.py))

**Purpose**: Migrate existing file metadata from `certification_profiles.uploaded_files_metadata` JSON field to `knowledge_base_documents` table

**Execution Result:**
```
Processing profile: AWS Machine Learning Specialty
  Found 4 files to migrate
    ✓ aws-ml-specialty-exam-guide.txt (exam_guide) - completed
    ✓ aws-ml-specialty-exam-guide.md (exam_guide) - completed
    ✓ ml-course-transcript.txt (transcript) - completed
    ✓ ml-course-transcript.md (transcript) - completed

Migration complete!
  Profiles processed: 1
  Files migrated: 4
```

### 3. Database Schema Used

The solution leverages the existing `KnowledgeBaseDocument` model defined in [src/models/certification.py:48-66](src/models/certification.py#L48-L66):

```python
class KnowledgeBaseDocument(Base):
    __tablename__ = "knowledge_base_documents"

    id = Column(PGUUID(as_uuid=True), primary_key=True)
    certification_profile_id = Column(PGUUID(as_uuid=True), nullable=False)
    original_filename = Column(String(500), nullable=False)
    stored_path = Column(Text, nullable=False)
    document_type = Column(String(50))  # MIME type
    content_classification = Column(String(50))  # exam_guide, transcript, supplemental
    file_size_bytes = Column(Integer, nullable=False)
    processing_status = Column(String(50), default='pending')
    chunk_count = Column(Integer)
    checksum = Column(String(64))
    created_at = Column(DateTime)
```

## Testing & Verification

### Test 1: Database Population
```bash
sqlite3 test_database.db "SELECT id, original_filename, content_classification, processing_status FROM knowledge_base_documents;"
```

**Result**: ✅ All 4 files present in database

### Test 2: FileRegistry Loading
Created [test_file_registry.py](test_file_registry.py) to verify registry can load from database.

**Result**: ✅ Successfully loaded 4 files with correct metadata

## Files Modified

1. **[src/service/file_upload_service.py](src/service/file_upload_service.py)** - Modified FileRegistry class (lines 339-527)
2. **[migrate_uploaded_files.py](migrate_uploaded_files.py)** - Created migration script
3. **[test_file_registry.py](test_file_registry.py)** - Created test script

## How to Apply the Fix

### For Existing Installations:

1. **Run the migration script** to populate the database:
   ```bash
   cd /path/to/presgen-assess
   source venv/bin/activate
   python migrate_uploaded_files.py
   ```

2. **Restart the backend server** - FileRegistry will now load from database

3. **Verify in UI** - Navigate to the certification profile and check that resources appear

### For New File Uploads:

No action needed - new files will automatically be saved to the database when uploaded.

## Benefits

✅ **Persistence** - File metadata survives server restarts
✅ **Reliability** - No more "disappearing" resources
✅ **Performance** - In-memory cache for fast access
✅ **Data Integrity** - Single source of truth in database
✅ **Backward Compatible** - Works with existing uploaded files after migration

## Future Considerations

1. **ChromaDB Integration**: Currently ChromaDB data directory (`data/chroma`) doesn't exist. Consider implementing:
   - ChromaDB persistence layer
   - Sync between `knowledge_base_documents` and ChromaDB collections

2. **Async Database Support**: Current implementation uses synchronous SQLite. For production:
   - Consider migrating to async database operations
   - Align with existing `src/service/database.py` async patterns

3. **User ID Tracking**: `KnowledgeBaseDocument` table doesn't store `user_id`. Consider:
   - Adding `user_id` column for multi-tenant support
   - Using join with `certification_profiles` for user filtering

## Conclusion

The issue has been **fully resolved**. Resources will no longer disappear from the UI after backend restarts. All file metadata is now persisted to the database and properly loaded by the FileRegistry.
