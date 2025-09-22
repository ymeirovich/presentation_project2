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

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)


def main():
    """Run the PresGen-Assess FastAPI application."""
    logger.info("🚀 Starting PresGen-Assess application")

    try:
        uvicorn.run(
            "main:app",
            host="0.0.0.0",
            port=8080,
            reload=settings.debug,
            log_level=settings.log_level.lower(),
            access_log=True
        )
    except KeyboardInterrupt:
        logger.info("👋 PresGen-Assess application stopped")
    except Exception as e:
        logger.error(f"❌ Failed to start application: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()