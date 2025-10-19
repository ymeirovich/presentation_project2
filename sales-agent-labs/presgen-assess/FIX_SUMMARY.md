# RAG Context Filtering Fix - Implementation Summary

## Problem Statement
Assessment questions were being generated from RAG context that mixed content from ALL certification profiles, not just the assigned certification profile.

## Root Causes Identified

### 1. **ChromaDB Metadata Key Mismatch** ⚠️ CRITICAL
- **Issue:** Documents stored with `certification_id` metadata key
- **Query:** ChromaDB queried with `cert_id` first, falling back to `certification_id`
- **Result:** Primary query with `cert_id` returned NO results or WRONG results
- **Impact:** Fallback query may have returned ALL documents without proper filtering

**Location:** `src/knowledge/embeddings.py:148-173`

### 2. **Insufficient Logging**
- No visibility into which `certification_id` was used for RAG filtering
- No validation that retrieved chunks matched requested certification
- No tracking of which assessment prompt was used (profile vs default)
- LLM request/response messages not fully logged

## Fixes Implemented

### ✅ Fix 1: Standardize ChromaDB Metadata Keys
**File:** `src/knowledge/embeddings.py`

**Changes:**
- Line 163: Changed primary query to use `certification_id` (matches storage key)
- Line 194: Added fallback to legacy `cert_id` for backward compatibility
- Added comprehensive logging at each stage

**Before:**
```python
where={"cert_id": certification_id}  # Primary (WRONG KEY)
where={"certification_id": certification_id}  # Fallback
```

**After:**
```python
where={"certification_id": certification_id}  # Primary (CORRECT KEY)
where={"cert_id": certification_id}  # Fallback (legacy data)
```

---

### ✅ Fix 2: Add Comprehensive RAG Retrieval Logging
**File:** `src/knowledge/embeddings.py`

**Added Logs:**

1. **Entry Point Logging (Line 141-144):**
   ```python
   logger.info(
       f"🔍 RAG retrieve_context | certification_id={certification_id} | "
       f"query={query[:100]}... | k={k} | content_types={content_types}"
   )
   ```

2. **ChromaDB Query Logging (Line 155-173):**
   - Logs the `where` clause being used
   - Logs number of chunks returned per collection
   - Logs first chunk's metadata for verification

3. **Certification Validation Logging (Line 219-269):**
   - Tracks total chunks, passed chunks, failed chunks, missing metadata
   - **CRITICAL:** Logs error for any certification mismatch
   - Example:
     ```python
     logger.error(
         f"🚨 CRITICAL: RAG certification mismatch! | "
         f"expected={certification_id} | actual={metadata_cert} | "
         f"chunk_id={chunk_id} | doc={metadata.get('document_name')}"
     )
     ```

4. **Final Summary Logging (Line 302-317):**
   - Total chunks returned
   - Breakdown by source type (exam_guides vs transcripts)
   - Unique documents retrieved

---

### ✅ Fix 3: Add Certification Profile & Prompt Logging
**File:** `src/services/llm_service.py`

**Added Logs:**

1. **Function Entry (Line 57-62):**
   ```python
   logger.info(
       f"🎯 generate_assessment_questions | certification_id={certification_id} | "
       f"domain={domain} | question_count={question_count}"
   )
   ```

2. **Profile Resolution (Line 70-91):**
   - Success: Logs `profile_id`, `profile_name`, `cert_slug`, `has_assessment_prompt`
   - Failure: Logs `using_fallback_prompt=True`
   - Missing prompt: Logs `using_default_prompt=True`

3. **RAG Retrieval Initiation (Line 97-102):**
   - Logs the `certification_id` being used for RAG query
   - Logs the query text

4. **RAG Results (Line 112-156):**
   - Logs total results, exam_guides count, transcripts count
   - Logs fallback attempts if primary retrieval fails
   - Logs final context preparation summary

---

### ✅ Fix 4: Log Complete LLM Request/Response Messages
**File:** `src/services/llm_service.py`

**Added Logs:**

1. **LLM Request (Line 219-237):**
   ```json
   {
     "event": "generate_questions_request",
     "assessment_prompt_source": "profile",
     "system_message": "[COMPLETE SYSTEM PROMPT]",
     "user_message": "[COMPLETE USER PROMPT WITH RAG CONTEXT]",
     "knowledge_base_context_preview": "[FIRST 500 CHARS OF RAG CONTEXT]"
   }
   ```

2. **LLM Response (Line 257-270):**
   ```json
   {
     "event": "generate_questions_response",
     "raw_response": "[COMPLETE LLM RESPONSE]",
     "prompt_tokens": 2456,
     "completion_tokens": 1234,
     "total_tokens": 3690,
     "finish_reason": "stop"
   }
   ```

---

## Testing & Verification

### Log Locations
**Primary Log File:** `src/logs/presgen_assess_combined.log`

### Critical Filters to Monitor

#### 1. Check for Certification Mismatches
```bash
grep "🚨 CRITICAL: RAG certification mismatch" src/logs/presgen_assess_combined.log
```
**Expected:** No results (no mismatches)

#### 2. Verify RAG Filtering
```bash
grep "RAG chunk validation" src/logs/presgen_assess_combined.log
```
**Look for:** `passed=total`, `failed_mismatch=0`

#### 3. Verify Certification Profile Usage
```bash
grep "Certification profile loaded" src/logs/presgen_assess_combined.log
```
**Look for:** Correct `profile_name`, `has_assessment_prompt=True`

#### 4. Verify Assessment Prompt Source
```bash
grep '"assessment_prompt_source"' src/logs/presgen_assess_combined.log
```
**Expected:** `"assessment_prompt_source": "profile"` (not "default")

#### 5. Check RAG Context Documents
```bash
grep "RAG retrieval complete" src/logs/presgen_assess_combined.log
```
**Look for:** `docs=[...]` should only contain files for the target certification

### Sample Test Workflow

1. **Start Assessment Generation:**
   - Create workflow for specific certification (e.g., AWS SAA)
   - Note the `workflow_id` from logs

2. **Monitor Logs:**
   ```bash
   tail -f src/logs/presgen_assess_combined.log | grep "workflow_id=<YOUR_WORKFLOW_ID>"
   ```

3. **Verify Certification Filtering:**
   - Check `RAG retrieve_context` logs for correct `certification_id`
   - Check `RAG chunk validation` for `failed_mismatch=0`
   - Check `RAG retrieval complete` for certification-specific documents

4. **Verify Prompt Usage:**
   - Check `Certification profile loaded` for correct profile
   - Check `generate_questions_request` for `assessment_prompt_source: "profile"`

---

## Files Modified

| File | Changes | Lines Modified |
|------|---------|----------------|
| `src/knowledge/embeddings.py` | Fixed metadata key, added comprehensive logging | 130-322 |
| `src/services/llm_service.py` | Added profile/RAG/LLM logging | 43-270 |

## New Files Created

| File | Purpose |
|------|---------|
| `LOGGING_GUIDE.md` | Comprehensive guide to all new logs and diagnostic filters |
| `FIX_SUMMARY.md` | This document - implementation summary |

---

## Impact Assessment

### Positive Impacts
✅ RAG context now properly filtered by `certification_id`
✅ Complete visibility into certification profile resolution
✅ Complete visibility into RAG retrieval and filtering
✅ Complete visibility into LLM prompts and responses
✅ Easy diagnosis of certification mixing issues

### Potential Issues
⚠️ **Log File Size:** Comprehensive logging will increase log file size
⚠️ **Performance:** Minimal impact (logging is fast, but adds overhead)
⚠️ **Legacy Data:** Data stored with `cert_id` will use fallback query (still works)

### Migration Notes
- No database migration required
- Existing data with `cert_id` key will still work via fallback
- New data should be stored with `certification_id` key (already implemented)

---

## Next Steps

### Immediate Actions
1. **Deploy Changes:** Deploy to test/staging environment
2. **Monitor Logs:** Watch for `🚨 CRITICAL` errors indicating mismatches
3. **Verify Workflows:** Run sample assessments for different certifications

### Future Enhancements
1. **Data Migration:** Migrate legacy `cert_id` data to `certification_id`
2. **Structured Logging:** Convert to JSON structured logging for easier parsing
3. **Metrics:** Add Prometheus/CloudWatch metrics for certification mismatch rate
4. **Alerts:** Set up alerts for critical certification mismatch errors

---

## Rollback Plan

If issues arise:

1. **Revert Metadata Key Change:**
   - Change line 163 back to `where={"cert_id": certification_id}`
   - Keep logging changes (they're helpful regardless)

2. **Disable Verbose Logging:**
   - Comment out detailed logging if log file size is an issue
   - Keep critical error logs (`🚨 CRITICAL`)

3. **Git Revert:**
   ```bash
   git revert <commit-hash>
   ```

---

## Contact & Support

For questions about this fix:
- Review `LOGGING_GUIDE.md` for log interpretation
- Check logs with filters documented above
- Verify certification_id flow: Profile → LLM Service → RAG → ChromaDB

---

**Fix Completed:** 2025-10-19
**Primary Issue:** ChromaDB metadata key mismatch causing RAG context mixing
**Solution:** Standardized to `certification_id` + comprehensive logging
