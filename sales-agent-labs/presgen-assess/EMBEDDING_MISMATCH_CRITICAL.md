# 🚨 CRITICAL: Embedding Function Mismatch

## Problem
File uploads fail processing because of **embedding function inconsistency** between components.

## Root Cause

### Component 1: Knowledge Base (RAG) - `src/knowledge/embeddings.py`
**Uses:** `OpenAIEmbeddingFunctionV1` with OpenAI API (`text-embedding-3-small`)
```python
self.embedding_function = OpenAIEmbeddingFunctionV1(
    api_key=settings.openai_api_key,
    model_name="text-embedding-3-small"
)
```

### Component 2: File Upload Processing - `src/service/chromadb_schema.py`
**Tries:** `SentenceTransformerEmbeddingFunction` (FAILS - not installed)
**Falls back to:** `DefaultEmbeddingFunction()`

```python
try:
    self.embedding_function = embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name=embed_model  # "text-embedding-3-small"
    )
except ValueError as err:
    # ❌ Falls back to DEFAULT (incompatible with OpenAI embeddings!)
    self.embedding_function = embedding_functions.DefaultEmbeddingFunction()
```

## Impact

### When Documents are Uploaded:
1. Upload succeeds ✅
2. Processing starts ✅
3. Chunks created ✅
4. Embeddings generated with `DefaultEmbeddingFunction` ❌
5. Stored in ChromaDB ✅
6. **BUT:** Embeddings are INCOMPATIBLE with RAG retrieval!

### When RAG Queries Documents:
1. Query embedded with `OpenAIEmbeddingFunctionV1` ✅
2. Searches ChromaDB collections ✅
3. **FINDS NO MATCHES** ❌ (different embedding space!)
4. Returns 0 results ❌

## Evidence

### Warning in Logs:
```
SentenceTransformerEmbeddingFunction unavailable (The sentence_transformers python package is not installed. Please install it with `pip install sentence_transformers`); using default embedding function.
```

### Database Shows Failed Processing:
```sql
SELECT id, original_filename, processing_status FROM knowledge_base_documents
WHERE certification_profile_id='36b361410f79449fa6bfb2ec59fddcd1';

8a67941a... | ACC Exam Preparation Study Guide.txt | failed
15038b18... | ACC ICF Preparation transcript.txt    | failed
```

## Solutions

### Option 1: Use OpenAI Embeddings Everywhere (RECOMMENDED)
**Change `chromadb_schema.py` to use OpenAI embeddings:**

```python
# BEFORE (chromadb_schema.py:175-185):
try:
    self.embedding_function = embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name=embed_model
    )
except ValueError as err:
    self.embedding_function = embedding_functions.DefaultEmbeddingFunction()

# AFTER:
from openai import OpenAI

class OpenAIEmbeddingFunctionV1:
    """Custom OpenAI embedding function compatible with OpenAI v1.0+ API."""
    def __init__(self, api_key: str, model_name: str = "text-embedding-3-small"):
        self.client = OpenAI(api_key=api_key)
        self.model_name = model_name

    def __call__(self, input_texts: List[str]) -> List[List[float]]:
        response = self.client.embeddings.create(
            input=input_texts,
            model=self.model_name
        )
        return [data.embedding for data in response.data]

# Use OpenAI embeddings
self.embedding_function = OpenAIEmbeddingFunctionV1(
    api_key=settings.openai_api_key,
    model_name="text-embedding-3-small"
)
```

**Pros:**
- ✅ Consistent with RAG system
- ✅ No need to install sentence_transformers
- ✅ OpenAI embeddings are already used elsewhere

**Cons:**
- ❌ Costs money (OpenAI API calls)
- ❌ Requires internet connection

### Option 2: Install sentence_transformers
```bash
pip install sentence_transformers
```

**Then update BOTH systems to use sentence_transformers.**

**Pros:**
- ✅ Free (no API costs)
- ✅ Works offline

**Cons:**
- ❌ Requires changing RAG system too
- ❌ Large model downloads (~500MB+)
- ❌ Slower on CPU

### Option 3: Use DefaultEmbeddingFunction Everywhere
**Change `embeddings.py` to use DefaultEmbeddingFunction.**

**Pros:**
- ✅ Free
- ✅ Fast
- ✅ No dependencies

**Cons:**
- ❌ Lower quality embeddings
- ❌ Worse search relevance

## Recommended Fix: Option 1 (Use OpenAI Everywhere)

### Step 1: Update chromadb_schema.py
**File:** `src/service/chromadb_schema.py`

Add OpenAI embedding function class and use it:
```python
# Add at top of file
from openai import OpenAI
from src.common.config import settings

# Add class (same as in embeddings.py)
class OpenAIEmbeddingFunctionV1:
    """Custom OpenAI embedding function compatible with OpenAI v1.0+ API."""
    def __init__(self, api_key: str, model_name: str = "text-embedding-3-small"):
        self.client = OpenAI(api_key=api_key)
        self.model_name = model_name

    def __call__(self, input_texts: List[str]) -> List[List[float]]:
        try:
            response = self.client.embeddings.create(
                input=input_texts,
                model=self.model_name
            )
            return [data.embedding for data in response.data]
        except Exception as e:
            logging.getLogger(__name__).error(f"OpenAI embedding failed: {e}")
            raise

# In ChromaDBSchemaManager.__init__ (line 170):
def __init__(self, chroma_client: chromadb.Client, embed_model: str = "text-embedding-3-small"):
    self.client = chroma_client
    self.embed_model = embed_model

    # ✅ Use OpenAI embeddings consistently
    self.embedding_function = OpenAIEmbeddingFunctionV1(
        api_key=settings.openai_api_key,
        model_name=embed_model
    )
```

### Step 2: Delete Existing Incompatible Data
```bash
# Clear ChromaDB collections with incompatible embeddings
sqlite3 test_database.db "DELETE FROM knowledge_base_documents WHERE processing_status='failed';"

# Or delete the entire ChromaDB directory and re-ingest
rm -rf chroma_db/
```

### Step 3: Re-upload Files
Upload certification files again - they should now process successfully with consistent embeddings.

### Step 4: Verify
```bash
# Check processing status
sqlite3 test_database.db "SELECT id, original_filename, processing_status FROM knowledge_base_documents ORDER BY created_at DESC LIMIT 5;"

# Should show: processing_status='completed'
```

## Testing

### Test 1: Upload File
```bash
# Upload via UI
# Check logs for:
grep "OpenAIEmbeddingFunctionV1\|embedding" src/logs/*.log

# Should NOT see "SentenceTransformerEmbeddingFunction unavailable"
```

### Test 2: RAG Retrieval
```python
# After upload, test RAG query
from src.knowledge.embeddings import VectorDatabaseManager

vector_db = VectorDatabaseManager()
results = await vector_db.retrieve_context(
    query="ICF coaching ethics",
    certification_id="icf-core-competency",
    k=5
)

print(f"Found {len(results)} chunks")
# Should find chunks from uploaded files
```

## Files to Modify

| File | Change | Lines |
|------|--------|-------|
| `src/service/chromadb_schema.py` | Add OpenAIEmbeddingFunctionV1 class + use it | 170-185 |

## Rollback Plan
If issues arise, revert to sentence_transformers approach:
```bash
pip install sentence_transformers torch
# Revert chromadb_schema.py changes
# Re-upload all files
```

---

**Fix Priority:** HIGH
**Impact:** File uploads fail, RAG retrieval returns 0 results
**Estimated Time:** 15 minutes
**Risk:** Low (only affects new uploads, existing data already failed)
