# Assessment Generation Logging Guide

## Overview
This guide documents the comprehensive logging added to track certification-specific RAG context retrieval and LLM assessment question generation.

## Log File Location
**Primary Log File:** `src/logs/presgen_assess_combined.log`

---

## 🔍 RAG Context Retrieval Logs

### Phase 1: RAG Retrieval Entry Point
**Filter:** `RAG retrieve_context`

**Example:**
```
🔍 RAG retrieve_context | certification_id=aws-solutions-architect-associate | query=Security certification exam questions and concepts... | k=8 | content_types=['exam_guide', 'transcript']
```

**What to check:**
- ✅ `certification_id` matches the expected certification profile
- ✅ Query is relevant to the domain being assessed

---

### Phase 2: ChromaDB Collection Queries
**Filter:** `Querying exam_guides collection` OR `Querying transcripts collection`

**Example:**
```
🔍 Querying exam_guides collection | where={certification_id: aws-solutions-architect-associate} | n_results=4
📊 Query returned 3 chunks from exam_guides | certification_id=aws-solutions-architect-associate
📋 First chunk metadata: cert_id=aws-solutions-architect-associate | doc=aws-saa-exam-guide.pdf | classification=exam_guide
```

**What to check:**
- ✅ `where={certification_id: ...}` uses the correct certification ID
- ✅ Chunks are returned (> 0 chunks)
- ✅ First chunk metadata shows correct `certification_id`
- ⚠️ If "No results with certification_id, trying legacy cert_id" appears, data may be stored with old key

---

### Phase 3: Certification Validation
**Filter:** `RAG chunk validation`

**Example:**
```
✅ RAG chunk validation | collection=exam_guides | total=3 | passed=3 | failed_mismatch=0 | missing_metadata=0 | certification_id=aws-solutions-architect-associate
```

**What to check:**
- ✅ `passed` count matches `total` (no mismatches)
- 🚨 **CRITICAL:** If `failed_mismatch > 0`, RAG context is mixing certifications!
- ⚠️ If `missing_metadata > 0`, some chunks lack certification metadata

**Critical Error Example (Mixed Content):**
```
🚨 CRITICAL: RAG certification mismatch! | expected=aws-solutions-architect-associate | actual=azure-administrator | chunk_id=exam_guide_abc123 | doc=azure-admin-guide.pdf | source_type=exam_guide | collection=exam_guides
```

---

### Phase 4: Final RAG Summary
**Filter:** `RAG retrieval complete`

**Example:**
```
✅ RAG retrieval complete | certification_id=aws-solutions-architect-associate | total_chunks=6 | exam_guides=3 | transcripts=3 | unique_docs=2 | docs=['aws-saa-exam-guide.pdf', 'aws-saa-transcript.md']
📤 Returning top 6 chunks (requested k=8) | certification_id=aws-solutions-architect-associate
```

**What to check:**
- ✅ `total_chunks > 0` (RAG context retrieved)
- ✅ `docs` list contains only files for the target certification
- ✅ Mix of exam_guides and transcripts (if both are available)

---

## 🎯 LLM Service Logs (Assessment Generation)

### Phase 1: Function Entry
**Filter:** `generate_assessment_questions`

**Example:**
```
🎯 generate_assessment_questions | certification_id=36b36141-0f79-449f-a6bf-b2ec59fddcd1 | domain=Security | question_count=5 | difficulty=intermediate | use_rag_context=True
```

**What to check:**
- ✅ `certification_id` is the correct UUID or slug

---

### Phase 2: Certification Profile Resolution
**Filter:** `Certification profile loaded` OR `Certification profile NOT FOUND`

**Success Example:**
```
✅ Certification profile loaded | profile_id=36b36141-0f79-449f-a6bf-b2ec59fddcd1 | profile_name=AWS Solutions Architect Associate | cert_slug=aws-solutions-architect-associate | has_assessment_prompt=True | prompt_length=1234
```

**Failure Example:**
```
⚠️ Certification profile NOT FOUND | identifier=unknown-cert | using_fallback_prompt=True | cert_slug=unknown-cert
```

**What to check:**
- ✅ `profile_name` matches expected certification
- ✅ `has_assessment_prompt=True` (uses certification-specific prompt)
- ⚠️ If `has_assessment_prompt=False`, logs will show `using_default_prompt=True`

---

### Phase 3: RAG Retrieval Initiation
**Filter:** `Initiating RAG retrieval`

**Example:**
```
🔍 Initiating RAG retrieval | certification_id=aws-solutions-architect-associate | query=Security certification exam questions and concepts | k=8 | balance_sources=True
```

**What to check:**
- ✅ `certification_id` matches the cert_slug from profile resolution
- ✅ Query includes the domain name

---

### Phase 4: RAG Retrieval Results
**Filter:** `RAG retrieval result`

**Example:**
```
📊 RAG retrieval result | certification_id=aws-solutions-architect-associate | total_results=6 | exam_guides=3 | transcripts=3
```

**Fallback Example:**
```
⚠️ RAG returned 0 results for cert_slug=aws-saa, trying fallback with profile_id=36b36141-0f79-449f-a6bf-b2ec59fddcd1
✅ Fallback RAG retrieval succeeded | certification_profile_id=36b36141-0f79-449f-a6bf-b2ec59fddcd1 | total_results=4
```

**What to check:**
- ✅ `total_results > 0`
- ⚠️ If fallback occurs, check if cert_slug vs UUID is causing issues

---

### Phase 5: RAG Context Prepared
**Filter:** `RAG context prepared`

**Example:**
```
✅ RAG context prepared | certification_id=aws-solutions-architect-associate | context_chars=8432 | citations_count=6
```

**What to check:**
- ✅ `context_chars > 0` (context retrieved)
- ✅ `citations_count > 0` (sources tracked)

---

### Phase 6: LLM Request (COMPLETE MESSAGES)
**Filter:** `"event": "generate_questions_request"`

**Example (JSON format):**
```json
{
  "event": "generate_questions_request",
  "model": "gpt-4",
  "domain": "Security",
  "question_count": 5,
  "difficulty_level": "intermediate",
  "assessment_prompt_source": "profile",
  "system_message": "You are an expert certification exam question writer...",
  "user_message": "[FULL PROMPT WITH RAG CONTEXT]",
  "knowledge_base_context_preview": "=== OFFICIAL EXAM GUIDE CONTENT ===\n1. AWS IAM Best Practices..."
}
```

**What to check:**
- ✅ `assessment_prompt_source: "profile"` (using certification-specific prompt, not default)
- ✅ `user_message` contains RAG context from correct certification
- ✅ `knowledge_base_context_preview` shows relevant content

---

### Phase 7: LLM Response (COMPLETE RESPONSE)
**Filter:** `"event": "generate_questions_response"`

**Example (JSON format):**
```json
{
  "event": "generate_questions_response",
  "model": "gpt-4",
  "prompt_tokens": 2456,
  "completion_tokens": 1234,
  "total_tokens": 3690,
  "finish_reason": "stop",
  "raw_response": "{\"questions\": [{\"question_text\": \"...\", ...}]}"
}
```

**What to check:**
- ✅ `finish_reason: "stop"` (completed successfully)
- ✅ `raw_response` contains valid JSON with questions

---

## 🔎 Quick Diagnostic Filters

### Find All Logs for a Specific Workflow
```bash
grep "workflow_id=a2e71dde-8c48-4cd9-8371-2aee5e5b391d" presgen_assess_combined.log
```

### Check RAG Certification Filtering
```bash
grep "RAG retrieve_context\|Querying.*collection\|RAG chunk validation\|RAG retrieval complete" presgen_assess_combined.log
```

### Check Certification Mismatches (CRITICAL)
```bash
grep "🚨 CRITICAL: RAG certification mismatch" presgen_assess_combined.log
```

### Check LLM Request/Response for Certification
```bash
grep '"event": "generate_questions_request"\|"event": "generate_questions_response"' presgen_assess_combined.log | python3 -m json.tool
```

### Check Assessment Prompt Source
```bash
grep "assessment_prompt_source\|using_default_prompt\|has_assessment_prompt" presgen_assess_combined.log
```

### Verify ChromaDB Metadata Keys
```bash
grep "First chunk metadata" presgen_assess_combined.log
```

---

## 🚨 Common Issues and How to Diagnose

### Issue 1: RAG Context Mixing Certifications

**Symptoms:**
- `failed_mismatch > 0` in chunk validation logs
- `🚨 CRITICAL: RAG certification mismatch` errors

**Diagnosis:**
1. Check ChromaDB query logs: `grep "Querying.*collection" presgen_assess_combined.log`
2. Verify `where={certification_id: ...}` matches expected value
3. Check chunk metadata: `grep "First chunk metadata" presgen_assess_combined.log`
4. Look for mismatches: `grep "🚨 CRITICAL" presgen_assess_combined.log`

**Solution:**
- Fixed: ChromaDB now uses `certification_id` as primary filter key
- Chunks are validated post-retrieval
- Mismatched chunks are rejected

---

### Issue 2: Assessment Prompt Not Using Certification Profile

**Symptoms:**
- `assessment_prompt_source: "default"` in LLM request logs
- `using_default_prompt=True` warnings

**Diagnosis:**
1. Check profile loading: `grep "Certification profile loaded" presgen_assess_combined.log`
2. Check prompt availability: `grep "has_assessment_prompt" presgen_assess_combined.log`

**Solution:**
- Verify certification profile has `assessment_prompt` field populated in database
- Check profile_id/slug resolution

---

### Issue 3: No RAG Context Retrieved

**Symptoms:**
- `total_results=0` in RAG retrieval logs
- `context_chars=0` in RAG context prepared logs

**Diagnosis:**
1. Check if data is ingested: `grep "Stored.*chunks" presgen_assess_combined.log`
2. Verify certification_id used for ingestion matches query
3. Check for cert_id vs certification_id key mismatch

**Solution:**
- Re-ingest documents with correct `certification_id` metadata
- Verify ChromaDB collection has data: check collection stats

---

## 📋 Log Event Catalog

| Event/Filter | Purpose | Expected Values |
|-------------|---------|-----------------|
| `RAG retrieve_context` | Entry point for RAG retrieval | certification_id, query, k |
| `Querying exam_guides collection` | ChromaDB query execution | where clause, n_results |
| `RAG chunk validation` | Post-retrieval certification check | passed, failed_mismatch, missing_metadata |
| `RAG retrieval complete` | Final RAG summary | total_chunks, exam_guides, transcripts, unique_docs |
| `generate_assessment_questions` | LLM service entry | certification_id, domain, question_count |
| `Certification profile loaded` | Profile resolution success | profile_id, profile_name, cert_slug |
| `Initiating RAG retrieval` | RAG call from LLM service | certification_id, query |
| `RAG context prepared` | RAG context ready for LLM | context_chars, citations_count |
| `generate_questions_request` | Complete LLM request | system_message, user_message, assessment_prompt_source |
| `generate_questions_response` | Complete LLM response | raw_response, tokens, finish_reason |

---

## ✅ Verification Checklist

Use this checklist to verify certification-specific assessment generation:

- [ ] **RAG Retrieval:**
  - [ ] `certification_id` matches expected profile
  - [ ] ChromaDB query uses correct `where={certification_id: ...}`
  - [ ] First chunk metadata shows correct certification
  - [ ] Chunk validation: `passed=total`, `failed_mismatch=0`
  - [ ] Final retrieval shows only expected documents

- [ ] **Certification Profile:**
  - [ ] Profile loaded successfully with correct `profile_name`
  - [ ] `has_assessment_prompt=True` (using profile-specific prompt)
  - [ ] `cert_slug` correctly derived

- [ ] **LLM Request:**
  - [ ] `assessment_prompt_source: "profile"` (not "default")
  - [ ] `user_message` contains RAG context from correct certification
  - [ ] `knowledge_base_context_preview` shows relevant content

- [ ] **LLM Response:**
  - [ ] `finish_reason: "stop"` (completed successfully)
  - [ ] Questions generated match domain and certification

---

## 🔧 Maintenance

### Log Rotation
The combined log file can grow large. Rotate periodically:
```bash
mv src/logs/presgen_assess_combined.log src/logs/presgen_assess_combined.log.old
```

### Performance Impact
These logs are comprehensive but will increase log file size. Monitor disk usage.

### Future Enhancements
- Add structured JSON logging for easier parsing
- Implement log aggregation (ELK stack, CloudWatch, etc.)
- Add certification_id to all log entries for easier filtering
