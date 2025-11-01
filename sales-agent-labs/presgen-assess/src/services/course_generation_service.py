"""Centralised logging helpers for Sprint 4 course generation."""

import logging
from logging.handlers import RotatingFileHandler
import os
from typing import Any


_LOGGER_NAME = "course_generation"
_LOG_PATH = "logs/course_generation.log"
_debug_logger = logging.getLogger(__name__)


def _ensure_logger() -> logging.Logger:
    """Configure the course generation logger once and return it."""

    logger = logging.getLogger(_LOGGER_NAME)
    if logger.handlers:
        return logger

    os.makedirs(os.path.dirname(_LOG_PATH) or ".", exist_ok=True)

    logger.setLevel(logging.INFO)

    file_handler = RotatingFileHandler(
        _LOG_PATH,
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5,
    )
    file_handler.setLevel(logging.INFO)
    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    logger.propagate = False
    return logger


def log_course_event(event: str, **kwargs: Any) -> None:
    """Log a structured course generation event."""

    if _debug_logger.isEnabledFor(logging.DEBUG):
        _debug_logger.debug(
            "course_generation_event | event=%s | context=%s",
            event,
            kwargs if kwargs else "{}",
        )

    logger = _ensure_logger()
    if kwargs:
        context = " | ".join(f"{k}={v}" for k, v in kwargs.items())
        logger.info("%s | %s", event, context)
    else:
        logger.info(event)
