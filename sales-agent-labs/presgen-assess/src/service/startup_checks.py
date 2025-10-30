"""Startup validation checks for PresGen-Assess service."""

import logging
import sys
from pathlib import Path
from typing import List, Tuple

logger = logging.getLogger(__name__)


def validate_google_slides_integration() -> Tuple[bool, str]:
    """
    Validate that Google Slides integration module is importable.

    Returns:
        Tuple of (success: bool, message: str)
    """
    logger.info("🔍 Validating Google Slides integration...")

    # Use helper to import from sales-agent-labs (handles namespace collision)
    try:
        logger.info("  Importing helper module...")
        from src.common.google_slides_import_v2 import get_slides_google

        logger.info("  Calling get_slides_google()...")
        slides_google = get_slides_google()

        logger.info(f"  ✅ Got module: {slides_google}")
        logger.info(f"  Module file: {getattr(slides_google, '__file__', 'no __file__')}")

        logger.info("✅ Google Slides integration module verified")
        return True, "Google Slides module imported successfully"

    except Exception as e:
        logger.error(f"❌ Error during import: {type(e).__name__}: {e}")
        import traceback
        logger.error(traceback.format_exc())
        error_msg = (
            f"❌ Google Slides integration module not found: {e}\n"
            f"Current sys.path:\n" + "\n".join(f"  - {p}" for p in sys.path[:10])
        )
        logger.error(error_msg)
        return False, str(e)


def validate_environment() -> List[Tuple[str, bool, str]]:
    """
    Run all startup validation checks.

    Returns:
        List of tuples: (check_name, success, message)
    """
    checks = []

    # Check 1: Google Slides integration
    success, msg = validate_google_slides_integration()
    checks.append(("Google Slides Integration", success, msg))

    # Check 2: PYTHONPATH includes sales-agent-labs
    sales_agent_labs_in_path = any("sales-agent-labs" in p for p in sys.path)
    checks.append((
        "PYTHONPATH Configuration",
        sales_agent_labs_in_path,
        "sales-agent-labs found in sys.path" if sales_agent_labs_in_path
        else "sales-agent-labs NOT in sys.path - imports may fail"
    ))

    # Check 3: OAuth credentials exist
    repo_root = Path(__file__).parent.parent.parent.parent
    oauth_client_path = repo_root / "oauth_slides_client.json"
    token_path = repo_root / "token.json"

    oauth_exists = oauth_client_path.exists()
    token_exists = token_path.exists()
    oauth_msg = f"OAuth client: {'✓' if oauth_exists else '✗'} | Token: {'✓' if token_exists else '✗'}"

    checks.append((
        "OAuth Credentials",
        oauth_exists and token_exists,
        oauth_msg
    ))

    return checks


def log_startup_diagnostics():
    """Log startup diagnostics and validation results."""
    logger.info("=" * 80)
    logger.info("🔍 PresGen-Assess Startup Diagnostics")
    logger.info("=" * 80)

    checks = validate_environment()
    all_passed = True

    for check_name, success, message in checks:
        status = "✅ PASS" if success else "❌ FAIL"
        logger.info(f"{status} | {check_name}")
        logger.info(f"         {message}")
        if not success:
            all_passed = False

    logger.info("=" * 80)

    if not all_passed:
        logger.warning(
            "⚠️  Some startup checks failed. "
            "The service may not function correctly. "
            "Review the errors above and ensure PYTHONPATH is configured properly."
        )
    else:
        logger.info("✅ All startup checks passed - service ready")

    logger.info("=" * 80)

    return all_passed
