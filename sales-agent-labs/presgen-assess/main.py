#!/usr/bin/env python3
"""Main entry point for PresGen-Assess application."""

import logging
import sys
from pathlib import Path

import uvicorn

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.service.app import app
from src.common.config import settings
from src.common.logging_config import (
    initialize_service_loggers,
    log_application_startup,
    log_application_shutdown,
    get_service_logger
)

# Initialize enhanced file-based logging
initialize_service_loggers()

# Get application logger
logger = get_service_logger("main")


def main():
    """Run the PresGen-Assess FastAPI application."""
    # Log detailed startup information
    log_application_startup()

    try:
        logger.info("🌐 Starting Uvicorn server on http://0.0.0.0:8080")
        logger.info(f"🔧 Debug mode: {settings.debug}")
        logger.info(f"📊 Log level: {settings.log_level}")

        uvicorn.run(
            "main:app",
            host="0.0.0.0",
            port=8080,
            reload=settings.debug,
            log_level=settings.log_level.lower(),
            access_log=True
        )
    except KeyboardInterrupt:
        log_application_shutdown()
        logger.info("👋 PresGen-Assess application stopped gracefully")
    except Exception as e:
        logger.error(f"❌ Failed to start application: {e}", exc_info=True)
        log_application_shutdown()
        sys.exit(1)


if __name__ == "__main__":
    main()