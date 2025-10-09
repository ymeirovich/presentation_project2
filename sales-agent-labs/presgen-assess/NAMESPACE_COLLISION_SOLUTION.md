# Namespace Collision Solution

**Problem**: Both `presgen-assess` and `sales-agent-labs` have a `src/` directory, causing namespace collision when importing `src.agent.slides_google` from sales-agent-labs.

## Root Cause

1. `presgen-assess/src/` contains presgen-assess modules
2. `sales-agent-labs/src/` contains shared modules including `src.agent.slides_google`
3. Python caches the first `src` module it finds in `sys.modules`
4. Once cached, changing `sys.path` doesn't help - Python uses the cached module

## The Problem Flow

```
1. Application starts from presgen-assess/
2. Python adds presgen-assess/src to sys.path
3. First import of 'src' module loads presgen-assess/src
4. Python caches it in sys.modules['src']
5. Later, when trying to import src.agent.slides_google:
   - Python finds 'src' in sys.modules (from presgen-assess)
   - Looks for 'agent' submodule in presgen-assess/src
   - Fails: No module named 'src.agent'
```

## Solution Implemented

Created `src/common/google_slides_import_v2.py` helper that:

1. **Clears the module cache**: Removes all `src.*` modules from `sys.modules`
2. **Reorders sys.path**: Temporarily puts sales-agent-labs at position 0
3. **Imports fresh**: `import src.agent.slides_google` now finds the correct module
4. **Restores sys.path**: Other presgen-assess imports continue to work
5. **Caches the result**: The correct module stays in `sys.modules`

## Key Code

```python
# Remove all src.* modules from sys.modules
to_remove = [k for k in list(sys.modules.keys())
             if k == 'src' or k.startswith('src.')]
for k in to_remove:
    del sys.modules[k]

# Prioritize sales-agent-labs
sys.path.insert(0, sales_agent_labs_str)

# Import (will cache in sys.modules)
import src.agent.slides_google as slides_google

# Restore sys.path (but keep the cached module)
sys.path[:] = saved_path
```

## Files Modified

1. **Created**: `src/common/google_slides_import_v2.py` - Helper for safe imports
2. **Updated**: `src/service/startup_checks.py` - Uses helper for validation
3. **Updated**: `src/service/api/v1/endpoints/workflows.py` - Uses helper
4. **Updated**: `src/service/presgen_core_client.py` - Uses helper
5. **Created**: `run_server.sh` - Pre-flight validation script

## Remaining Issue

The helper restores `sys.path`, which causes subsequent imports from presgen-assess to fail when the code path imports both:
- `src.agent.slides_google` (needs sales-agent-labs first)
- `src.services.course_generation_service` (needs presgen-assess first)

## Next Step

Need to modify the helper to keep BOTH directories in sys.path in the correct order, or use fully qualified imports for presgen-assess modules.
