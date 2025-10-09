"""
Helper module to import Google Slides integration from sales-agent-labs.

This module handles the namespace collision between presgen-assess/src and sales-agent-labs/src
by using direct file import (importlib.util.spec_from_file_location).
"""

import sys
import importlib.util
from pathlib import Path


def import_google_slides_module():
    """
    Import slides_google from sales-agent-labs by manipulating sys.path.

    This ensures the module can be imported along with its relative imports.

    Returns the slides_google module.
    """
    import logging
    logger = logging.getLogger(__name__)

    # Get path to sales-agent-labs
    presgen_assess_src = Path(__file__).parent.parent
    presgen_assess_dir = presgen_assess_src.parent
    sales_agent_labs_dir = presgen_assess_dir.parent

    logger.info("🔍 Google Slides Import Helper - Starting")
    logger.info(f"  presgen_assess_dir: {presgen_assess_dir}")
    logger.info(f"  sales_agent_labs_dir: {sales_agent_labs_dir}")

    # Verify the module exists
    slides_google_path = sales_agent_labs_dir / "src" / "agent" / "slides_google.py"
    logger.info(f"  Target file: {slides_google_path}")
    logger.info(f"  File exists: {slides_google_path.exists()}")

    if not slides_google_path.exists():
        raise ImportError(
            f"Google Slides module not found at {slides_google_path}. "
            f"Ensure sales-agent-labs/src/agent/slides_google.py exists."
        )

    # Log sys.path BEFORE modifications
    logger.info("📊 sys.path BEFORE modifications:")
    for i, p in enumerate(sys.path[:15]):
        if 'sales-agent-labs' in p or 'presgen-assess' in p:
            logger.info(f"  [{i}] {p}")

    # Clean up sys.path - remove any "/sales-agent-labs/src" entries (wrong)
    # and ensure "/sales-agent-labs" (correct) is at the front
    sales_agent_labs_str = str(sales_agent_labs_dir)
    sales_agent_labs_src_str = str(sales_agent_labs_dir / "src")

    logger.info(f"🧹 Cleaning sys.path:")
    logger.info(f"  Removing wrong path: {sales_agent_labs_src_str}")

    # Remove the wrong path if present
    removed_count = 0
    while sales_agent_labs_src_str in sys.path:
        sys.path.remove(sales_agent_labs_src_str)
        removed_count += 1
    logger.info(f"  Removed {removed_count} instances of wrong path")

    logger.info(f"  Removing correct path (will re-add at front): {sales_agent_labs_str}")
    # Remove the correct path if present (we'll add it at position 0)
    removed_count = 0
    while sales_agent_labs_str in sys.path:
        sys.path.remove(sales_agent_labs_str)
        removed_count += 1
    logger.info(f"  Removed {removed_count} instances")

    # Add it at the front
    sys.path.insert(0, sales_agent_labs_str)
    logger.info(f"✅ Added {sales_agent_labs_str} at position 0")

    # Log sys.path AFTER modifications
    logger.info("📊 sys.path AFTER modifications:")
    for i, p in enumerate(sys.path[:15]):
        if 'sales-agent-labs' in p or 'presgen-assess' in p or i == 0:
            marker = " ← TARGET" if i == 0 else ""
            logger.info(f"  [{i}] {p}{marker}")

    try:
        # CRITICAL: Remove the 'src' module itself if it's from presgen-assess
        if 'src' in sys.modules:
            src_module = sys.modules['src']
            src_file = getattr(src_module, '__file__', None)
            logger.info(f"🔍 Found existing 'src' module in sys.modules:")
            logger.info(f"  File: {src_file}")

            # Check if it's from presgen-assess (wrong) or sales-agent-labs (correct)
            if src_file and 'presgen-assess' in src_file:
                logger.info(f"  ⚠️ This is from presgen-assess - REMOVING IT")
                del sys.modules['src']
            elif src_file and 'sales-agent-labs' in src_file:
                logger.info(f"  ✅ This is from sales-agent-labs - keeping it")
            else:
                logger.info(f"  ⚠️ Unknown source - removing to be safe")
                del sys.modules['src']

        # Clear any existing src.* submodules to avoid conflicts
        modules_to_remove = [k for k in sys.modules.keys() if k.startswith('src.')]
        if modules_to_remove:
            logger.info(f"🗑️ Removing conflicting submodules: {modules_to_remove}")
            for mod in modules_to_remove:
                del sys.modules[mod]

        # Check what 'src' module Python will find NOW
        logger.info("🔎 Testing import resolution AFTER cleanup...")
        try:
            import src
            logger.info(f"  'src' module resolves to: {src.__file__ if hasattr(src, '__file__') else 'no __file__'}")
            logger.info(f"  'src' module path: {src.__path__ if hasattr(src, '__path__') else 'no __path__'}")

            # Check if src.agent exists
            if hasattr(src, '__path__'):
                agent_path = Path(src.__path__[0]) / 'agent'
                logger.info(f"  Expected src.agent path: {agent_path}")
                logger.info(f"  src.agent directory exists: {agent_path.exists()}")

        except ImportError as ie:
            logger.error(f"  Cannot import 'src': {ie}")

        # Now import normally - the relative imports will work
        logger.info("📦 Attempting: import src.agent.slides_google")
        import src.agent.slides_google as slides_google
        logger.info(f"✅ Successfully imported! Module: {slides_google}")
        logger.info(f"  Module file: {slides_google.__file__ if hasattr(slides_google, '__file__') else 'no __file__'}")

        # Keep the module in sys.modules for caching and future imports
        return slides_google

    except Exception as e:
        logger.error(f"❌ Import failed: {type(e).__name__}: {e}")
        logger.error(f"  Exception details:", exc_info=True)
        raise ImportError(f"Failed to import Google Slides module: {e}") from e


# Cache the module
_slides_google_module = None


def get_slides_google():
    """Get the cached Google Slides module."""
    global _slides_google_module
    if _slides_google_module is None:
        _slides_google_module = import_google_slides_module()
    return _slides_google_module
