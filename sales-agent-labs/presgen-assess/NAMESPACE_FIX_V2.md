# Namespace Collision Fix - Version 2

## Problem Summary

Two Python projects with overlapping `src/` directory structures:
- `presgen-assess/src/` - Contains: services, integrations, common, assessment
- `sales-agent-labs/src/` - Contains: agent, mcp, service, common

When both are in sys.path, Python's module cache can only hold ONE `src` module at a time.

## The Error Chain

1. **Startup**: Import `src.agent.slides_google` from sales-agent-labs ✅
2. **Runtime**: Try to import `from src.services.course_generation_service` ❌
   - Error: `No module named 'src.services'`
   - Reason: `src` module in sys.modules points to sales-agent-labs

## Solution Architecture

The `google_slides_import_v2.py` helper uses a **module cache + selective restoration** strategy:

### Step 1: Save State
```python
saved_path = sys.path.copy()
saved_src_modules = {k: v for k, v in sys.modules.items()
                     if k == 'src' or k.startswith('src.')}
```

### Step 2: Import from sales-agent-labs
```python
# Clear all src.* modules
for k in list(sys.modules.keys()):
    if k == 'src' or k.startswith('src.'):
        del sys.modules[k]

# Prioritize sales-agent-labs
sys.path.insert(0, sales_agent_labs_dir)

# Import and CACHE the module object
import src.agent.slides_google as slides_google
_cached_slides_google = slides_google  # Store module object, not just name
```

### Step 3: Restore presgen-assess State
```python
# Restore ALL presgen-assess modules EXCEPT src.agent.*
for key, module in saved_src_modules.items():
    if not key.startswith('src.agent'):
        sys.modules[key] = module  # Overwrite if needed

# Restore sys.path
sys.path[:] = saved_path

# Ensure presgen-assess/src is at position 0
sys.path.insert(0, presgen_assess_src_dir)
```

### Step 4: Return Cached Object
```python
return _cached_slides_google  # Return the MODULE OBJECT, not a name
```

## Why This Works

1. **Module Object Caching**: The slides_google module is cached as a Python object, not just a name in sys.modules
2. **Selective Restoration**: We keep `src.agent.*` from sales-agent-labs but restore all other `src.*` from presgen-assess
3. **Path Prioritization**: presgen-assess/src goes to position 0 in sys.path, so future imports find presgen-assess modules
4. **Coexistence**: Both namespaces work:
   - `src.agent.slides_google` → sales-agent-labs (via cached object)
   - `src.services.*` → presgen-assess (via sys.modules + sys.path)
   - `src.integrations.*` → presgen-assess (via sys.modules + sys.path)

## Usage

```python
# In any presgen-assess file that needs Google Slides
from common.google_slides_import_v2 import get_slides_google

slides_google = get_slides_google()
create_presentation = slides_google.create_presentation
# ... use functions from the module
```

## Files Updated

1. `src/common/google_slides_import_v2.py` - The helper (improved restoration logic)
2. `src/service/startup_checks.py` - Uses v2 helper
3. `src/service/api/v1/endpoints/workflows.py` - Uses v2 helper
4. `src/service/presgen_core_client.py` - Uses v2 helper

## Testing

1. Start server: `./run_server.sh`
2. Check startup logs: Should see "✅ Google Slides integration module verified"
3. Click "Generate Course" button
4. Check runtime logs: Should see successful imports of both:
   - `src.agent.slides_google` (from sales-agent-labs)
   - `src.services.*` and `src.integrations.*` (from presgen-assess)

## Key Improvements in V2

- **Unconditional restoration**: Overwrites sys.modules entries instead of checking `if not in`
- **Path prioritization**: Explicitly puts presgen-assess/src at sys.path[0]
- **Enhanced verification**: Checks if restored `src` module points to correct directory
- **Better logging**: Traces save/restore process for debugging
