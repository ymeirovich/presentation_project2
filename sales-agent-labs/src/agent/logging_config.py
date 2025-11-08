import logging
import os
from pathlib import Path


def setup_logging() -> None:
    """
    Global logging config.
    LOG_LEVEL controls app logs; HTTP_DEBUG=1 enables verbose HTTP logs for GOOGLE API.
    All logs are sent to both terminal and the directory indicated by PRESGEN_LOG_DIR (defaults to src/logs/).
    """
    from datetime import datetime
    
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    
    # Determine log directory (supports container override)
    logs_dir_env = os.getenv("PRESGEN_LOG_DIR")
    if logs_dir_env:
        logs_dir = Path(logs_dir_env).expanduser()
    else:
        logs_dir = Path(__file__).resolve().parent.parent / "logs"

    logs_dir.mkdir(parents=True, exist_ok=True)
    
    # Create timestamped log file for main application logs
    app_log_file = logs_dir / f"presgen-{datetime.now().strftime('%Y%m%d-%H%M%S')}.log"
    
    # Configure logging with both console and file handlers
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[
            logging.StreamHandler(),  # Console output
            logging.FileHandler(app_log_file)  # File output
        ]
    )
    
    print(f"📝 Main App Logs: ENABLED → {app_log_file}")
    # Quiet noise libs by default
    logging.getLogger("google").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)

    # Optional: flip on wire-level HTTP logs when debugging
    if os.getenv("HTTP_DEBUG") == "1":
        # googleapiclient uses httplib2; these loggers surface request/response info
        logging.getLogger("googleapiclient.discovery").setLevel(logging.DEBUG)
        logging.getLogger("googleapiclient.discovery_cache").setLevel(logging.DEBUG)
        logging.getLogger("googleapiclient.http").setLevel(logging.DEBUG)
        logging.getLogger("httplib2").setLevel(logging.DEBUG)


# def setup_logging() -> None:
#     """
#     Configure global logging for the entire application.
#     Reads LOG_LEVEL from environment (.env) or defaults to INFO.
#     """
#     log_level = "INFO"

#     logging.basicConfig(
#         level=log_level,
#         format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
#         datefmt="%Y-%m-%d %H:%M:%S",
#     )

#     # Reduce noise from overly chatty libraries
#     logging.getLogger("google").setLevel(logging.WARNING)
#     logging.getLogger("urllib3").setLevel(logging.WARNING)
