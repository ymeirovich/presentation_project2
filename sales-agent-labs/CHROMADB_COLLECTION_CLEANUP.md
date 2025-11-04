# ChromaDB Collection Cleanup - November 4, 2025

## Issue Discovered

After implementing the fail-fast prevention code in `chromadb_schema.py`, discovered a second problematic ChromaDB collection with incorrect embedding dimensions.

## Collections Audit

### Collection: `assess__aws-ml-specialty_v1.0`
- **Status**: ✅ Correct
- **Documents**: 1480
- **Embedding Dimension**: 1536 (OpenAI text-embedding-3-small)
- **Action**: Kept

### Collection: `assess__aws-machine-learning-specialty-2_v1.0`
- **Status**: ❌ Incorrect
- **Documents**: 1443
- **Embedding Dimension**: 128 (DefaultEmbeddingFunction)
- **Action**: Deleted

## Why This Collection Had Wrong Dimensions

This collection was created when:
1. OPENAI_API_KEY was not set or invalid
2. `chromadb_schema.py` fell back to DefaultEmbeddingFunction (128 dimensions)
3. Collection was created with 128-dimensional embeddings
4. Future uploads with OpenAI embeddings (1536 dimensions) would fail with dimension mismatch

## Actions Taken

### 1. Deleted Problematic Collection
```python
import chromadb
client = chromadb.PersistentClient(path='/app/data/chroma')
client.delete_collection('assess__aws-machine-learning-specialty-2_v1.0')
```

### 2. Verified Environment
- ✅ OPENAI_API_KEY is set in container
- ✅ Fail-fast code prevents DefaultEmbeddingFunction fallback
- ✅ Only correct collection remains

## Current State

### ChromaDB Collections (After Cleanup)
```
📦 ChromaDB Collections:
  - assess__aws-ml-specialty_v1.0: 1480 documents
  ✅ Embedding dimension: 1536 (OpenAI text-embedding-3-small)
```

### Prevention Measures
With the fail-fast code in `chromadb_schema.py` (commit 1923fa8), this issue cannot happen again:
- No fallback to DefaultEmbeddingFunction
- Raises `ValueError` if OPENAI_API_KEY is missing
- Raises `RuntimeError` if OpenAI embedding initialization fails

## Next File Upload Behavior

When a file is uploaded to a certification that had the deleted collection:
1. ✅ System validates OPENAI_API_KEY exists
2. ✅ Collection does not exist, will be created fresh
3. ✅ New collection created with OpenAI embeddings (1536 dimensions)
4. ✅ File processes successfully
5. ✅ UI shows "Completed" status

## Files Modified
- `data/assess/chroma/chroma.sqlite3` - Collection metadata updated
- `data/assess/presgen_assess.db` - Database state after cleanup

## Related Documentation
- [EMBEDDING_DIMENSION_MISMATCH_FIX.md](EMBEDDING_DIMENSION_MISMATCH_FIX.md) - Original fix
- [presgen-assess/src/service/chromadb_schema.py](presgen-assess/src/service/chromadb_schema.py) - Fail-fast implementation
