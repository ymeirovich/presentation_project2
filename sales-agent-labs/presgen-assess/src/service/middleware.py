"""Custom middleware for PresGen-Assess FastAPI application."""

import logging
import time
import uuid
from typing import Callable

from fastapi import Request, Response, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware

from src.service.auth import rate_limiter

logger = logging.getLogger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for request/response logging with correlation IDs."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Generate correlation ID for request tracking
        correlation_id = str(uuid.uuid4())

        # Add correlation ID to request state
        request.state.correlation_id = correlation_id

        # Log incoming request
        start_time = time.time()
        logger.info(
            f"➡️ {request.method} {request.url.path}",
            extra={
                "correlation_id": correlation_id,
                "method": request.method,
                "path": request.url.path,
                "query_params": str(request.query_params),
                "client_ip": request.client.host if request.client else None
            }
        )

        try:
            # Process request
            response = await call_next(request)

            # Calculate processing time
            process_time = time.time() - start_time

            # Log response
            logger.info(
                f"⬅️ {response.status_code} {request.method} {request.url.path} ({process_time:.3f}s)",
                extra={
                    "correlation_id": correlation_id,
                    "status_code": response.status_code,
                    "process_time": process_time
                }
            )

            # Add correlation ID to response headers
            response.headers["X-Correlation-ID"] = correlation_id

            return response

        except Exception as e:
            # Log error
            process_time = time.time() - start_time
            logger.error(
                f"❌ Error processing {request.method} {request.url.path} ({process_time:.3f}s): {e}",
                extra={
                    "correlation_id": correlation_id,
                    "error": str(e)
                },
                exc_info=True
            )
            raise


class RateLimitingMiddleware(BaseHTTPMiddleware):
    """Middleware for API rate limiting."""

    def __init__(self, app, calls_per_window: int = 100, window_minutes: int = 15):
        super().__init__(app)
        self.calls_per_window = calls_per_window
        self.window_minutes = window_minutes

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip rate limiting for health checks and docs
        if request.url.path in ["/health", "/docs", "/redoc", "/openapi.json"]:
            return await call_next(request)

        # Get client identifier (IP address)
        client_ip = request.client.host if request.client else "unknown"
        client_id = f"ip:{client_ip}"

        # Check rate limit
        if not rate_limiter.is_allowed(client_id, self.calls_per_window, self.window_minutes):
            logger.warning(f"🚦 Rate limit exceeded for {client_ip}")
            return Response(
                content='{"detail": "Rate limit exceeded. Please try again later."}',
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                headers={
                    "Content-Type": "application/json",
                    "Retry-After": str(self.window_minutes * 60),
                    "X-RateLimit-Limit": str(self.calls_per_window),
                    "X-RateLimit-Window": f"{self.window_minutes}m"
                }
            )

        # Process request
        response = await call_next(request)

        # Add rate limit headers
        stats = rate_limiter.get_stats(client_id)
        response.headers["X-RateLimit-Limit"] = str(self.calls_per_window)
        response.headers["X-RateLimit-Remaining"] = str(stats["remaining_capacity"])
        response.headers["X-RateLimit-Window"] = f"{self.window_minutes}m"

        return response