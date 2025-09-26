"""Enhanced logging configuration for PresGen-Assess with file-based persistent storage."""

import logging
import logging.handlers
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

from src.common.config import settings


class ColoredFormatter(logging.Formatter):
    """Custom formatter with color coding for different log levels."""

    # Color codes
    COLORS = {
        'DEBUG': '\033[36m',     # Cyan
        'INFO': '\033[32m',      # Green
        'WARNING': '\033[33m',   # Yellow
        'ERROR': '\033[31m',     # Red
        'CRITICAL': '\033[35m',  # Magenta
    }
    RESET = '\033[0m'

    def format(self, record):
        # Add color to levelname for console output
        if hasattr(record, 'levelname'):
            color = self.COLORS.get(record.levelname, '')
            if color and sys.stdout.isatty():  # Only color if output is to terminal
                record.levelname = f"{color}{record.levelname}{self.RESET}"

        return super().format(record)


def setup_file_logging(service_name: str, log_level: str = None) -> logging.Logger:
    """
    Setup file-based logging for a specific service with rotation and retention.

    Args:
        service_name: Name of the service (e.g., 'certifications', 'assessments', etc.)
        log_level: Log level override

    Returns:
        Logger instance configured for the service
    """
    log_level = log_level or settings.log_level.upper()

    # Create logs directory if it doesn't exist
    log_dir = Path("src/logs")
    log_dir.mkdir(parents=True, exist_ok=True)

    # Create service-specific logger
    logger = logging.getLogger(f"presgen_assess.{service_name}")

    # Clear existing handlers to avoid duplicates
    logger.handlers.clear()

    # Set log level
    logger.setLevel(getattr(logging, log_level))

    # File formatter with detailed information
    file_formatter = logging.Formatter(
        fmt='%(asctime)s | %(name)s | %(levelname)-8s | %(funcName)s:%(lineno)d | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # Console formatter with colors
    console_formatter = ColoredFormatter(
        fmt='%(asctime)s | %(name)-20s | %(levelname)-8s | %(message)s',
        datefmt='%H:%M:%S'
    )

    # Rotating file handler for service-specific logs
    service_log_file = log_dir / f"{service_name}.log"
    file_handler = logging.handlers.RotatingFileHandler(
        service_log_file,
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setLevel(getattr(logging, log_level))
    file_handler.setFormatter(file_formatter)

    # Combined application log (all services)
    combined_log_file = log_dir / "presgen_assess_combined.log"
    combined_handler = logging.handlers.RotatingFileHandler(
        combined_log_file,
        maxBytes=50 * 1024 * 1024,  # 50MB
        backupCount=10,
        encoding='utf-8'
    )
    combined_handler.setLevel(getattr(logging, log_level))
    combined_handler.setFormatter(file_formatter)

    # Error-only log file
    error_log_file = log_dir / "presgen_assess_errors.log"
    error_handler = logging.handlers.RotatingFileHandler(
        error_log_file,
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(file_formatter)

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, log_level))
    console_handler.setFormatter(console_formatter)

    # Add handlers to logger
    logger.addHandler(file_handler)      # Service-specific file
    logger.addHandler(combined_handler)  # Combined file
    logger.addHandler(error_handler)     # Errors only
    logger.addHandler(console_handler)   # Console output

    # Prevent propagation to root logger to avoid duplicate messages
    logger.propagate = False

    return logger


def setup_uvicorn_logging():
    """Configure uvicorn logging to use our file-based system."""

    # Create logs directory
    log_dir = Path("src/logs")
    log_dir.mkdir(parents=True, exist_ok=True)

    # Uvicorn access log
    uvicorn_access_file = log_dir / "uvicorn_access.log"
    uvicorn_access_handler = logging.handlers.RotatingFileHandler(
        uvicorn_access_file,
        maxBytes=20 * 1024 * 1024,  # 20MB
        backupCount=5,
        encoding='utf-8'
    )
    uvicorn_access_handler.setFormatter(logging.Formatter(
        '%(asctime)s | %(name)s | %(levelname)s | %(message)s'
    ))

    # Configure uvicorn loggers
    uvicorn_access_logger = logging.getLogger("uvicorn.access")
    uvicorn_access_logger.handlers.clear()
    uvicorn_access_logger.addHandler(uvicorn_access_handler)
    uvicorn_access_logger.setLevel(logging.INFO)
    uvicorn_access_logger.propagate = False

    # Uvicorn error log
    uvicorn_error_file = log_dir / "uvicorn_error.log"
    uvicorn_error_handler = logging.handlers.RotatingFileHandler(
        uvicorn_error_file,
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    uvicorn_error_handler.setFormatter(logging.Formatter(
        '%(asctime)s | %(name)s | %(levelname)s | %(message)s'
    ))

    uvicorn_logger = logging.getLogger("uvicorn")
    uvicorn_logger.handlers.clear()
    uvicorn_logger.addHandler(uvicorn_error_handler)
    uvicorn_logger.setLevel(logging.INFO)
    uvicorn_logger.propagate = False


def get_service_logger(service_name: str) -> logging.Logger:
    """
    Get or create a logger for a specific service.

    Args:
        service_name: Name of the service

    Returns:
        Logger instance for the service
    """
    logger_name = f"presgen_assess.{service_name}"

    # Check if logger already exists
    if logger_name in logging.Logger.manager.loggerDict:
        return logging.getLogger(logger_name)

    # Create new logger
    return setup_file_logging(service_name)


def log_application_startup():
    """Log application startup information."""
    startup_logger = get_service_logger("startup")

    startup_logger.info("=" * 80)
    startup_logger.info("🚀 PresGen-Assess Application Starting")
    startup_logger.info("=" * 80)
    startup_logger.info(f"📅 Startup Time: {datetime.now().isoformat()}")
    startup_logger.info(f"🐍 Python Version: {sys.version}")
    startup_logger.info(f"📂 Working Directory: {os.getcwd()}")
    startup_logger.info(f"🔧 Debug Mode: {settings.debug}")
    startup_logger.info(f"📊 Log Level: {settings.log_level}")
    startup_logger.info(f"🗄️ Database URL: {settings.database_url[:50]}...")
    startup_logger.info("=" * 80)


def log_application_shutdown():
    """Log application shutdown information."""
    shutdown_logger = get_service_logger("shutdown")

    shutdown_logger.info("=" * 80)
    shutdown_logger.info("🔄 PresGen-Assess Application Shutting Down")
    shutdown_logger.info(f"📅 Shutdown Time: {datetime.now().isoformat()}")
    shutdown_logger.info("=" * 80)


# Pre-configured loggers for different services
CERTIFICATION_LOGGER = None
DATABASE_LOGGER = None
API_LOGGER = None
WORKFLOW_LOGGER = None
ASSESSMENT_LOGGER = None

def initialize_service_loggers():
    """Initialize all service-specific loggers."""
    global CERTIFICATION_LOGGER, DATABASE_LOGGER, API_LOGGER, WORKFLOW_LOGGER, ASSESSMENT_LOGGER

    CERTIFICATION_LOGGER = setup_file_logging("certifications")
    DATABASE_LOGGER = setup_file_logging("database")
    API_LOGGER = setup_file_logging("api")
    WORKFLOW_LOGGER = setup_file_logging("workflows")
    ASSESSMENT_LOGGER = setup_file_logging("assessments")

    # Setup uvicorn logging
    setup_uvicorn_logging()


# Convenience functions for getting loggers
def get_certification_logger() -> logging.Logger:
    """Get the certification service logger."""
    global CERTIFICATION_LOGGER
    if CERTIFICATION_LOGGER is None:
        CERTIFICATION_LOGGER = setup_file_logging("certifications")
    return CERTIFICATION_LOGGER

def get_database_logger() -> logging.Logger:
    """Get the database service logger."""
    global DATABASE_LOGGER
    if DATABASE_LOGGER is None:
        DATABASE_LOGGER = setup_file_logging("database")
    return DATABASE_LOGGER

def get_api_logger() -> logging.Logger:
    """Get the API service logger."""
    global API_LOGGER
    if API_LOGGER is None:
        API_LOGGER = setup_file_logging("api")
    return API_LOGGER

def get_workflow_logger() -> logging.Logger:
    """Get the workflow service logger."""
    global WORKFLOW_LOGGER
    if WORKFLOW_LOGGER is None:
        WORKFLOW_LOGGER = setup_file_logging("workflows")
    return WORKFLOW_LOGGER

def get_assessment_logger() -> logging.Logger:
    """Get the assessment service logger."""
    global ASSESSMENT_LOGGER
    if ASSESSMENT_LOGGER is None:
        ASSESSMENT_LOGGER = setup_file_logging("assessments")
    return ASSESSMENT_LOGGER