from __future__ import annotations
import json, logging, time, uuid, os, sys
from typing import Any

# GCP debug logging setup - controlled by environment variable
_GCP_DEBUG_SETUP = False

def _setup_gcp_debug_logging():
    """Setup GCP client-level debug logging if enabled"""
    global _GCP_DEBUG_SETUP
    if _GCP_DEBUG_SETUP:
        return
    
    enable_gcp_debug = os.getenv("ENABLE_GCP_DEBUG_LOGGING", "false").lower() == "true"
    enable_cloud_logging = os.getenv("ENABLE_CLOUD_LOGGING", "false").lower() == "true"
    enable_local_debug_file = os.getenv("ENABLE_LOCAL_DEBUG_FILE", "false").lower() == "true"
    
    if enable_gcp_debug:
        # Enable detailed GCP client logging to terminal
        logging.getLogger('google.api_core').setLevel(logging.DEBUG)
        logging.getLogger('google.auth').setLevel(logging.DEBUG)
        logging.getLogger('google.cloud').setLevel(logging.DEBUG)
        logging.getLogger('googleapiclient').setLevel(logging.DEBUG)
        logging.getLogger('google_auth_httplib2').setLevel(logging.DEBUG)
        logging.getLogger('urllib3').setLevel(logging.DEBUG)
        
        # Only print to stdout if not in MCP server mode (which needs clean stdout for JSON-RPC)
        if os.getenv("MCP_SERVER_MODE") != "true":
            print(f"🔍 GCP Debug Logging: ENABLED (terminal output)")
        else:
            # Log to stderr in MCP server mode to avoid corrupting stdout
            print(f"🔍 GCP Debug Logging: ENABLED (terminal output)", file=sys.stderr)
    
    # Setup local debug file logging
    if enable_local_debug_file:
        try:
            from datetime import datetime
            import pathlib
            
            # Ensure logs directory exists - use presgen-video/logs if video logging enabled
            video_logging = os.getenv("PRESGEN_VIDEO_LOGGING", "false").lower() == "true"
            if video_logging:
                logs_dir = pathlib.Path("presgen-video/logs")
            else:
                logs_dir = pathlib.Path("src/logs")
            logs_dir.mkdir(exist_ok=True)
            
            debug_file = logs_dir / f"debug-gcp-{datetime.now().strftime('%Y%m%d-%H%M%S')}.log"
            
            file_handler = logging.FileHandler(debug_file)
            file_handler.setLevel(logging.DEBUG)
            
            # Detailed format for file logging
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            file_handler.setFormatter(formatter)
            
            # Add file handler to relevant loggers
            loggers_to_file = [
                'google.api_core', 'google.auth', 'google.cloud',
                'googleapiclient', 'google_auth_httplib2', 'urllib3',
                'agent.slides', 'mcp_lab.rpc_client', 'mcp.tools',
                # Training and avatar generation loggers
                'presgen_training2.orchestrator', 'presgen_training2.liveportrait',
                'presgen_training2.voice', 'presgen_training2.content',
                'presgen_training2.slides', 'presgen_training2.video',
                # HTTP service loggers
                'src.service.http', 'service.http', 'fastapi', 'uvicorn', 'uvicorn.access', 'uvicorn.error'
            ]

            # Add video-specific loggers if video logging is enabled
            if video_logging:
                video_loggers = [
                    'video_transcription', 'video_content', 'video_slides',
                    'video_phase2', 'video_phase3', 'video_audio', 'video_face'
                ]
                loggers_to_file.extend(video_loggers)
            
            for logger_name in loggers_to_file:
                logger = logging.getLogger(logger_name)
                logger.addHandler(file_handler)

            # If verbose logging is enabled, also add file handler to root logger to catch everything
            if os.getenv("ENABLE_VERBOSE_LOGGING", "false").lower() == "true":
                root_logger = logging.getLogger()
                root_logger.addHandler(file_handler)
                if os.getenv("MCP_SERVER_MODE") != "true":
                    print(f"📝 Verbose Logging: ENABLED - All logs will be written to file")
                else:
                    print(f"📝 Verbose Logging: ENABLED - All logs will be written to file", file=sys.stderr)

            if os.getenv("MCP_SERVER_MODE") != "true":
                print(f"📝 Local Debug File: ENABLED → {debug_file}")
            else:
                print(f"📝 Local Debug File: ENABLED → {debug_file}", file=sys.stderr)
            
        except Exception as e:
            print(f"⚠️  Local debug file setup failed: {e}")
    
    if enable_cloud_logging:
        try:
            import google.cloud.logging
            from google.cloud.logging_v2.handlers import CloudLoggingHandler
            
            client = google.cloud.logging.Client()
            handler = CloudLoggingHandler(client)
            
            # Add to root logger
            root_logger = logging.getLogger()
            root_logger.addHandler(handler)
            
            print(f"☁️  GCP Cloud Logging: ENABLED (sending to GCP)")
        except ImportError:
            print("⚠️  GCP Cloud Logging requested but google-cloud-logging not installed")
        except Exception as e:
            print(f"⚠️  GCP Cloud Logging setup failed: {e}")
    else:
        if os.getenv("MCP_SERVER_MODE") != "true":
            print(f"💰 GCP Cloud Logging: DISABLED (cost optimization)")
        else:
            print(f"💰 GCP Cloud Logging: DISABLED (cost optimization)", file=sys.stderr)
    
    _GCP_DEBUG_SETUP = True


def _json_serializable(obj):
    """Convert non-serializable objects to strings for JSON logging"""
    if isinstance(obj, bytes):
        try:
            return obj.decode('utf-8')
        except UnicodeDecodeError:
            return f"<bytes: {len(obj)} bytes>"
    elif hasattr(obj, '__dict__'):
        return str(obj)
    else:
        return str(obj)

def jlog(logger: logging.Logger, level: int, **kv: Any) -> None:
    # Setup GCP logging on first call
    _setup_gcp_debug_logging()

    kv.setdefault("ts_ms", int(time.time() * 1000))
    kv.setdefault("level", logging.getLevelName(level))
    if "req_id" not in kv:
        kv["req_id"] = str(uuid.uuid4())  # caller can override; useful for tracing

    # Add GCP correlation ID for debugging
    if os.getenv("ENABLE_GCP_DEBUG_LOGGING") == "true":
        # Use proper GCP trace format for correlation
        import socket
        trace_id = f"projects/{os.getenv('GOOGLE_CLOUD_PROJECT', 'unknown')}/traces/{uuid.uuid4().hex}"
        kv.setdefault("gcp_trace_id", trace_id)

    # Convert non-serializable objects to strings
    for key, value in kv.items():
        try:
            json.dumps(value)
        except (TypeError, ValueError):
            kv[key] = _json_serializable(value)

    logger.log(level, json.dumps(kv, ensure_ascii=False))
