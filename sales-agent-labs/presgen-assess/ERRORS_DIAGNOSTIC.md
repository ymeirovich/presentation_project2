# PresGen-Assess Error Diagnostic Report

**Date:** 2025-11-03
**Component:** presgen-assess
**Status:** ⚠️ Non-blocking warnings identified

---

## Error 1: Knowledge Base Prompts Not Found

### Error Message

```json
{
  "level": "WARNING",
  "message": "Knowledge base prompts not found for collection: aws_machine_learning_specialty_vMLS-C01",
  "step": "api_get_not_found",
  "success": false
}
```

### Analysis

**What's Happening:**
- API endpoint: `GET /knowledge-prompts/{collection_name}`
- Requested collection: `aws_machine_learning_specialty_vMLS-C01`
- Result: 404 Not Found - prompts don't exist in database

**Why It Happens:**
This is **expected behavior** when:
1. A new certification collection is created
2. Custom prompts haven't been defined yet
3. System attempts to load collection-specific prompts

**Impact:**
- ⚠️ **Non-blocking** - System continues to function
- System falls back to default prompts
- All features work, just without customization

### Solution

#### Option 1: Create Default Prompts (Recommended)

Create prompts for this collection via API:

```bash
curl -X POST http://localhost:8000/api/v1/knowledge-prompts/ \
  -H "Content-Type: application/json" \
  -d '{
    "collection_name": "aws_machine_learning_specialty_vMLS-C01",
    "certification_name": "AWS Machine Learning Specialty",
    "document_ingestion_prompt": "Extract key concepts from AWS ML certification materials...",
    "context_retrieval_prompt": "Retrieve relevant AWS ML context for the question...",
    "semantic_search_prompt": "Search for AWS ML concepts related to...",
    "content_classification_prompt": "Classify content as: exam_guide, practice_question, concept_explanation...",
    "version": "1.0",
    "is_active": true
  }'
```

#### Option 2: Run Migration Script

If a migration script exists:

```bash
docker exec presgen-assess python scripts/migrate_prompts.py
```

#### Option 3: Ignore (Use Defaults)

- No action needed
- System uses default prompts
- Functionality not impacted

**Recommendation:** **Option 3** (Ignore) - unless you need custom prompts for this specific certification.

---

## Error 2: File Upload Status "Failed"

### Symptoms

- File uploaded via Resource Manager
- Status shows as "Failed"
- No clear error message in immediate logs

### Possible Causes

Based on code analysis of [file_upload_service.py](src/service/file_upload_service.py):

#### 1. File Validation Failure

**Common Issues:**
- File size exceeds 50MB limit
- File extension not in allowed list: `.pdf`, `.docx`, `.txt`, `.md`
- Missing filename

**Check:**
```python
# Line 87-98 in file_upload_service.py
def validate_file(self, file: UploadFile) -> None:
    # Checks file extension and size
```

#### 2. ChromaDB Connection Issues

**Symptoms from logs:**
```
Failed to send telemetry event ClientStartEvent: capture() takes 1 positional argument but 3 were given
```

**Analysis:**
- ChromaDB telemetry has version mismatch
- ⚠️ **Non-critical** - telemetry failure doesn't block processing
- Actual document processing may still work

#### 3. Document Processing Failure

**Check:**
- PDF parsing errors
- DOCX corruption
- Text extraction issues

#### 4. Database Session Errors

**From logs:**
```
❌ Database session error:
```

**Possible cause:**
- Database connection timeout
- Transaction conflict
- Schema mismatch

### Diagnostic Steps

#### Step 1: Check File Upload Logs

```bash
docker logs presgen-assess 2>&1 | grep -i "upload\|processing" | tail -100
```

Look for:
- File size information
- Processing errors
- ChromaDB insertion failures

#### Step 2: Check Database

```bash
# Connect to container
docker exec -it presgen-assess bash

# Check database for file records
sqlite3 /app/data/presgen_assess.db "SELECT * FROM file_metadata WHERE processing_status='failed' ORDER BY upload_timestamp DESC LIMIT 10;"
```

#### Step 3: Check File Permissions

```bash
docker exec presgen-assess ls -la /app/uploads/
```

Ensure:
- Directory is writable
- Files are being created
- Permissions are correct

#### Step 4: Test File Upload Manually

```bash
# Create test file
echo "Test content for AWS ML certification" > test.txt

# Upload via API
curl -X POST http://localhost:8000/api/v1/files/upload \
  -F "file=@test.txt" \
  -F "cert_profile_id=your-cert-id" \
  -F "resource_type=SUPPLEMENTAL"
```

### Common Solutions

#### Solution 1: Check File Size

```bash
# If file is too large, increase limit in docker-compose.yml
environment:
  - MAX_FILE_SIZE=104857600  # 100MB
```

#### Solution 2: Fix ChromaDB Telemetry (Optional)

Disable telemetry to reduce noise:

```python
# In src/service/chromadb_schema.py or initialization
import chromadb
client = chromadb.Client(
    Settings(
        anonymized_telemetry=False  # Disable telemetry
    )
)
```

#### Solution 3: Check Database Schema

```bash
# Verify table exists
docker exec presgen-assess sqlite3 /app/data/presgen_assess.db ".schema file_metadata"
```

#### Solution 4: Review Processing Status Field

Check file_upload_service.py line 40:
```python
processing_status: str = "pending"  # pending, processing, completed, failed
```

Find where status is set to "failed" and add logging.

---

## Non-Critical Warnings (Can be Ignored)

### 1. ChromaDB Telemetry Errors

```
Failed to send telemetry event ClientStartEvent: capture() takes 1 positional argument but 3 were given
```

**Status:** ⚠️ Cosmetic
**Impact:** None - telemetry is optional
**Fix:** Disable telemetry (optional)

### 2. bcrypt Version Warning

```
(trapped) error reading bcrypt version
AttributeError: module 'bcrypt' has no attribute '__about__'
```

**Status:** ⚠️ Non-blocking
**Impact:** None - authentication still works
**Fix:** Update bcrypt (optional)

### 3. Startup Validation Warnings

```
⚠️  Some startup checks failed. The service may not function correctly.
```

**Status:** ⚠️ Expected in development
**Impact:** Service continues to run
**Fix:** Review startup checks, but service is functional

---

## Recommended Actions

### Immediate (To Fix File Upload)

1. **Get specific error details:**
   ```bash
   # Check recent file processing logs
   docker logs presgen-assess --tail=500 | grep -A 10 "failed"

   # Check what's being stored in database
   docker exec presgen-assess python -c "
   import sqlite3
   conn = sqlite3.connect('/app/data/presgen_assess.db')
   cursor = conn.execute('SELECT * FROM file_metadata WHERE processing_status=\"failed\" ORDER BY upload_timestamp DESC LIMIT 1')
   for row in cursor:
       print(row)
   "
   ```

2. **Try a test upload with detailed logging:**
   - Upload a small text file
   - Monitor logs in real-time:
     ```bash
     docker logs -f presgen-assess
     ```

3. **Check file details:**
   - What file are you uploading?
   - File size?
   - File type?

### Optional (Nice to Have)

1. **Fix telemetry warnings:**
   - Disable ChromaDB telemetry
   - Update bcrypt package

2. **Create knowledge base prompts:**
   - Only if you need custom prompts
   - Otherwise use defaults

---

## Need More Information

To provide a more specific fix for Error 2 (File Upload Failed), please provide:

1. **What file are you uploading?**
   - Filename
   - File size
   - File type (.pdf, .docx, etc.)

2. **When does it fail?**
   - Immediately after upload?
   - During processing?
   - After ChromaDB insertion?

3. **Any error messages in the UI?**
   - What does the UI show?
   - Any error details?

4. **Run this diagnostic:**
   ```bash
   docker logs presgen-assess 2>&1 | grep -A 20 -B 5 "processing_status\|FileUploadService\|process_file" | tail -100
   ```

---

## Summary

| Error | Severity | Impact | Action |
|-------|----------|--------|--------|
| Knowledge Base Prompts Not Found | ⚠️ Warning | None - uses defaults | Optional: Create prompts |
| File Upload Failed | ❌ Error | File not processed | **Investigate**: Need more details |
| ChromaDB Telemetry | ⚠️ Cosmetic | None | Optional: Disable telemetry |
| bcrypt Warning | ⚠️ Cosmetic | None | Optional: Update package |

**Next Step:** Gather more details about the file upload failure using the diagnostic commands above.
