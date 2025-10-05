import logging
from logging.handlers import RotatingFileHandler
import os

# Create logs directory if it doesn't exist
os.makedirs("logs", exist_ok=True)

# Configure course generation logger
course_gen_logger = logging.getLogger("course_generation")
course_gen_logger.setLevel(logging.INFO)

# File handler with rotation (10MB max, keep 5 backups)
file_handler = RotatingFileHandler(
    "logs/course_generation.log",
    maxBytes=10*1024*1024,  # 10MB
    backupCount=5
)
file_handler.setLevel(logging.INFO)

# Format: timestamp | level | message
formatter = logging.Formatter(
    '%(asctime)s | %(levelname)-8s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
file_handler.setFormatter(formatter)

course_gen_logger.addHandler(file_handler)

# Prevent propagation to root logger
course_gen_logger.propagate = False

def log_course_event(event: str, **kwargs):
    """Log course generation event with context"""
    context = " | ".join([f"{k}={v}" for k, v in kwargs.items()])
    course_gen_logger.info(f"{event} | {context}")