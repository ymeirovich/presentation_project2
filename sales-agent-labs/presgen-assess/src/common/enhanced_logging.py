"""
Enhanced logging configuration for data flow tracking.
Provides correlation ID support and structured logging for UI->DB->UI data flow.
"""

import logging
import json
import time
from uuid import uuid4, UUID
from typing import Dict, Any, Optional, Union
from contextvars import ContextVar
from functools import wraps
from datetime import datetime


# Context variable for correlation ID
correlation_id_var: ContextVar[Optional[str]] = ContextVar('correlation_id', default=None)


class EnhancedJSONEncoder(json.JSONEncoder):
    """Custom JSON encoder that handles UUID and other complex types."""

    def default(self, obj):
        try:
            if isinstance(obj, UUID):
                return str(obj)
            elif isinstance(obj, datetime):
                return obj.isoformat()
            elif hasattr(obj, '__dict__'):
                # Handle objects with dictionaries (like SQLAlchemy models)
                return {k: v for k, v in obj.__dict__.items() if not k.startswith('_')}
            elif hasattr(obj, 'isoformat'):
                # Handle date/datetime objects
                return obj.isoformat()
            else:
                # Fallback to string representation
                return str(obj)
        except Exception:
            # Ultimate fallback for any serialization errors
            return f"<non-serializable: {type(obj).__name__}>"


class CorrelationIDFilter(logging.Filter):
    """Add correlation ID to log records."""

    def filter(self, record):
        correlation_id = correlation_id_var.get()
        record.correlation_id = correlation_id or 'no-correlation-id'
        return True


class DataFlowFormatter(logging.Formatter):
    """Structured formatter for data flow logging."""

    def format(self, record):
        log_entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'correlation_id': getattr(record, 'correlation_id', 'no-correlation-id'),
            'message': record.getMessage(),
            'step': getattr(record, 'step', None),
            'component': getattr(record, 'component', None),
            'data_before': getattr(record, 'data_before', None),
            'data_after': getattr(record, 'data_after', None),
            'transformation': getattr(record, 'transformation', None),
            'duration_ms': getattr(record, 'duration_ms', None),
            'success': getattr(record, 'success', None),
            'error': getattr(record, 'error', None)
        }

        # Remove None values for cleaner logs
        log_entry = {k: v for k, v in log_entry.items() if v is not None}

        try:
            return json.dumps(log_entry, indent=2, cls=EnhancedJSONEncoder)
        except TypeError as e:
            # Fallback for serialization issues
            safe_entry = {k: str(v) if not isinstance(v, (str, int, float, bool, type(None))) else v
                         for k, v in log_entry.items()}
            return json.dumps(safe_entry, indent=2)


def setup_enhanced_logging():
    """Setup enhanced logging configuration."""
    # Create formatters
    data_flow_formatter = DataFlowFormatter()

    # Create handlers
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(data_flow_formatter)
    console_handler.addFilter(CorrelationIDFilter())

    # Configure loggers for different components
    loggers = [
        'kb_prompts.database',
        'kb_prompts.api',
        'kb_prompts.proxy',
        'kb_prompts.ui',
        'cert_prompts.database',
        'cert_prompts.api',
        'cert_prompts.proxy',
        'cert_prompts.ui',
        'data_flow'
    ]

    for logger_name in loggers:
        logger = logging.getLogger(logger_name)
        logger.setLevel(logging.INFO)
        logger.addHandler(console_handler)
        logger.propagate = False

    return loggers


def set_correlation_id(correlation_id: str = None) -> str:
    """Set correlation ID for current context."""
    if correlation_id is None:
        correlation_id = str(uuid4())

    correlation_id_var.set(correlation_id)
    return correlation_id


def get_correlation_id() -> Optional[str]:
    """Get current correlation ID."""
    return correlation_id_var.get()


def log_data_flow(
    logger: logging.Logger,
    step: str,
    component: str,
    message: str,
    data_before: Optional[Dict[str, Any]] = None,
    data_after: Optional[Dict[str, Any]] = None,
    transformation: Optional[str] = None,
    duration_ms: Optional[float] = None,
    success: Optional[bool] = None,
    error: Optional[str] = None
):
    """Log data flow with structured information."""
    extra = {
        'step': step,
        'component': component,
        'data_before': data_before,
        'data_after': data_after,
        'transformation': transformation,
        'duration_ms': duration_ms,
        'success': success,
        'error': error
    }

    # Remove None values
    extra = {k: v for k, v in extra.items() if v is not None}

    if error:
        logger.error(message, extra=extra)
    elif success is False:
        logger.warning(message, extra=extra)
    else:
        logger.info(message, extra=extra)


def track_data_transformation(
    logger: logging.Logger,
    step: str,
    component: str
):
    """Decorator to track data transformations."""
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = time.time()
            correlation_id = get_correlation_id()

            # Extract data before transformation
            data_before = None
            if args:
                # Try to extract data from first argument (usually the data object)
                try:
                    if hasattr(args[0], '__dict__'):
                        data_before = args[0].__dict__
                    elif isinstance(args[0], dict):
                        data_before = args[0]
                except:
                    pass

            try:
                result = await func(*args, **kwargs)
                duration_ms = (time.time() - start_time) * 1000

                # Extract data after transformation
                data_after = None
                if result:
                    try:
                        if hasattr(result, '__dict__'):
                            data_after = result.__dict__
                        elif isinstance(result, dict):
                            data_after = result
                    except:
                        pass

                log_data_flow(
                    logger=logger,
                    step=step,
                    component=component,
                    message=f"Data transformation completed: {func.__name__}",
                    data_before=data_before,
                    data_after=data_after,
                    transformation=func.__name__,
                    duration_ms=duration_ms,
                    success=True
                )

                return result

            except Exception as e:
                duration_ms = (time.time() - start_time) * 1000

                log_data_flow(
                    logger=logger,
                    step=step,
                    component=component,
                    message=f"Data transformation failed: {func.__name__}",
                    data_before=data_before,
                    transformation=func.__name__,
                    duration_ms=duration_ms,
                    success=False,
                    error=str(e)
                )

                raise

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            start_time = time.time()
            correlation_id = get_correlation_id()

            # Extract data before transformation
            data_before = None
            if args:
                try:
                    if hasattr(args[0], '__dict__'):
                        data_before = args[0].__dict__
                    elif isinstance(args[0], dict):
                        data_before = args[0]
                except:
                    pass

            try:
                result = func(*args, **kwargs)
                duration_ms = (time.time() - start_time) * 1000

                # Extract data after transformation
                data_after = None
                if result:
                    try:
                        if hasattr(result, '__dict__'):
                            data_after = result.__dict__
                        elif isinstance(result, dict):
                            data_after = result
                    except:
                        pass

                log_data_flow(
                    logger=logger,
                    step=step,
                    component=component,
                    message=f"Data transformation completed: {func.__name__}",
                    data_before=data_before,
                    data_after=data_after,
                    transformation=func.__name__,
                    duration_ms=duration_ms,
                    success=True
                )

                return result

            except Exception as e:
                duration_ms = (time.time() - start_time) * 1000

                log_data_flow(
                    logger=logger,
                    step=step,
                    component=component,
                    message=f"Data transformation failed: {func.__name__}",
                    data_before=data_before,
                    transformation=func.__name__,
                    duration_ms=duration_ms,
                    success=False,
                    error=str(e)
                )

                raise

        # Return appropriate wrapper based on function type
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


# Pre-configured loggers for different components
KB_PROMPTS_DB_LOGGER = logging.getLogger('kb_prompts.database')
KB_PROMPTS_API_LOGGER = logging.getLogger('kb_prompts.api')
KB_PROMPTS_PROXY_LOGGER = logging.getLogger('kb_prompts.proxy')
KB_PROMPTS_UI_LOGGER = logging.getLogger('kb_prompts.ui')

CERT_PROMPTS_DB_LOGGER = logging.getLogger('cert_prompts.database')
CERT_PROMPTS_API_LOGGER = logging.getLogger('cert_prompts.api')
CERT_PROMPTS_PROXY_LOGGER = logging.getLogger('cert_prompts.proxy')
CERT_PROMPTS_UI_LOGGER = logging.getLogger('cert_prompts.ui')

DATA_FLOW_LOGGER = logging.getLogger('data_flow')


# Phase-Specific Logging Enhancements

def log_assessment_generation_start(assessment_params: Dict, correlation_id: str = None):
    """Log start of assessment generation with detailed parameters."""
    logger = logging.getLogger("assessment_engine.generation")

    log_data_flow(
        message="Assessment generation started",
        step="generation_start",
        component="assessment_engine",
        data_before={
            "certification_profile_id": assessment_params.get("certification_profile_id"),
            "question_count": assessment_params.get("question_count"),
            "difficulty_level": assessment_params.get("difficulty_level"),
            "balance_domains": assessment_params.get("balance_domains", True),
            "use_rag_context": assessment_params.get("use_rag_context", True)
        },
        correlation_id=correlation_id or get_correlation_id()
    )


def log_google_forms_creation(form_data: Dict, correlation_id: str = None):
    """Log Google Forms creation with metadata."""
    logger = logging.getLogger("google_forms.creation")

    log_data_flow(
        message="Google Form creation initiated",
        step="form_creation_start",
        component="google_forms_service",
        data_before={
            "form_title": form_data.get("form_title"),
            "question_count": len(form_data.get("questions", [])),
            "settings": form_data.get("settings", {}),
            "assessment_id": form_data.get("assessment_id")
        },
        correlation_id=correlation_id or get_correlation_id()
    )


def log_google_api_usage(api_call: Dict, correlation_id: str = None):
    """Log Google API usage with rate limiting and quota tracking."""
    logger = logging.getLogger("google_api.usage")

    logger.info(
        "Google API call executed",
        extra={
            "correlation_id": correlation_id or get_correlation_id(),
            "api_service": api_call.get("service"),
            "api_method": api_call.get("method"),
            "response_time_ms": api_call.get("response_time_ms"),
            "request_size_bytes": api_call.get("request_size_bytes"),
            "response_size_bytes": api_call.get("response_size_bytes"),
            "quota_usage": api_call.get("quota_usage", {}),
            "rate_limit_remaining": api_call.get("rate_limit_remaining"),
            "success": api_call.get("success", True)
        }
    )


def log_performance_metrics(component: str, metrics: Dict, correlation_id: str = None):
    """Log performance metrics for system monitoring."""
    logger = logging.getLogger(f"performance.{component}")

    logger.info(
        f"Performance metrics for {component}",
        extra={
            "correlation_id": correlation_id or get_correlation_id(),
            "component": component,
            "execution_time_seconds": metrics.get("execution_time_seconds"),
            "memory_usage_mb": metrics.get("memory_usage_mb"),
            "cpu_usage_percent": metrics.get("cpu_usage_percent"),
            "throughput_per_second": metrics.get("throughput_per_second"),
            "success_rate": metrics.get("success_rate"),
            "error_count": metrics.get("error_count", 0)
        }
    )


class PhaseAwareLogger:
    """Phase-aware logger that automatically tracks workflow progress."""

    def __init__(self, phase_name: str):
        self.phase_name = phase_name
        self.logger = logging.getLogger(f"phase.{phase_name}")
        self.start_time = time.time()

    def log_phase_start(self, phase_params: Dict):
        """Log the start of a workflow phase."""
        log_data_flow(
            message=f"Phase {self.phase_name} started",
            step=f"{self.phase_name}_phase_start",
            component=f"phase_{self.phase_name}",
            data_before=phase_params,
            correlation_id=get_correlation_id()
        )

    def log_phase_completion(self, phase_results: Dict):
        """Log the completion of a workflow phase."""
        execution_time = time.time() - self.start_time

        log_data_flow(
            message=f"Phase {self.phase_name} completed",
            step=f"{self.phase_name}_phase_complete",
            component=f"phase_{self.phase_name}",
            data_after={
                **phase_results,
                "execution_time_seconds": execution_time,
                "phase_success": phase_results.get("success", True)
            },
            correlation_id=get_correlation_id()
        )

    def log_phase_error(self, error: Exception, context: Dict = None):
        """Log phase execution errors with context."""
        execution_time = time.time() - self.start_time

        log_data_flow(
            message=f"Phase {self.phase_name} failed",
            step=f"{self.phase_name}_phase_error",
            component=f"phase_{self.phase_name}",
            error_details={
                "error_type": type(error).__name__,
                "error_message": str(error),
                "execution_time_seconds": execution_time,
                "context": context or {}
            },
            correlation_id=get_correlation_id()
        )


# Phase-specific pre-configured loggers
ASSESSMENT_ENGINE_LOGGER = logging.getLogger('assessment_engine')
GOOGLE_FORMS_LOGGER = logging.getLogger('google_forms')
RESPONSE_PROCESSOR_LOGGER = logging.getLogger('response_processor')
GAP_ANALYSIS_LOGGER = logging.getLogger('gap_analysis')
PRESGEN_INTEGRATION_LOGGER = logging.getLogger('presgen_integration')
AVATAR_GENERATOR_LOGGER = logging.getLogger('avatar_generator')
GOOGLE_API_LOGGER = logging.getLogger('google_api')
PERFORMANCE_LOGGER = logging.getLogger('performance')

# Initialize logging on import
setup_enhanced_logging()