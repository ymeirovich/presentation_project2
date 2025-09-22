"""FastAPI application factory and configuration for PresGen-Assess."""

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse

from src.common.config import settings
from src.service.api.v1.router import api_router
from src.service.database import init_db
from src.service.middleware import RequestLoggingMiddleware

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    logger.info("🚀 Starting PresGen-Assess application")

    # Initialize database
    try:
        await init_db()
        logger.info("✅ Database initialized successfully")
    except Exception as e:
        logger.error(f"❌ Database initialization failed: {e}")
        raise

    yield

    logger.info("🔄 Shutting down PresGen-Assess application")


def create_app() -> FastAPI:
    """Create and configure FastAPI application."""

    app = FastAPI(
        title="PresGen-Assess API",
        description="AI-powered certification assessment and presentation generation",
        version="1.0.0",
        docs_url="/docs" if settings.debug else None,
        redoc_url="/redoc" if settings.debug else None,
        lifespan=lifespan
    )

    # Security middleware
    if not settings.debug:
        app.add_middleware(
            TrustedHostMiddleware,
            allowed_hosts=["localhost", "127.0.0.1", "*.presgen-assess.com"]
        )

    # CORS middleware
    if settings.enable_cors:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"] if settings.debug else ["https://presgen-assess.com"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    # Custom middleware
    app.add_middleware(RequestLoggingMiddleware)

    # Include API routes
    app.include_router(api_router, prefix=settings.api_v1_prefix)

    # Health check endpoint
    @app.get("/health")
    async def health_check():
        """Application health check."""
        return {"status": "healthy", "service": "presgen-assess"}

    # Global exception handler
    @app.exception_handler(Exception)
    async def global_exception_handler(request, exc):
        logger.error(f"❌ Unhandled exception: {exc}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error"}
        )

    return app


# Application instance
app = create_app()