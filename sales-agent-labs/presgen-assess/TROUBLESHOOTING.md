# PresGen-Assess Troubleshooting Guide

**Last Updated**: 2025-10-09

---

## Common Errors and Solutions

### Error: `No module named 'src.agent'`

**Full Error:**
```
PRESENTATION_DECK_FAILED | error=No module named 'src.agent'
```

**Root Cause:**
The application cannot import `src.agent.slides_google` from the parent `sales-agent-labs/` directory because PYTHONPATH is not configured correctly.

**Solution:**

**Option 1: Use the run script (Recommended)**
```bash
cd presgen-assess
source ../.venv/bin/activate  # Must activate virtualenv first
./run_server.sh
```

The script will:
- ✅ Automatically set PYTHONPATH
- ✅ Validate Google Slides module is importable before starting
- ✅ Show clear error messages if validation fails

**Option 2: Manual start with PYTHONPATH**
```bash
cd /Users/yitzchak/Documents/learn/presentation_project/sales-agent-labs
source .venv/bin/activate
export PYTHONPATH=/Users/yitzchak/Documents/learn/presentation_project/sales-agent-labs:$PYTHONPATH
cd presgen-assess
uvicorn src.service.app:app --reload --port 8000
```

**Verification:**

Test the import manually before starting:
```bash
cd /Users/yitzchak/Documents/learn/presentation_project/sales-agent-labs
source .venv/bin/activate
export PYTHONPATH=/Users/yitzchak/Documents/learn/presentation_project/sales-agent-labs:$PYTHONPATH
python3 -c "import src.agent.slides_google; print('✅ Import successful')"
```

**Why This Happens:**

The application structure has:
- PresGen-Assess service at: `sales-agent-labs/presgen-assess/`
- Google Slides integration at: `sales-agent-labs/src/agent/slides_google.py`

When starting uvicorn from `presgen-assess/`, Python needs the parent directory in its path to find `src.agent.slides_google`.

---

### Error: `⚠️ PresGen-Core mock path used`

**Root Cause:**
Either:
1. `PRESGEN_USE_MOCK=true` is set (intentional mock mode)
2. Google Slides module import failed (fallback to mock)

**Solution:**

**Check 1: Verify mock mode setting**
```bash
echo $PRESGEN_USE_MOCK
```

If it shows `true`, and you want real mode:
```bash
export PRESGEN_USE_MOCK=false
```

**Check 2: Verify Google Slides module**
```bash
python3 -c "import src.agent.slides_google"
```

If this fails, follow the **"No module named 'src.agent'"** solution above.

**Check 3: Review startup diagnostics**

When the server starts, look for:
```
✅ PASS | Google Slides Integration
         Google Slides module imported successfully

✅ PASS | PYTHONPATH Configuration
         sales-agent-labs found in sys.path
```

If you see `❌ FAIL`, the startup checks will show exactly what's missing.

---

### Error: `OAuth token expired` or `Invalid credentials`

**Symptoms:**
- Google Slides API calls fail with 401 Unauthorized
- Errors mentioning expired tokens or invalid credentials

**Solution:**

**Refresh OAuth token:**
```bash
cd /Users/yitzchak/Documents/learn/presentation_project/sales-agent-labs
source .venv/bin/activate
export PYTHONPATH=/Users/yitzchak/Documents/learn/presentation_project/sales-agent-labs:$PYTHONPATH
python3 src/agent/slides_google.py --auth
```

This will:
1. Open a browser for Google OAuth consent
2. Generate a fresh `token.json`
3. Save it in the repository root

**Verify credentials exist:**
```bash
ls -la oauth_slides_client.json token.json
```

Both files should exist in the `sales-agent-labs/` directory.

---

### Error: Virtual environment not found

**Symptoms:**
```
⚠️ Warning: Virtual environment not activated
```

**Solution:**

**Create virtualenv (if missing):**
```bash
cd /Users/yitzchak/Documents/learn/presentation_project/sales-agent-labs
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

**Activate existing virtualenv:**
```bash
cd /Users/yitzchak/Documents/learn/presentation_project/sales-agent-labs
source .venv/bin/activate
```

**Verify activation:**
```bash
which python3
# Should show: /Users/yitzchak/Documents/learn/presentation_project/sales-agent-labs/.venv/bin/python3
```

---

### Error: PresGen-Core connection refused

**Symptoms:**
```
PresGen-Core request failed: Connection refused
stage=core_failure
```

**Root Cause:**
PresGen-Core service (presgen-training2) is not running on port 8080.

**Solution:**

**Start PresGen-Core:**
```bash
# Terminal 2 (separate from PresGen-Assess)
cd /Users/yitzchak/Documents/learn/presentation_project/sales-agent-labs
source .venv/bin/activate
export PYTHONPATH=/Users/yitzchak/Documents/learn/presentation_project/sales-agent-labs:$PYTHONPATH
cd presgen-training2
# Check the actual startup command for presgen-training2
uvicorn src.api.main:app --reload --port 8080
```

**Verify PresGen-Core is running:**
```bash
curl http://localhost:8080/health
# Should return 200 OK
```

**Check PRESGEN_CORE_URL configuration:**
```bash
echo $PRESGEN_CORE_URL
# Should show: http://localhost:8080 (or your configured URL)
```

---

## Startup Diagnostics

When the server starts successfully, you should see:

```
🚀 Starting PresGen-Assess server...
📁 Working directory: /Users/.../presgen-assess
🔧 PYTHONPATH: /Users/.../sales-agent-labs:...

🔍 Validating Google Slides integration...
✅ Google Slides module verified

================================================================================
🔍 PresGen-Assess Startup Diagnostics
================================================================================
✅ PASS | Google Slides Integration
         Google Slides module imported successfully
✅ PASS | PYTHONPATH Configuration
         sales-agent-labs found in sys.path
✅ PASS | OAuth Credentials
         OAuth client: ✓ | Token: ✓
================================================================================
✅ All startup checks passed - service ready
================================================================================
```

**If startup checks fail**, the diagnostics will show which component is missing and suggest fixes.

---

## Testing Checklist

Before reporting an issue, verify:

- [ ] Virtual environment activated: `echo $VIRTUAL_ENV`
- [ ] PYTHONPATH set correctly: `echo $PYTHONPATH | grep sales-agent-labs`
- [ ] Google Slides module importable: `python3 -c "import src.agent.slides_google"`
- [ ] OAuth credentials present: `ls oauth_slides_client.json token.json`
- [ ] PresGen-Core running (if not in mock mode): `curl http://localhost:8080/health`
- [ ] Database initialized: `ls presgen-assess/test_database.db`
- [ ] Server starts without errors using `./run_server.sh`
- [ ] Startup diagnostics show all checks passed

---

## Getting Help

If issues persist:

1. **Collect logs:**
   ```bash
   tail -100 presgen-assess/logs/course_generation.log
   tail -100 presgen-assess/logs/presgen_assess_combined.log
   ```

2. **Check startup diagnostics** from server output

3. **Verify environment:**
   ```bash
   cd presgen-assess
   ./run_server.sh 2>&1 | head -50 > startup_log.txt
   ```

4. **Include in your report:**
   - Startup log output
   - Error message from logs
   - PYTHONPATH value
   - Virtual environment path
   - Operating system and Python version

---

## Quick Reference

### Recommended Startup Sequence

```bash
# Terminal 1: PresGen-Assess
cd /Users/yitzchak/Documents/learn/presentation_project/sales-agent-labs/presgen-assess
source ../.venv/bin/activate
export PRESGEN_USE_MOCK=false  # For real mode
./run_server.sh

# Terminal 2: PresGen-Core (if not using mock)
cd /Users/yitzchak/Documents/learn/presentation_project/sales-agent-labs/presgen-training2
source ../.venv/bin/activate
export PYTHONPATH=/Users/yitzchak/Documents/learn/presentation_project/sales-agent-labs:$PYTHONPATH
# Use actual startup command for presgen-training2

# Terminal 3: Frontend (optional)
cd /Users/yitzchak/Documents/learn/presentation_project/sales-agent-labs/presgen-ui
npm run dev
```

### Environment Variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `PRESGEN_USE_MOCK` | `false` | Enable mock mode (bypass PresGen-Core) |
| `PRESGEN_CORE_URL` | `http://localhost:8080` | PresGen-Core service URL |
| `PYTHONPATH` | (required) | Must include `sales-agent-labs/` directory |
| `PRESGEN_CORE_VOICE_PROFILE` | `OpenAI Demo Voice (Your Audio)` | TTS voice profile |
| `PRESGEN_CORE_QUALITY_LEVEL` | `fast` | Video quality (`fast` or `high`) |
