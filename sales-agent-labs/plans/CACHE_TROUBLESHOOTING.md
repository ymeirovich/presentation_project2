# PresGen Cache Troubleshooting Guide

## Quick Fix for Cache Issues

When slides aren't generating or charts aren't appearing in slides, the issue is usually cache-related. Follow these steps:

### 1. Use the Cache Clearing Script

```bash
# Clear all caches (recommended for most issues)
python3 clear_cache.py

# Check current cache status
python3 clear_cache.py --status

# Clear only problematic data slide entries
python3 clear_cache.py --data-slides
```

### 2. Verify Environment Settings

Ensure your `.env` file has:
```bash
PRESGEN_DEV_MODE=true
PRESGEN_USE_CACHE=false
```

### 3. Restart Services

After clearing cache, restart both servers:
```bash
# Terminal 1 - Backend
uvicorn src.service.http:app --reload --port 8080

# Terminal 2 - Frontend
cd presgen-ui && npm run dev
```

## Common Cache Issues

### Issue: Charts Generate but Slides Don't Update

**Symptoms:**
- Charts appear in `out/images/charts/`
- Logs show `"use_cache": true` and `"cache_hit"`
- Slides contain old content without new charts

**Solution:**
```bash
python3 clear_cache.py --data-slides
# Restart backend server
```

### Issue: Cache Settings Ignored

**Symptoms:**
- Environment shows `PRESGEN_DEV_MODE=true`
- Logs still show `"use_cache": true`

**Root Causes:**
1. Server hasn't reloaded environment variables
2. Frontend components have hardcoded cache settings
3. Idempotency cache overriding cache settings

**Solution:**
```bash
# Check current status
python3 clear_cache.py --status

# Clear all caches
python3 clear_cache.py

# Restart servers completely (not just reload)
```

### Issue: PDF Processing Fails

**Symptoms:**
- Error: "Failed to read PDF file: Error: Setting up fake worker failed"
- CDN worker loading issues

**Current Status:**
- PDF processing is intentionally disabled in server-side processing
- Client-side PDF.js may be attempting to process files
- DOCX processing works via server-side conversion

**Workaround:**
- Convert PDF to text manually
- Use copy-paste for PDF content
- Use DOCX files instead of PDF when possible

## Manual Cache Clearing (Without Script)

If the script isn't available:

```bash
# Backup first
cp out/state/idempotency.json out/state/idempotency.json.backup

# Clear specific data query entries
python3 -c "
import json
with open('out/state/idempotency.json', 'r') as f:
    cache = json.load(f)

# Remove data query entries
entries_to_remove = [k for k in cache.keys() if '#dq' in k]
for entry in entries_to_remove:
    del cache[entry]
    print(f'Removed: {entry}')

with open('out/state/idempotency.json', 'w') as f:
    json.dump(cache, f)

print(f'Remaining entries: {len(cache)}')
"
```

## Cache Debugging Commands

```bash
# Check environment variables
python3 -c "
import os
from dotenv import load_dotenv
load_dotenv()
print('PRESGEN_DEV_MODE:', os.getenv('PRESGEN_DEV_MODE'))
print('PRESGEN_USE_CACHE:', os.getenv('PRESGEN_USE_CACHE'))
"

# Count cache entries
python3 -c "
import json
with open('out/state/idempotency.json', 'r') as f:
    cache = json.load(f)
print(f'Total cache entries: {len(cache)}')
data_entries = [k for k in cache.keys() if '#dq' in k]
print(f'Data query entries: {len(data_entries)}')
for entry in data_entries:
    print(f'  - {entry}')
"

# Monitor cache usage in logs
tail -f src/logs/mcp-server-*.log | grep "use_cache\|cache_hit"
```

## Prevention

1. **Always use the cache clearing script** before debugging cache issues
2. **Verify environment settings** after any configuration changes
3. **Restart servers completely** after environment changes
4. **Monitor logs** for `"use_cache": false` to confirm cache is disabled

## Files Managed by Cache System

- `out/state/idempotency.json` - Prevents duplicate slide creation
- `out/state/cache/llm_summarize/` - LLM response cache
- `out/state/cache/imagen/` - Image generation cache
- Frontend components with hardcoded `use_cache: true`

The cache clearing script handles all of these automatically with proper backups.