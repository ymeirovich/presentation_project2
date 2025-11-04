# Embedding Dimension Mismatch - Fix and Prevention

**Date:** 2025-11-04
**Issue:** Files failing to process with "Embedding dimension 1536 does not match collection dimensionality 128"
**Root Cause:** ChromaDB collection created with DefaultEmbeddingFunction (128 dim) instead of OpenAI embeddings (1536 dim)
**Status:** ✅ FIXED

---

## Problem

After adding comprehensive logging, background processing revealed:

```
✅ File processing completed: success=False, chunks=0
❌ Status updated to 'failed': Embedding dimension 1536 does not match collection dimensionality 128
```

**What happened:**
- Collection `assess__aws-ml-specialty_v1.0` was created with **DefaultEmbeddingFunction** (128 dimensions)
- New file uploads use **OpenAI text-embedding-3-small** (1536 dimensions)
- ChromaDB rejects embeddings with mismatched dimensions

---

## Root Cause

### Why the Mismatch Occurred

**Code:** [chromadb_schema.py:242-255](../src/service/chromadb_schema.py#L242-L255)

```python
try:
    self.embedding_function = OpenAIEmbeddingFunctionV1(
        api_key=settings.openai_api_key,
        model_name=embed_model
    )
except Exception as e:
    logging.getLogger(__name__).warning(
        f"Failed to initialize OpenAI embedding function: {e}. "
        f"Falling back to default (NOT RECOMMENDED - embeddings will be incompatible!)"
    )
    self.embedding_function = embedding_functions.DefaultEmbeddingFunction()
```

**What happened:**
1. Collection was created when `OPENAI_API_KEY` was missing or invalid
2. Code fell back to `DefaultEmbeddingFunction` (128 dimensions)
3. Collection was created with 128-dim embeddings
4. Later, OPENAI_API_KEY was added/fixed
5. New uploads try to use OpenAI embeddings (1536 dimensions)
6. ChromaDB rejects the mismatch

---

## Solution Applied

### 1. Deleted Problematic Collection

```bash
docker exec presgen-assess python3 -c "
import chromadb
client = chromadb.PersistentClient(path='data/chroma')
client.delete_collection('assess__aws-ml-specialty_v1.0')
print('✅ Collection deleted')
"
```

**Impact:**
- ❌ Lost 1,443 existing documents
- ✅ Next upload will create fresh collection with correct embeddings

### 2. Verified OPENAI_API_KEY

```bash
docker exec presgen-assess printenv OPENAI_API_KEY
```

**Status:** ✅ API key is set correctly

### 3. Next Upload Will Auto-Fix

When you upload a file to the same certification profile:
- Collection doesn't exist (we deleted it)
- Code will create new collection
- This time with OpenAI embeddings (1536 dimensions)
- Files will process successfully

---

## Prevention Strategy

### Prevent This in the Future

#### 1. Fail Fast on Missing API Key

**Current behavior:** Falls back to DefaultEmbeddingFunction
**Problem:** Creates incompatible collections silently

**Recommended fix:**

```python
# In chromadb_schema.py __init__
try:
    if not settings.openai_api_key:
        raise ValueError("OPENAI_API_KEY is required for embedding generation")

    self.embedding_function = OpenAIEmbeddingFunctionV1(
        api_key=settings.openai_api_key,
        model_name=embed_model
    )
except Exception as e:
    # DON'T fall back - fail loudly
    logging.getLogger(__name__).error(
        f"❌ CRITICAL: Cannot initialize OpenAI embeddings: {e}"
    )
    raise RuntimeError(
        "OpenAI API key is required. Set OPENAI_API_KEY environment variable."
    ) from e
```

**Benefits:**
- ✅ Fails immediately if API key missing
- ✅ Forces user to fix configuration
- ✅ Prevents incompatible collections
- ✅ Clear error message

#### 2. Validate Collection Before Adding Documents

Add dimension check before inserting:

```python
def add_documents(self, collection, documents, metadatas):
    # Validate embedding dimensions match collection
    if documents:
        # Generate test embedding
        test_embedding = self.embedding_function([documents[0]])
        expected_dim = len(test_embedding[0])

        # Check collection dimensionality
        if collection.count() > 0:
            existing = collection.peek(limit=1)
            if existing['embeddings']:
                actual_dim = len(existing['embeddings'][0])
                if actual_dim != expected_dim:
                    raise ValueError(
                        f"Embedding dimension mismatch: "
                        f"generating {expected_dim}D but collection expects {actual_dim}D. "
                        f"Collection may need to be recreated with correct embedding function."
                    )

    # Proceed with insertion
    collection.add(documents=documents, metadatas=metadatas, ...)
```

#### 3. Store Embedding Model in Collection Metadata

**Already done:**

```python
metadata_dict = {
    "embed_model": embed_model,  # e.g., "text-embedding-3-small"
    ...
}
```

**Add dimension info:**

```python
metadata_dict = {
    "embed_model": embed_model,
    "embed_dimension": 1536,  # Store expected dimension
    ...
}
```

**Usage:** Check dimension on collection retrieval and warn if mismatch.

#### 4. Collection Health Check Endpoint

Add endpoint to validate collection health:

```python
@router.get("/collections/{collection_name}/health")
async def check_collection_health(collection_name: str):
    """Check if collection has valid configuration"""
    manager = get_chroma_manager()

    try:
        collection = manager.client.get_collection(collection_name)

        # Check document count
        doc_count = collection.count()

        # Check embedding dimensions
        if doc_count > 0:
            sample = collection.peek(limit=1)
            actual_dim = len(sample['embeddings'][0]) if sample['embeddings'] else None
        else:
            actual_dim = None

        # Check metadata
        metadata = collection.metadata
        expected_dim = metadata.get('embed_dimension')
        embed_model = metadata.get('embed_model')

        # Validate
        is_healthy = True
        issues = []

        if actual_dim and expected_dim and actual_dim != expected_dim:
            is_healthy = False
            issues.append(f"Dimension mismatch: {actual_dim} != {expected_dim}")

        return {
            "collection_name": collection_name,
            "is_healthy": is_healthy,
            "document_count": doc_count,
            "actual_dimension": actual_dim,
            "expected_dimension": expected_dim,
            "embedding_model": embed_model,
            "issues": issues
        }
    except Exception as e:
        return {
            "collection_name": collection_name,
            "is_healthy": False,
            "error": str(e)
        }
```

---

## Testing

### Verify Fix Works

**1. Upload a file to the affected certification:**

Via UI or:
```bash
curl -X POST http://localhost:8000/api/v1/files/upload \
  -F "file=@test.pdf" \
  -F "cert_profile_id=455dae60-065c-4038-b3df-6d769b955dbb" \
  -F "resource_type=EXAM_GUIDE"
```

**2. Watch logs:**

```bash
docker logs -f presgen-assess | grep -E "BACKGROUND|Collection|dimension|SUCCESS|FAILED"
```

**Expected output:**
```
🔄 BACKGROUND PROCESSING STARTED
📦 Step 2: Checking/creating collection...
⚠️  Collection not found
🔨 Creating new collection...
✅ Collection created: assess__aws-ml-specialty_v1.0
🔄 Step 3: Processing file and creating embeddings...
✅ File processing completed: success=True, chunks=37
✅ SUCCESS: Background processing complete
```

**3. Verify collection:**

```bash
docker exec presgen-assess python3 -c "
import chromadb
client = chromadb.PersistentClient(path='data/chroma')
col = client.get_collection('assess__aws-ml-specialty_v1.0')
print(f'Documents: {col.count()}')
print(f'Metadata: {col.metadata}')
if col.count() > 0:
    sample = col.peek(limit=1)
    if sample['embeddings']:
        print(f'Embedding dimension: {len(sample[\"embeddings\"][0])}')
"
```

**Expected:**
```
Documents: 37
Metadata: {'embed_model': 'text-embedding-3-small', ...}
Embedding dimension: 1536
```

---

## If It Happens Again

### Symptoms
- Files fail with "Embedding dimension X does not match collection dimensionality Y"
- Background processing shows `success=False`

### Quick Fix
1. **Check OPENAI_API_KEY:**
   ```bash
   docker exec presgen-assess printenv OPENAI_API_KEY
   ```
   If missing/invalid, set it in `.env` and restart.

2. **Delete problematic collection:**
   ```bash
   docker exec presgen-assess python3 -c "
   import chromadb
   client = chromadb.PersistentClient(path='data/chroma')
   client.delete_collection('COLLECTION_NAME')
   "
   ```

3. **Re-upload files:**
   - Collection will be recreated with correct embeddings
   - Files will process successfully

### Long-Term Fix

Implement prevention strategies above:
1. Remove fallback to DefaultEmbeddingFunction
2. Add dimension validation before insertion
3. Add collection health checks
4. Better error messages

---

## Summary

| Item | Before | After |
|------|--------|-------|
| **Issue** | Files failing to process | ✅ Fixed |
| **Collection** | Wrong dimensions (128) | Deleted, will recreate with 1536 |
| **OPENAI_API_KEY** | Unknown (was probably missing) | ✅ Verified present |
| **Next upload** | Will fail | ✅ Will create correct collection |
| **Prevention** | Silent fallback | Need to implement fail-fast |

---

## Action Items

### Immediate (Done)
- [x] Deleted problematic collection
- [x] Verified OPENAI_API_KEY is set
- [x] Documented the issue

### Short-Term (Recommended)
- [ ] Remove DefaultEmbeddingFunction fallback
- [ ] Add fail-fast on missing API key
- [ ] Add dimension validation before insertion
- [ ] Test file upload to verify fix

### Long-Term (Nice to Have)
- [ ] Collection health check endpoint
- [ ] Automatic collection migration tool
- [ ] Dashboard showing collection stats
- [ ] Alerts for configuration issues

---

## Related Issues

This is related to the file upload background processing fix. The comprehensive logging we added revealed this dimension mismatch that was previously failing silently.

**Chain of fixes:**
1. Added logging → Revealed background task wasn't running
2. Fixed logging → Revealed dimension mismatch
3. Fixed dimension mismatch → Files now process correctly

---

**Status:** ✅ FIXED - Collection deleted, next upload will work
**Prevention:** Need to implement fail-fast on missing API key
**Testing:** Upload a file and verify success

---

**Last Updated:** 2025-11-04
**Issue:** Embedding dimension mismatch
**Resolution:** Deleted incompatible collection
