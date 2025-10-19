# Testing Instructions - After All Fixes

## Summary of All Fixes Applied

### ✅ 1. Fixed Hardcoded certification_id = "aws-ml-specialty"
- **File:** `src/services/ai_question_generator.py`
- All assessments now use correct certification

### ✅ 2. Fixed ChromaDB Metadata Key Mismatch
- **File:** `src/knowledge/embeddings.py`
- Changed query from `cert_id` → `certification_id`

### ✅ 3. Added Comprehensive Logging
- **Files:** `src/knowledge/embeddings.py`, `src/services/llm_service.py`
- Full visibility into RAG retrieval and LLM requests

### ✅ 4. Fixed Embedding Function Mismatch
- **File:** `src/service/chromadb_schema.py`
- Changed from DefaultEmbeddingFunction → OpenAIEmbeddingFunctionV1
- **This fix should resolve upload processing failures!**

### ✅ 5. Updated ICF Certification Profile
- **Database:** Set `collection_name='icf-core-competency'`

---

## Current Status

### Files Already Uploaded (But Failed Processing):
```sql
2f81da97... | ACC Exam Preparation Study Guide.txt | failed
b6098ad7... | ACC ICF Preparation transcript.txt   | failed
```

**Why They Failed:**
- Uploaded BEFORE embedding function fix
- Processing used DefaultEmbeddingFunction (incompatible)

---

## Testing Steps

### Step 1: Delete Old Failed Uploads
```bash
cd /Users/yitzchak/Documents/learn/presentation_project/sales-agent-labs/presgen-assess

# Delete from database
sqlite3 test_database.db "DELETE FROM knowledge_base_documents WHERE processing_status='failed';"

# Delete files from disk
rm -f uploads/exam_guides/2f81da97-7927-452d-8d3d-8c4d8b229c68.txt
rm -f uploads/transcripts/b6098ad7-5f48-4538-9844-ee70eff74aee.txt
```

### Step 2: Verify Application is Running with New Code
```bash
# Check process
ps aux | grep "python.*main" | grep -v grep

# Should show: /Python main.py running
```

**If NOT running:**
```bash
pkill -f "python.*main"
python main.py
```

### Step 3: Re-upload Files via UI

**Upload these files for ICF certification:**
1. ACC Exam Preparation Study Guide.txt
2. ACC ICF Preparation transcript.txt

**Expected in UI:**
- During upload: Shows "Uploading..." or spinner
- After upload: Shows "Processing..." (NOT "Failed")
- After ~30-60 seconds: Shows "Completed" ✅

**If still shows "Failed":**
Check stdout for errors (the terminal where `python main.py` is running)

### Step 4: Verify Database
```bash
sqlite3 test_database.db "SELECT id, original_filename, processing_status, chunk_count FROM knowledge_base_documents WHERE certification_profile_id='36b361410f79449fa6bfb2ec59fddcd1' ORDER BY created_at DESC;"
```

**Expected Output:**
```
<uuid> | ACC Exam Preparation Study Guide.txt | completed | <chunk_count>
<uuid> | ACC ICF Preparation transcript.txt   | completed | <chunk_count>
```

**NOT:**
```
<uuid> | ... | failed | 0
```

### Step 5: Verify ChromaDB Collections
```bash
sqlite3 test_database.db "SELECT name FROM sqlite_master WHERE type='table' AND name LIKE '%chroma%';"
```

Should show ChromaDB tables with data.

### Step 6: Test RAG Retrieval
Generate an ICF assessment and check logs:

```bash
# Watch logs in real-time
tail -f src/logs/assessments.log | grep -E "certification_id|RAG retrieve"
```

**Expected:**
```
🎯 Using certification_id for RAG | vector_cert_id=icf-core-competency
🔍 RAG retrieve_context | certification_id=icf-core-competency
📊 Query returned 3 chunks from exam_guides
✅ RAG retrieval complete | total_chunks=6 | docs=['ACC Exam Preparation Study Guide.txt', ...]
```

**NOT:**
```
certification_id=aws-ml-specialty  ❌ WRONG!
total_chunks=0  ❌ NO DATA FOUND!
```

### Step 7: Verify Assessment Questions
Check that generated questions are about ICF coaching, NOT AWS ML!

**Good:**
- "What are the ICF Core Competencies?"
- "Explain the ethical guidelines for coaches"

**Bad:**
- "What is Amazon SageMaker?" ❌
- "Explain AWS ML pipeline" ❌

---

## Troubleshooting

### Issue: Files Still Show "Failed"

**Check 1: Embedding Function**
```bash
grep "OpenAI embedding function\|SentenceTransformer" src/logs/*.log | tail -5
```

**Expected:**
```
✅ Using OpenAI embedding function: text-embedding-3-small
```

**NOT:**
```
SentenceTransformerEmbeddingFunction unavailable
```

**Check 2: OpenAI API Key**
```bash
grep "OPENAI_API_KEY" .env
```

Should show a valid API key.

**Check 3: Actual Error**
Look at the terminal running `python main.py` for exceptions during background processing.

### Issue: RAG Returns 0 Results

**Check 1: Verify Documents Processed**
```bash
sqlite3 test_database.db "SELECT processing_status, chunk_count FROM knowledge_base_documents WHERE certification_profile_id='36b361410f79449fa6bfb2ec59fddcd1';"
```

**Expected:**
```
completed | 45
completed | 32
```

**NOT:**
```
failed | 0
pending | 0
```

**Check 2: Verify ChromaDB Has Data**
```python
from src.knowledge.embeddings import VectorDatabaseManager
vector_db = VectorDatabaseManager()

# Check collections
print(vector_db.exam_guides_collection.count())  # Should be > 0
print(vector_db.transcripts_collection.count())  # Should be > 0
```

### Issue: Still Using aws-ml-specialty

**Check:** Application restart
```bash
# Kill old process
pkill -f "python.*main"

# Clear Python cache
find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null

# Restart
python main.py
```

---

## Success Criteria

✅ Files upload successfully
✅ `processing_status='completed'` in database
✅ `chunk_count > 0` for uploaded files
✅ RAG retrieval uses `certification_id='icf-core-competency'`
✅ RAG returns chunks from uploaded files
✅ Assessment questions are relevant to ICF content
✅ No "aws-ml-specialty" in logs
✅ No "SentenceTransformerEmbeddingFunction unavailable" warnings

---

## If Everything Fails

### Nuclear Option: Fresh Start
```bash
# 1. Stop application
pkill -f "python.*main"

# 2. Delete ALL ChromaDB data
rm -rf chroma_db/

# 3. Delete ALL uploaded files
rm -rf uploads/exam_guides/*
rm -rf uploads/transcripts/*

# 4. Clear database
sqlite3 test_database.db "DELETE FROM knowledge_base_documents;"

# 5. Clear Python cache
find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null

# 6. Restart
python main.py

# 7. Re-upload files
# Upload via UI
```

---

## Logs to Monitor

### Success Indicators:
```bash
# Upload processing
grep "✅ Using OpenAI embedding function" src/logs/*.log

# RAG retrieval
grep "certification_id=icf-core-competency" src/logs/assessments.log

# Successful processing
grep "processing_status=completed" src/logs/*.log
```

### Failure Indicators:
```bash
# Embedding mismatch
grep "SentenceTransformer.*unavailable" src/logs/*.log

# Wrong certification
grep "certification_id=aws-ml-specialty" src/logs/assessments.log

# Processing failures
grep "processing_status=failed" src/logs/*.log
```

---

**All fixes are in place - testing should now succeed!**
