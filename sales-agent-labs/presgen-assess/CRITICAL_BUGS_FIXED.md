# 🚨 CRITICAL BUGS FIXED - RAG Context Mixing

## Summary
Assessment questions were mixing content from ALL certifications due to **THREE CRITICAL BUGS**:

1. ✅ ChromaDB metadata key mismatch (cert_id vs certification_id)
2. ✅ Hardcoded certification_id = "aws-ml-specialty"
3. ✅ Missing collection_name in certification profiles

---

## 🐛 BUG #1: ChromaDB Metadata Key Mismatch

### Problem:
Documents stored with `"certification_id"` but queried with `"cert_id"` first, causing filter failure.

### Evidence:
```python
# Storage (documents.py:238)
metadata = {"certification_id": certification_id, ...}

# Query (embeddings.py:151) - WRONG!
where={"cert_id": certification_id}
```

### Fix:
**File:** `src/knowledge/embeddings.py:163`
```python
# Changed primary query to use correct key
where={"certification_id": certification_id}  # ✅ CORRECT
```

### Status: ✅ FIXED

---

## 🐛 BUG #2: Hardcoded certification_id = "aws-ml-specialty"

### Problem:
`ai_question_generator.py` **HARDCODED** certification_id to "aws-ml-specialty" for ALL certifications!

### Evidence from Logs:
```
2025-10-19 16:06:14 | cert_profile_id=36b36141-0f79-449f-a6bf-b2ec59fddcd1 (ICF Core Competency)
2025-10-19 16:06:14 | certification_id=aws-ml-specialty ❌ WRONG!
```

### Root Cause:
**File:** `src/services/ai_question_generator.py:434`
```python
# BEFORE (HARDCODED):
vector_cert_id = "aws-ml-specialty"  # TODO: Make this dynamic
```

### Fix:
**File:** `src/services/ai_question_generator.py:431-450`
```python
# ✅ FIX: Derive vector_cert_id from certification profile
vector_cert_id = cert_resources.get("collection_name")

if not vector_cert_id:
    # Derive slug from certification name as fallback
    cert_name_lower = cert_name.lower()
    import re
    vector_cert_id = re.sub(r'[^a-z0-9]+', '-', cert_name_lower).strip('-')
    logger.warning(
        f"⚠️ No collection_name for cert_profile_id={cert_profile_id}, "
        f"derived vector_cert_id={vector_cert_id} from cert_name={cert_name}"
    )

logger.info(
    f"🎯 Using certification_id for RAG | cert_profile_id={cert_profile_id} | "
    f"vector_cert_id={vector_cert_id} | cert_name={cert_name}"
)
```

### Status: ✅ FIXED

---

## 🐛 BUG #3: Missing collection_name in cert_resources

### Problem:
`_get_certification_resources()` didn't include `collection_name`, so the fix in Bug #2 couldn't work.

### Root Cause:
**File:** `src/services/ai_question_generator.py:301-310` (BEFORE)
```python
resources = {
    "certification_name": profile.name,
    "certification_profile_id": certification_profile_id,
    # ❌ collection_name NOT INCLUDED
    "knowledge_domains": knowledge_domains,
    ...
}
```

### Fix:
**File:** `src/services/ai_question_generator.py:305`
```python
resources = {
    "certification_name": profile.name,
    "certification_profile_id": certification_profile_id,
    "collection_name": profile.collection_name,  # ✅ ADDED
    "knowledge_domains": knowledge_domains,
    ...
}
```

### Status: ✅ FIXED

---

## 🐛 BUG #4: ICF Certification Missing collection_name in Database

### Problem:
ICF certification profile in database had NULL `collection_name`.

### Evidence:
```sql
SELECT id, name, collection_name FROM certification_profiles;
36b361410f79449fa6bfb2ec59fddcd1|ACC ICF Certification|   ❌ NULL
```

### Fix:
```sql
UPDATE certification_profiles
SET collection_name='icf-core-competency'
WHERE id='36b361410f79449fa6bfb2ec59fddcd1';
```

### Status: ✅ FIXED

---

## 📊 Files Modified

| File | Lines | Changes |
|------|-------|---------|
| `src/knowledge/embeddings.py` | 16-19, 141-317 | Logger import + comprehensive RAG logging |
| `src/services/llm_service.py` | 57-156, 219-270 | Certification & LLM request/response logging |
| `src/services/ai_question_generator.py` | 305, 431-450 | Add collection_name + fix hardcoded cert_id |
| `test_database.db` | - | Updated ICF collection_name |

---

## ✅ Verification Steps

### 1. Restart Application
```bash
pkill -f "uvicorn.*presgen"
cd /Users/yitzchak/Documents/learn/presentation_project/sales-agent-labs/presgen-assess
python main.py
```

### 2. Generate ICF Assessment
Create a new workflow for cert_profile_id `36b36141-0f79-449f-a6bf-b2ec59fddcd1`.

### 3. Check Logs
```bash
tail -f src/logs/assessments.log | grep "🎯 Using certification_id"
```

**Expected Output:**
```
🎯 Using certification_id for RAG | cert_profile_id=36b36141-0f79-449f-a6bf-b2ec59fddcd1 | vector_cert_id=icf-core-competency | cert_name=ACC ICF Certification
```

### 4. Verify RAG Retrieval
```bash
tail -f src/logs/assessments.log | grep "🔍 RAG retrieve_context"
```

**Expected Output:**
```
🔍 RAG retrieve_context | certification_id=icf-core-competency | query=Coaching Ethics...
```

**NOT:**
```
🔍 RAG retrieve_context | certification_id=aws-ml-specialty ❌ WRONG!
```

### 5. Check for Certification Mismatches
```bash
grep "🚨 CRITICAL: RAG certification mismatch" src/logs/assessments.log
```

**Expected:** No results (no mismatches)

---

## ⚠️ Known Remaining Issues

### Issue: No ICF Knowledge Base Data
The ICF certification has no documents ingested into the knowledge base.

**Evidence:**
```bash
sqlite3 test_database.db "SELECT DISTINCT metadata FROM knowledge_base_chunks WHERE metadata LIKE '%icf%';"
# Returns: No rows
```

**Impact:**
- RAG retrieval will return 0 results for ICF certification
- Questions will fall back to template-based generation
- This is NOT a bug in the certification_id filtering - it's a data ingestion issue

**Solution:**
Ingest ICF certification documents:
```python
# Use the knowledge base ingestion endpoint
POST /api/v1/certifications/{cert_id}/ingest
# Upload ICF exam guides, transcripts, etc.
```

---

## 📋 Testing Checklist

- [ ] Application restarted with new code
- [ ] ICF assessment generated
- [ ] Logs show `vector_cert_id=icf-core-competency` (not aws-ml-specialty)
- [ ] RAG retrieval uses correct certification_id
- [ ] No "🚨 CRITICAL" certification mismatches in logs
- [ ] Questions are relevant to ICF certification (once data ingested)

---

## 🎯 Root Cause Analysis

**Why This Happened:**

1. **Hardcoded Test Data:** Developer hardcoded "aws-ml-specialty" during testing and left TODO comment
2. **Incomplete Resource Loading:** collection_name wasn't included in cert_resources dict
3. **Missing Data Validation:** No check that collection_name exists before using it
4. **Inadequate Logging:** No visibility into which certification_id was being used

**Prevention:**

1. ✅ Added comprehensive logging to track certification_id at every step
2. ✅ Added fallback logic to derive certification_id from name
3. ✅ Added warnings when collection_name is missing
4. ✅ Fixed all hardcoded certification values

---

## 📝 Next Steps

1. **RESTART APPLICATION** (required to load fixes)
2. **Test with ICF certification** (should use icf-core-competency, not aws-ml-specialty)
3. **Ingest ICF documents** into knowledge base (separate task)
4. **Monitor logs** for any remaining issues

---

**Bugs Fixed:** 2025-10-19
**Critical Severity:** All RAG retrievals were using wrong certification
**Impact:** 100% of assessments affected
**Resolution:** Hardcoded value removed + logging added + database updated
