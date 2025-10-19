# ⚠️ APPLICATION RESTART REQUIRED

## Changes Made
The following files have been modified with enhanced logging:

1. **src/knowledge/embeddings.py** - Fixed cert_id/certification_id mismatch + comprehensive RAG logging
2. **src/services/llm_service.py** - Added certification profile & LLM request/response logging

## Why Restart is Needed
Even though uvicorn is running with `--reload`, it may not have detected these changes yet. The Python module cache may also be stale.

## How to Restart

### Option 1: Kill and Restart Uvicorn
```bash
# Find the process
ps aux | grep uvicorn | grep presgen-assess

# Kill it (replace PID with actual process ID)
kill <PID>

# Or kill all uvicorn processes
pkill -f "uvicorn.*presgen"

# Restart
cd /Users/yitzchak/Documents/learn/presentation_project/sales-agent-labs/presgen-assess
python main.py
# OR
uvicorn src.service.http:app --reload --port 8000
```

### Option 2: Restart from IDE/Terminal
If running in a terminal or IDE, press `Ctrl+C` and restart with:
```bash
python main.py
```

## Verification After Restart

### 1. Generate a New Assessment
Create a new workflow to trigger assessment generation.

### 2. Check Logs for New Format
```bash
# Should now see new logging format
tail -f src/logs/assessments.log | grep "🎯 generate_assessment_questions"

# Should see RAG filtering logs
tail -f src/logs/assessments.log | grep "🔍 RAG retrieve_context"

# Check for certification mismatches (should be NONE)
grep "🚨 CRITICAL: RAG certification mismatch" src/logs/assessments.log
```

### 3. Expected New Log Entries

**Assessment Generation Entry:**
```
🎯 generate_assessment_questions | certification_id=36b36141-0f79-449f-a6bf-b2ec59fddcd1 | domain=Security | question_count=5
```

**Certification Profile Loaded:**
```
✅ Certification profile loaded | profile_id=36b36141-0f79-449f-a6bf-b2ec59fddcd1 | profile_name=ICF Core Competency Coach Certification | cert_slug=icf-core-competency | has_assessment_prompt=True
```

**RAG Retrieval:**
```
🔍 RAG retrieve_context | certification_id=icf-core-competency | query=Security certification exam questions... | k=8
```

**RAG Validation:**
```
✅ RAG chunk validation | collection=exam_guides | total=4 | passed=4 | failed_mismatch=0 | missing_metadata=0
```

**LLM Request (JSON):**
```json
{
  "event": "generate_questions_request",
  "assessment_prompt_source": "profile",
  "system_message": "You are an expert certification exam question writer...",
  "user_message": "[FULL PROMPT]"
}
```

## If Logs Still Don't Appear

### 1. Check Python Cache Was Cleared
```bash
cd /Users/yitzchak/Documents/learn/presentation_project/sales-agent-labs/presgen-assess
find . -path "*/src/*" -name "__pycache__" -type d -exec rm -rf {} +
find . -name "*.pyc" -delete
```

### 2. Verify File Modifications
```bash
# Check when files were last modified
stat -f "%Sm" src/services/llm_service.py
stat -f "%Sm" src/knowledge/embeddings.py

# Should show recent modification times
```

### 3. Check Import Errors
```bash
cd /Users/yitzchak/Documents/learn/presentation_project/sales-agent-labs/presgen-assess
source venv/bin/activate  # or activate your virtual environment
python -c "from src.services.llm_service import LLMService; from src.knowledge.embeddings import VectorDatabaseManager; print('Imports successful')"
```

If you see `ModuleNotFoundError`, install dependencies:
```bash
pip install -r requirements.txt
```

## Current Status
- ✅ Code changes committed to files
- ✅ Python cache cleared
- ❌ Application NOT restarted yet
- ❌ New logs NOT appearing yet

## Next Step
**RESTART THE APPLICATION NOW** using one of the methods above, then verify the new logs appear.

---

**Modified Files:**
- src/knowledge/embeddings.py (line 16-19: logger import, lines 141-317: comprehensive logging)
- src/services/llm_service.py (lines 57-156: certification & RAG logging, lines 219-270: LLM logging)
