# File Upload "Failed" Status Analysis

**Date:** 2025-11-04
**Issue:** Files show "Failed" status in UI despite successful upload logs
**File:** AWS-Certified-Machine-Learning-Engineer-Associate_Exam-Guide (1).pdf
**File ID:** `2ae84cad-5d14-4f39-927e-9d99703eed62`

---

## Problem Summary

Files uploaded via the Certification Resource Manager show **"Failed"** status (in red) in the UI, even though the backend logs show successful upload and database registration.

### What the Logs Show (✅ All Successful)

```
✅ FileUploadService: File saved successfully
✅ Step 1 Complete: File saved with ID: 2ae84cad-5d14-4f39-927e-9d99703eed62
✅ Step 2 Complete: File registered in database
⚙️ Step 3: Scheduling background processing...
✅ Step 3 Complete: Background task scheduled
✅ UPLOAD SUCCESSFUL: 2ae84cad-5d14-4f39-927e-9d99703eed62
```

### What the UI Shows (❌ Failed)

![Screenshot](Screenshot 2025-11-04 at 15.10.44.png)

Both files show:
- ⭕ Red "Failed" badge
- File details are correct (name, size, type)
- Download and delete buttons still available

---

## Root Cause Analysis

### Issue 1: Background Processing Not Executing

**Code:** [file_management.py:159-168](src/service/api/v1/endpoints/file_management.py#L159-L168)

```python
if process_immediately:
    print("⚙️ Step 3: Scheduling background processing...")
    background_tasks.add_task(
        process_file_background,
        file_metadata,
        cert_profile_slug,
        bundle_version,
        {},  # domain_mappings
        cert_profile.name
    )
    print("✅ Step 3 Complete: Background task scheduled")
```

**Problem:** The background task `process_file_background` is **scheduled** but we see no logs from it actually **running**.

**Expected logs (missing):**
- Vector database processing
- Chunk creation
- Status updates

**Actual logs:** None - the function never executes or fails silently.

### Issue 2: In-Memory File Registry

**Code:** [file_management.py:20](src/service/api/v1/endpoints/file_management.py#L20)

```python
from src.service.file_upload_service import file_registry
```

The `file_registry` is an **in-memory** data structure. It tracks files but:
- ❌ Not persisted to database
- ❌ Lost on container restart
- ❌ Not shared across API instances
- ❌ UI cannot query it

### Issue 3: No Database Record Created

**Investigation:** Queried `knowledge_base_documents` table:

```bash
# No record found for file_id: 2ae84cad-5d14-4f39-927e-9d99703eed62
```

**Expected:**
- File metadata in `knowledge_base_documents` table
- `processing_status` field showing "pending", "processing", or "completed"

**Actual:**
- No database record exists
- File only tracked in-memory

### Issue 4: UI Default Status

**Hypothesis:** The UI is likely:
1. Checking for a database record after upload
2. Not finding any record
3. Defaulting to "Failed" status

**Or:**
4. Checking an API endpoint that returns the in-memory registry
5. Initial status is "pending"
6. Background processing fails silently
7. Status never updates to "completed"
8. UI shows "Failed" after timeout or on refresh

---

## What IS Working

✅ **File Upload:**
- File is saved to disk
- Path: `uploads/exam_guides/2ae84cad-5d14-4f39-927e-9d99703eed62.pdf`
- Size: 219,817 bytes
- Hash calculated correctly

✅ **In-Memory Registry:**
- File added to `file_registry._files` dict
- Metadata cached in memory

✅ **API Response:**
- Upload endpoint returns 200 OK
- Response includes correct file_id and metadata

---

## What is NOT Working

❌ **Background Processing:**
- No logs from `process_file_background` function
- No vector database ingestion
- No chunk creation
- No status updates

❌ **Database Persistence:**
- File not in `knowledge_base_documents` table
- No processing status tracking
- No chunk count

❌ **Status Updates:**
- UI shows "Failed" instead of "Processing" or "Completed"
- No mechanism to update UI after background processing

---

## Code Flow Analysis

### Upload Flow

```
1. POST /files/upload
   ├─> ✅ file_upload_service.save_uploaded_file()
   │    └─> File written to uploads/exam_guides/
   │
   ├─> ✅ file_registry.register_file()
   │    └─> Added to in-memory dict
   │
   ├─> ⚙️ background_tasks.add_task(process_file_background)
   │    └─> Scheduled (but not executing?)
   │
   └─> ✅ Return FileUploadResponse
        └─> processing_status: "pending"
```

### Background Processing Flow (Expected but NOT Happening)

```
process_file_background()
   ├─> Get ChromaDB collection manager
   ├─> Ensure collection exists
   ├─> process_uploaded_file()
   │    ├─> Extract text/parse document
   │    ├─> Create chunks
   │    ├─> Generate embeddings
   │    └─> Store in vector DB
   ├─> Update file_registry status
   │    └─> "completed" or "failed"
   └─> ❌ THIS NEVER RUNS
```

### UI Status Check Flow (Hypothesis)

```
UI Component
   ├─> GET /files/list or /files/{file_id}
   ├─> Receives processing_status: "pending"
   ├─> Waits for status update
   ├─> No update received
   └─> Shows "Failed" (timeout or default)
```

---

## Debugging Steps

### Step 1: Check if Background Tasks are Running

```bash
docker logs presgen-assess 2>&1 | grep -E "process_file_background|Processing file|Background.*file"
```

**Result:** No output - background task is not running.

### Step 2: Check File Registry API

```bash
curl http://localhost:8000/api/v1/files/list?cert_profile_id=455dae60-065c-4038-b3df-6d769b955dbb
```

**Expected:** List of files with their status.

### Step 3: Check Database for File Records

```bash
docker exec presgen-assess python3 -c "
import sqlite3
conn = sqlite3.connect('/app/data/presgen_assess.db')
cursor = conn.execute('SELECT * FROM knowledge_base_documents')
for row in cursor:
    print(row)
"
```

**Result:** No records found for uploaded files.

### Step 4: Check Background Task Logs

Add logging to background task to see if it's executing:

```python
async def process_file_background(...):
    print(f"🔄 BACKGROUND PROCESSING STARTED: {file_metadata.file_id}")
    try:
        # ... existing code
        print(f"✅ BACKGROUND PROCESSING COMPLETED: {file_metadata.file_id}")
    except Exception as e:
        print(f"❌ BACKGROUND PROCESSING FAILED: {file_metadata.file_id}: {e}")
```

---

## Possible Causes

### Cause 1: FastAPI BackgroundTasks Not Executing

**Issue:** `background_tasks.add_task()` may not be executing if:
- Response is returned before task runs
- Task fails silently without logging
- Exception in task is swallowed

**Solution:** Add try/catch with explicit logging at the start of `process_file_background`.

### Cause 2: Async Context Issues

**Issue:** `process_file_background` is async but may not have proper event loop context.

**Code:** [file_management.py:567](src/service/api/v1/endpoints/file_management.py#L567)

```python
async def process_file_background(...):  # async function
```

**Problem:** Background tasks in FastAPI might not properly handle async functions in some cases.

**Solution:** Ensure proper async execution or use synchronous background processing.

### Cause 3: ChromaDB Manager Initialization Fails

**Issue:** `get_chroma_manager()` at line 576 might be failing silently.

**Code:** [file_management.py:48-58](src/service/api/v1/endpoints/file_management.py#L48-L58)

```python
def get_chroma_manager():
    global chroma_client, collection_manager
    if collection_manager is None:
        chroma_client = chromadb.PersistentClient(
            path="data/chroma",
            settings=chromadb.Settings(anonymized_telemetry=False)
        )
        collection_manager = ChromaDBCollectionManager(chroma_client)
    return collection_manager
```

**If this fails:** Background task would crash but exception might not be logged.

### Cause 4: File Registry Status Not Persisted

**Issue:** `file_registry.update_file_status()` updates in-memory dict but doesn't persist to database.

**Location:** Status updates at lines 613-625 don't write to `knowledge_base_documents` table.

**Result:** UI can't query persistent status.

---

## Recommended Fixes

### Fix 1: Add Comprehensive Logging to Background Task

```python
async def process_file_background(
    file_metadata: FileMetadata,
    cert_id: str,
    bundle_version: str,
    domain_mappings: Dict[str, str],
    cert_name: str
):
    """Background task to process uploaded file"""
    print("="*80)
    print(f"🔄 BACKGROUND TASK STARTED")
    print(f"   File ID: {file_metadata.file_id}")
    print(f"   Filename: {file_metadata.original_filename}")
    print(f"   Cert ID: {cert_id}")
    print("="*80)

    try:
        print("📊 Step 1: Getting ChromaDB manager...")
        manager = get_chroma_manager()
        print("✅ ChromaDB manager obtained")

        # ... rest of the code with logging at each step

    except Exception as e:
        print(f"❌ BACKGROUND TASK EXCEPTION: {type(e).__name__}")
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        # Update status
        file_registry.update_file_status(
            file_metadata.file_id,
            "failed",
            str(e),
            chunk_count=0
        )
```

### Fix 2: Persist Status to Database

Create a database model for file tracking and persist status updates:

```python
# After updating file_registry
file_registry.update_file_status(file_id, "completed", None, chunk_count)

# Also update database
await db.execute(
    update(KnowledgeBaseDocuments)
    .where(KnowledgeBaseDocuments.id == UUID(file_id))
    .values(
        processing_status="completed",
        chunk_count=chunk_count,
        processed_at=datetime.utcnow()
    )
)
await db.commit()
```

### Fix 3: Add Status Polling Endpoint

```python
@router.get("/status/{file_id}")
async def get_file_status(file_id: str):
    """Get processing status for a file"""
    # Check in-memory registry first
    file_info = file_registry.get_file(file_id)
    if file_info:
        return {
            "file_id": file_id,
            "status": file_info.processing_status,
            "chunk_count": file_info.chunk_count,
            "error_message": file_info.error_message
        }

    # Fallback to database
    # Query knowledge_base_documents table
    ...
```

### Fix 4: UI to Poll for Status Updates

Update the frontend to poll the status endpoint after upload:

```javascript
// After successful upload
const pollStatus = async (fileId) => {
  const maxAttempts = 30;
  for (let i = 0; i < maxAttempts; i++) {
    const status = await fetch(`/api/v1/files/status/${fileId}`);
    const data = await status.json();

    if (data.status === 'completed') {
      updateUI(fileId, 'success');
      break;
    } else if (data.status === 'failed') {
      updateUI(fileId, 'failed', data.error_message);
      break;
    }

    await sleep(2000); // Wait 2 seconds
  }
};
```

---

## Immediate Action Items

1. **Add logging to background task** - See if it's even running
2. **Check background task execution** - Run test upload and watch logs
3. **Verify ChromaDB path** - Ensure `data/chroma` is accessible
4. **Check file registry endpoint** - See what UI is querying
5. **Add database persistence** - Store status in knowledge_base_documents

---

## Summary

**The "Failed" status is NOT because the upload failed.**

The upload, file save, and in-memory registration all succeed. The issue is:

1. ❌ Background processing (`process_file_background`) is not executing or failing silently
2. ❌ No database record is created for the file
3. ❌ UI shows "Failed" because it can't find a proper status
4. ❌ No mechanism for UI to get real-time status updates

**To fix:**
- Add comprehensive logging to background task
- Persist file status to database
- Create status polling mechanism
- Debug why background task isn't running

**Status:** ⚠️ Files are uploaded successfully but not being processed into vector database
