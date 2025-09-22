"""Custom middleware for PresGen-Assess FastAPI application."""

import logging
import time
import uuid
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

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