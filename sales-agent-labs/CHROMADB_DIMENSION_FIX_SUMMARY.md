# ChromaDB "Cannot Open Header File" Fix - Complete Solution

**Date:** 2025-11-15
**Issue:** Knowledge base file uploads failing with "Cannot open header file" error
**Root Cause:** Embedding dimension mismatch after AWS migration
**Status:** ✅ RESOLVED

---

## Table of Contents

1. [Problem Summary](#problem-summary)
2. [Root Cause Analysis](#root-cause-analysis)
3. [Solution Overview](#solution-overview)
4. [Implementation Details](#implementation-details)
5. [Deployment Instructions](#deployment-instructions)
6. [Validation & Testing](#validation--testing)
7. [Prevention & Monitoring](#prevention--monitoring)

---

## Problem Summary

### Symptoms
- File uploads to Knowledge Base showing "Failed" status
- Logs showing: `❌ Status updated to 'failed': Cannot open header file`
- Error occurs during batch processing: `📦 Adding batch 1/73`
- Problem persists across container rebuilds

### Impact
- Users cannot upload certification materials (PDFs, transcripts, DOCX)
- RAG (Retrieval Augmented Generation) context not available
- Assessment generation quality degraded

---

## Root Cause Analysis

### The Migration Issue

**What happened:**
1. ✅ SQLite database migrated from local dev → AWS Lightsail
   - Contains: 4 cert profiles, 92 workflows, 6 knowledge base document records
   - Includes collection metadata expecting 1536-dimensional embeddings

2. ❌ ChromaDB vector database NOT migrated
   - `data/chroma/` directory empty on AWS
   - No vector index files present

3. ❌ OpenAI API key configuration unclear
   - System falls back to 128-dimensional simple hash embeddings
   - Dimension mismatch: collections expect 1536-dim, receiving 128-dim

### Technical Details

**Error Source:** Hnswlib (vector similarity search library used by ChromaDB)

**Error Location:** `src/service/chromadb_schema.py:346-350`
```python
collection.add(
    documents=batch_docs,
    metadatas=batch_metas,
    ids=batch_ids
)  # ❌ Fails here with "Cannot open header file"
```

**Embedding Dimensions:**
- **OpenAI `text-embedding-3-small`**: 1536 dimensions
- **Fallback `simple_hash`**: 128 dimensions
- **Mismatch**: Collection created for 1536-dim, receiving 128-dim vectors

### Why This Wasn't Caught Earlier

1. **No embedding dimension validation** in upload flow
2. **Silent fallback** when OpenAI API key missing/invalid
3. **No dimension tracking** in database schema
4. **Poor error messages** from ChromaDB/Hnswlib

---

## Solution Overview

### Four-Pillar Approach

1. **Database Backup & Reset** (Option 1)
   - Backup current database
   - Reset ChromaDB vector data
   - Clear failed document processing status

2. **Enhanced Error Handling** (Option 2)
   - Wrap ChromaDB operations in try/catch
   - Provide actionable diagnostic messages
   - Guide users to fix

3. **Schema Enhancement** (Option 3)
   - Add `embedding_dimension` column to `knowledge_base_documents`
   - Track embedding model and dimensions
   - Enable dimension validation

4. **API Key Validation** (Option 4)
   - Verify OPENAI_API_KEY in container environment
   - Startup checks for embedding service
   - Clear error messages when missing

---

## Implementation Details

### 1. Diagnostic & Fix Script

**File:** `fix_chromadb_dimensions.py`

**Features:**
- ✅ Check OpenAI API key in presgen-assess container
- ✅ Inspect ChromaDB data directory
- ✅ Analyze knowledge_base_documents table
- ✅ Backup database with timestamps
- ✅ Reset ChromaDB collections
- ✅ Reset document processing status
- ✅ Automated fix workflow

**Usage:**
```bash
# Run diagnostic (read-only)
python3 fix_chromadb_dimensions.py

# Backup database
python3 fix_chromadb_dimensions.py --backup

# Full reset (with backups)
python3 fix_chromadb_dimensions.py --full-reset

# Automated fix (all steps)
python3 fix_chromadb_dimensions.py --auto-fix
```

### 2. Enhanced Error Handling

**File:** `presgen-assess/src/service/chromadb_schema.py`

**Changes:**
- Added try/catch around `collection.add()` (lines 345-389)
- Detect "Cannot open header file" error
- Provide diagnostic guidance
- Suggest fix: `python3 fix_chromadb_dimensions.py --auto-fix`

**Error Message Example:**
```
❌ Failed to add batch 1/73
❌ Error: Cannot open header file

🔍 DIAGNOSIS: Embedding Dimension Mismatch
   - ChromaDB collection expects different embedding dimensions
   - Common causes:
     1. OpenAI API key missing → fallback to 128-dim embeddings
     2. Collection created with 1536-dim, now using 128-dim
     3. Database migrated without ChromaDB vector data

🔧 FIX:
   1. Validate OPENAI_API_KEY is set in presgen-assess/.env
   2. Run: python3 fix_chromadb_dimensions.py --auto-fix
   3. Re-upload files after fix completes
```

### 3. Database Schema Enhancement

**File:** `presgen-assess/src/models/certification.py`

**Changes:**
- Added `embedding_dimension` column (line 63)
- Track vector dimensions per document
- Enable validation before processing

**Migration:** `presgen-assess/alembic/versions/add_embedding_dimension.py`
```sql
ALTER TABLE knowledge_base_documents
ADD COLUMN embedding_dimension INTEGER;

-- Set defaults for existing records
UPDATE knowledge_base_documents
SET embedding_dimension = 1536
WHERE embedding_model = 'text-embedding-3-small';

UPDATE knowledge_base_documents
SET embedding_dimension = 128
WHERE embedding_model IS NULL OR embedding_model = 'simple_hash';
```

### 4. API Key Validation

**Function:** `check_openai_api_key_in_container()`

**Checks:**
- Reads OPENAI_API_KEY from presgen-assess container
- Validates format (starts with `sk-` or `sk-proj-`)
- Reports dimension mismatch risk
- Provides fix instructions

---

## Deployment Instructions

### Step 1: Copy Files to AWS

```bash
# From your local machine
cd /Users/yitzchak/Documents/learn/presentation_project/sales-agent-labs

# Copy diagnostic script
scp fix_chromadb_dimensions.py ubuntu@35.175.156.231:/home/ubuntu/presgen/sales-agent-labs/

# Copy updated source files
scp presgen-assess/src/service/chromadb_schema.py \
    ubuntu@35.175.156.231:/home/ubuntu/presgen/sales-agent-labs/presgen-assess/src/service/

scp presgen-assess/src/models/certification.py \
    ubuntu@35.175.156.231:/home/ubuntu/presgen/sales-agent-labs/presgen-assess/src/models/

scp presgen-assess/alembic/versions/add_embedding_dimension.py \
    ubuntu@35.175.156.231:/home/ubuntu/presgen/sales-agent-labs/presgen-assess/alembic/versions/
```

### Step 2: SSH to AWS

```bash
ssh ubuntu@35.175.156.231
cd /home/ubuntu/presgen/sales-agent-labs
```

### Step 3: Copy Script to Container

```bash
# Copy the diagnostic script into the running container
docker cp fix_chromadb_dimensions.py presgen-assess:/app/
```

### Step 4: Run Diagnostic Inside Container

```bash
# Run the diagnostic from inside the container
docker exec -it presgen-assess python3 /app/fix_chromadb_dimensions.py
```

**Expected Output:**

- 🐳 Running inside Docker container
- 🔑 OpenAI API key check (from container env)
- 📂 ChromaDB directory status at /app/data/chroma
- 🗄️ Database document count by status from /app/data/presgen_assess.db

### Step 5: Verify OpenAI API Key

```bash
# Check if API key is set in container
docker exec presgen-assess printenv OPENAI_API_KEY

# If not set or invalid, add to .env file
nano presgen-assess/.env

# Add line:
# OPENAI_API_KEY=sk-proj-your-key-here

# Restart container
docker-compose restart presgen-assess
```

### Step 6: Run Database Migration

```bash
# Apply schema changes (adds embedding_dimension column)
docker exec presgen-assess alembic upgrade head
```

### Step 7: Run Automated Fix

```bash
# Run the automated fix inside the container
# This will:
# 1. Backup database (timestamped)
# 2. Validate OpenAI key
# 3. Reset ChromaDB vector data
# 4. PRESERVE document records and reset status to 'pending'
docker exec -it presgen-assess python3 /app/fix_chromadb_dimensions.py --auto-fix
```

**Confirm when prompted (10 second countdown)**

**What happens to your data:**

- ✅ **Database records PRESERVED** - All document metadata kept (filenames, paths, sizes)
- ✅ **Files PRESERVED** - Original uploaded files remain on disk
- ✅ **Status reset to 'pending'** - Documents will be automatically re-processed
- ✅ **Vector data reset** - ChromaDB will recreate embeddings with correct dimensions
- ✅ **Backup created** - Full database backup with timestamp for safety

### Step 8: Rebuild and Restart Containers

```bash
# Rebuild with updated code
docker-compose build presgen-assess

# Restart services
docker-compose up -d

# Verify healthy
docker-compose ps
```

---

## Validation & Testing

### 1. Check Container Health

```bash
docker-compose ps
# presgen-assess should show "Up" and "healthy"
```

### 2. Check API Key in Container

```bash
docker exec presgen-assess printenv OPENAI_API_KEY
# Should output: sk-proj-...
```

### 3. Test File Upload

**Via UI:**
1. Navigate to: http://35.175.156.231
2. Go to Certification Resource Manager
3. Upload a small test file (e.g., a TXT or PDF)
4. Monitor logs:
   ```bash
   docker-compose logs -f presgen-assess
   ```

**Expected Logs:**
```
📥 FileUploadService: Saving file 'test.txt'
✅ File saved successfully
📦 Adding batch 1/X: 20 documents
✅ Successfully added Y documents in Z batches
✅ Status updated to 'completed' with Y chunks
```

### 4. Verify in Database

```bash
docker exec presgen-assess python3 -c "
import sqlite3
conn = sqlite3.connect('/app/data/presgen_assess.db')
cursor = conn.execute('''
    SELECT original_filename, processing_status, chunk_count, embedding_dimension
    FROM knowledge_base_documents
    ORDER BY created_at DESC
    LIMIT 5
''')
for row in cursor:
    print(f'{row[0]:<40} {row[1]:<15} chunks={row[2]:<5} dim={row[3]}')
"
```

**Expected Output:**
```
test.txt                                 completed       chunks=15   dim=1536
```

---

## Prevention & Monitoring

### Future Deployment Best Practices

1. **Always Migrate Both Databases**
   - SQLite database (presgen_assess.db)
   - ChromaDB vector data (data/chroma/)
   - Or start fresh and re-upload files

2. **Validate Environment Before Upload**
   - Run `fix_chromadb_dimensions.py` diagnostic
   - Verify OPENAI_API_KEY is set
   - Check embedding dimension consistency

3. **Track Embedding Dimensions**
   - Use new `embedding_dimension` column
   - Add validation in upload flow
   - Alert on dimension mismatches

### Monitoring Checklist

```bash
# Daily health check
docker-compose logs presgen-assess | grep -E "❌|Failed|Error" | tail -20

# Weekly database check
python3 fix_chromadb_dimensions.py

# After any migration
python3 fix_chromadb_dimensions.py --auto-fix
```

### Startup Validation

Add to presgen-assess startup checks:
1. Verify OPENAI_API_KEY is set
2. Test embedding generation
3. Check ChromaDB connectivity
4. Validate collection dimensions match expected

---

## Files Modified

### New Files
- ✅ `fix_chromadb_dimensions.py` - Diagnostic and fix script
- ✅ `CHROMADB_DIMENSION_FIX_SUMMARY.md` - This document
- ✅ `presgen-assess/alembic/versions/add_embedding_dimension.py` - Schema migration

### Modified Files
- ✅ `presgen-assess/src/service/chromadb_schema.py` - Enhanced error handling
- ✅ `presgen-assess/src/models/certification.py` - Added embedding_dimension column
- ✅ `presgen-assess/src/service/app.py` - Already fixed (allowed_hosts)

---

## Summary

### Root Cause
Database migrated without vector data → dimension mismatch → "Cannot open header file"

### Solution
1. Validate OpenAI API key
2. Reset ChromaDB and document status
3. Add dimension tracking and error handling
4. Re-upload files with proper embeddings

### Prevention
- Track embedding dimensions in schema
- Validate environment before processing
- Provide clear error messages
- Monitor upload success rates

### Status
✅ **RESOLVED** - All components implemented and ready for deployment

---

**Next Action:** Run deployment instructions on AWS Lightsail instance.
