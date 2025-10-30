"""
Simple, robust helper to import Google Slides from sales-agent-labs.

Strategy: Import once, cache the module object, and provide direct access to it.
This avoids namespace pollution while ensuring both src namespaces can coexist.
"""

import sys
from pathlib import Path

# Module cache - stores the actual module object
_cached_slides_google = None


def get_slides_google():
    """
    Import and return the slides_google module from sales-agent-labs.

    This function handles the namespace collision by:
    1. Importing src.agent.slides_google with sales-agent-labs prioritized
    2. Caching the module OBJECT (not just in sys.modules)
    3. Restoring sys.path so presgen-assess imports continue to work
    4. Returning the cached module object
    """
    global _cached_slides_google
    import logging
    logger = logging.getLogger(__name__)

    # Return cached module if available
    if _cached_slides_google is not None:
        logger.debug("✅ Returning cached slides_google module")
        return _cached_slides_google

    logger.info("🔄 First-time import of slides_google from sales-agent-labs")

    # Get paths
    this_file = Path(__file__)
    presgen_assess_src = this_file.parent.parent  # .../presgen-assess/src or /app/src
    presgen_assess_dir = presgen_assess_src.parent  # .../presgen-assess or /app

    # In Docker: /app/src -> /app/sales-agent-labs
    # In local: .../sales-agent-labs/presgen-assess/src -> .../sales-agent-labs

    # Try Docker path first
    if presgen_assess_dir.name == "app":
        # Docker context: /app/
        sales_agent_labs_dir = presgen_assess_dir / "sales-agent-labs"
    else:
        # Local context: .../sales-agent-labs/presgen-assess
        sales_agent_labs_dir = presgen_assess_dir.parent

    sales_agent_labs_str = str(sales_agent_labs_dir)
    presgen_assess_src_str = str(presgen_assess_src)

    # Verify target exists
    target = sales_agent_labs_dir / "src" / "agent" / "slides_google.py"
    if not target.exists():
        raise ImportError(f"slides_google.py not found at {target}")

    # Save sys state to restore after import
    saved_path = sys.path.copy()
    saved_src_modules = {k: v for k, v in sys.modules.items() if k == 'src' or k.startswith('src.')}

    logger.info(f"📦 Saved {len(saved_src_modules)} presgen-assess src.* modules")
    logger.debug(f"  Modules: {list(saved_src_modules.keys())[:10]}")

    try:
        # Remove all src.* modules to force fresh import
        to_remove = [k for k in list(sys.modules.keys()) if k == 'src' or k.startswith('src.')]
        logger.info(f"🗑️ Removing {len(to_remove)} src.* modules from sys.modules")
        for k in to_remove:
            del sys.modules[k]

        # Temporarily prioritize sales-agent-labs
        if sales_agent_labs_str in sys.path:
            sys.path.remove(sales_agent_labs_str)
        sys.path.insert(0, sales_agent_labs_str)
        logger.info(f"✅ Prioritized sales-agent-labs in sys.path: {sales_agent_labs_str}")

        # Import and cache the MODULE OBJECT
        logger.info("📦 Importing src.agent.slides_google...")
        import src.agent.slides_google as slides_google
        _cached_slides_google = slides_google
        logger.info(f"✅ Successfully imported: {slides_google.__file__}")

        # CRITICAL: Keep sales-agent-labs src.agent.* modules but restore presgen-assess src root
        # We need to selectively restore to allow both namespaces to coexist

        # First, restore ALL presgen-assess modules EXCEPT src.agent.*
        restored_count = 0
        skipped_count = 0
        for key, module in saved_src_modules.items():
            if key.startswith('src.agent'):
                # Keep the sales-agent-labs version
                skipped_count += 1
                logger.debug(f"  Skipping {key} (keeping sales-agent-labs version)")
            else:
                # Restore presgen-assess version (overwrite if needed)
                sys.modules[key] = module
                restored_count += 1
                logger.debug(f"  Restored {key}")

        logger.info(f"🔄 Restored {restored_count} presgen-assess modules, skipped {skipped_count} src.agent modules")

        # Now restore sys.path with presgen-assess/src prioritized
        # This ensures future imports from presgen-assess code find presgen-assess modules
        sys.path[:] = saved_path

        # Ensure presgen-assess/src is at the front for presgen-assess imports
        # but keep sales-agent-labs accessible for already-imported src.agent modules
        if presgen_assess_src_str in sys.path:
            sys.path.remove(presgen_assess_src_str)
        sys.path.insert(0, presgen_assess_src_str)

        logger.info("🔄 Restored sys.path with presgen-assess/src prioritized")
        logger.debug(f"  sys.path[0]: {sys.path[0]}")
        logger.debug(f"  sys.path[1]: {sys.path[1] if len(sys.path) > 1 else 'N/A'}")

        # Verify 'src' module is restored and functional
        if 'src' in sys.modules:
            src_module = sys.modules['src']
            src_file = getattr(src_module, '__file__', 'no __file__')
            src_path = getattr(src_module, '__path__', [])

            logger.info(f"✅ 'src' module verified: {src_file}")
            logger.info(f"  Module __path__: {list(src_path)[:3]}")

            # Verify it's pointing to presgen-assess
            if 'presgen-assess' in str(src_file) or 'presgen-assess' in str(src_path):
                logger.info("  ✅ Points to presgen-assess (correct)")
            else:
                logger.warning(f"  ⚠️  Points to {src_file} (may cause issues)")
        else:
            logger.error("❌ 'src' module NOT in sys.modules after restoration!")

        # Return the cached module object
        return _cached_slides_google

    except Exception as e:
        logger.error(f"❌ Import failed: {type(e).__name__}: {e}")
        logger.error(f"  Restoring sys state...")
        # Restore everything on failure
        sys.path[:] = saved_path
        sys.modules.update(saved_src_modules)
        raise ImportError(f"Failed to import slides_google: {e}") from e
