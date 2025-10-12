# RAG Certification ID Mapping Solution

## Problem Summary

**Issue**: RAG retrieval returned 0 chunks even though 45 embeddings exist in ChromaDB.

**Root Cause**: UUID vs String Code Mismatch
- **Application Database** (PostgreSQL/SQLite): Uses UUID as certification ID
  - Example: `455dae60-065c-4038-b3df-6d769b955dbb`
- **Vector Database** (ChromaDB): Uses string code as certification ID
  - Example: `"aws-ml-specialty"`

**Result**: RAG code queried ChromaDB with UUID, but embeddings stored with string code → 0 results.

---

## Architecture

### Two Database Systems

#### 1. Application Database (SQLite/PostgreSQL)
**Table**: `certification_profiles`

| Field | Type | Purpose | Example |
|-------|------|---------|---------|
| `id` | UUID | Primary key | `455dae60-065c-4038-b3df-6d769b955dbb` |
| `name` | VARCHAR | Display name | `"AWS Machine Learning Specialty"` |
| `collection_name` | VARCHAR | **RAG ID mapping** | `"aws-ml-specialty"` |

#### 2. Vector Database (ChromaDB)
**Location**: `./knowledge-base/embeddings/chroma.sqlite3`

**Collections**:
1. `certification_exam_guides` - Official exam guides
2. `certification_transcripts` - Course transcripts

**Metadata**: Each embedding has `certification_id = "aws-ml-specialty"` (string code)

---

## Solution: Mapping Layer

### Implementation

**File**: `src/service/api/v1/endpoints/workflows.py:2708-2719`

```python
# ✅ Use collection_name (string code) instead of UUID for ChromaDB query
# ChromaDB stores embeddings with certification_id as string code (e.g., "aws-ml-specialty")
# not UUID from certification_profiles table
rag_certification_id = cert_profile.collection_name if cert_profile and cert_profile.collection_name else str(workflow.certification_profile_id)

for query in queries[:3]:  # Top 3 learning objectives
    result = await rag_kb.retrieve_context_for_assessment(
        query=query,
        certification_id=rag_certification_id,  # Uses string code, not UUID
        k=6,
        balance_sources=True
    )
```

### How It Works

1. **Retrieve Certification Profile** (line 2637-2642):
   ```python
   cert_profile = await db.get(CertificationProfile, workflow.certification_profile_id)
   ```

2. **Extract String Code** (line 2711):
   ```python
   rag_certification_id = cert_profile.collection_name  # "aws-ml-specialty"
   ```

3. **Query ChromaDB with String Code** (line 2716):
   ```python
   certification_id=rag_certification_id  # NOT UUID
   ```

4. **Fallback to UUID** (if collection_name is NULL):
   ```python
   rag_certification_id = cert_profile.collection_name if cert_profile.collection_name else str(workflow.certification_profile_id)
   ```

---

## Database Updates

### Standardize collection_name Field

Updated certification profiles to use consistent string codes:

```sql
-- AWS Machine Learning Specialty
UPDATE certification_profiles
SET collection_name = 'aws-ml-specialty'
WHERE id = '455dae60065c4038b3df6d769b955dbb';

-- AWS Solutions Architect Associate (if needed)
UPDATE certification_profiles
SET collection_name = 'aws-saa-c03'
WHERE id = '59596658655141f4ba61c6e84a5a8100';
```

### Verify Mapping

```sql
SELECT
    cp.id as uuid,
    cp.name,
    cp.collection_name as rag_string_code
FROM certification_profiles cp;
```

**Result**:
| uuid | name | rag_string_code |
|------|------|-----------------|
| 455dae60-... | AWS Machine Learning Specialty | `aws-ml-specialty` |
| 59596658-... | AWS Solution Architect Associate | `aws-saa-c03` |

---

## Enhanced Logging

### New Log Field: `certification_id_used`

Shows which ID was actually used for RAG query:

```json
{
  "event": "rag_context_collected_for_presentation_prompt",
  "workflow_id": "d818edd4-cb61-4d3a-ad2c-07aa2f325496",
  "certification_id_used": "aws-ml-specialty",  // ← NEW FIELD
  "queries_used": ["Understand core Data Engineering principles", ...],
  "chunks_retrieved": 18,
  "total_chars": 5432
}
```

**Purpose**: Allows operators to verify the correct certification ID is being used for RAG queries.

---

## Testing

### Before Fix
```json
{
  "event": "rag_context_collected_for_presentation_prompt",
  "chunks_retrieved": 0,
  "total_chars": 0,
  "retrieval_duration_seconds": 5.036473,
  "certification_id_used": "455dae60065c4038b3df6d769b955dbb"  // UUID (wrong)
}
```
**Problem**: UUID doesn't match ChromaDB metadata → 0 results

### After Fix (Expected)
```json
{
  "event": "rag_context_collected_for_presentation_prompt",
  "chunks_retrieved": 18,
  "total_chars": 5432,
  "retrieval_duration_seconds": 1.234,
  "certification_id_used": "aws-ml-specialty"  // String code (correct)
}
```
**Success**: String code matches ChromaDB metadata → chunks retrieved

---

## Verification Queries

### Check ChromaDB Embeddings
```sql
-- Count embeddings by certification
sqlite3 ./knowledge-base/embeddings/chroma.sqlite3 "
SELECT DISTINCT string_value as certification_id, COUNT(*) as embedding_count
FROM embedding_metadata
WHERE key = 'certification_id'
GROUP BY string_value;
"
```

**Expected Output**:
```
aws-ml-specialty|45
```

### Check Application Database
```sql
-- Verify collection_name mapping
sqlite3 test_database.db "
SELECT id, name, collection_name
FROM certification_profiles;
"
```

**Expected Output**:
```
455dae60065c4038b3df6d769b955dbb|AWS Machine Learning Specialty|aws-ml-specialty
```

### Verify Match
The `collection_name` in the application database should match the `certification_id` in ChromaDB embeddings.

✅ `collection_name` = "aws-ml-specialty"
✅ ChromaDB `certification_id` = "aws-ml-specialty"
✅ **MATCH** → RAG retrieval will work

---

## Best Practices

### For New Certifications

When creating a new certification profile:

1. **Choose a consistent string code**:
   - Format: `{provider}-{exam-code}` (lowercase, hyphenated)
   - Examples: `aws-saa-c03`, `azure-az-104`, `gcp-pca`

2. **Set collection_name during creation**:
   ```python
   cert_profile = CertificationProfile(
       name="AWS Solutions Architect Associate",
       collection_name="aws-saa-c03",  # Set this!
       ...
   )
   ```

3. **Use same string code when ingesting documents**:
   ```python
   await rag_kb.ingest_certification_materials(
       certification_id="aws-saa-c03",  # Must match collection_name
       documents=[...]
   )
   ```

### For Existing Certifications

If `collection_name` is NULL or incorrect:

1. **Find ChromaDB certification_id**:
   ```sql
   SELECT DISTINCT string_value FROM embedding_metadata WHERE key = 'certification_id';
   ```

2. **Update certification profile**:
   ```sql
   UPDATE certification_profiles
   SET collection_name = '<chromadb-certification-id>'
   WHERE id = '<uuid>';
   ```

---

## Troubleshooting

### RAG Returns 0 Chunks

**Check 1**: Verify collection_name is set
```sql
SELECT id, name, collection_name FROM certification_profiles WHERE id = '<workflow-cert-id>';
```
- If NULL → Set collection_name

**Check 2**: Verify ChromaDB has embeddings
```sql
SELECT COUNT(*) FROM embedding_metadata WHERE key = 'certification_id' AND string_value = '<collection-name>';
```
- If 0 → Ingest documents for this certification

**Check 3**: Verify IDs match
```sql
-- Application DB
SELECT collection_name FROM certification_profiles WHERE id = '<uuid>';

-- ChromaDB
SELECT DISTINCT string_value FROM embedding_metadata WHERE key = 'certification_id';
```
- If don't match → Update collection_name to match ChromaDB

**Check 4**: Check logs for `certification_id_used`
```json
{
  "event": "rag_context_collected_for_presentation_prompt",
  "certification_id_used": "???"  // Should be string code, not UUID
}
```
- If UUID → Mapping layer not working (check cert_profile loaded correctly)

---

## Related Files

- **Model**: `src/models/certification.py` (CertificationProfile model)
- **RAG Base**: `src/knowledge/base.py` (retrieve_context_for_assessment)
- **RAG Embeddings**: `src/knowledge/embeddings.py` (ChromaDB queries)
- **Workflow**: `src/service/api/v1/endpoints/workflows.py:2708-2719` (mapping layer)

---

## Commit History

1. **Database Update**: Set `collection_name = "aws-ml-specialty"` for AWS ML cert
2. **Code Update**: Added mapping layer to use `collection_name` instead of UUID
3. **Logging Update**: Added `certification_id_used` field to RAG logs

---

**Date**: 2025-10-12
**Status**: ✅ Implemented
**Next Step**: Test course generation and verify `chunks_retrieved > 0`
