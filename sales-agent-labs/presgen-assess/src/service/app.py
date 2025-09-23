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
from src.service.middleware import RequestLoggingMiddleware, RateLimitingMiddleware

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
        description="""
## AI-Powered Certification Assessment and Presentation Generation

**PresGen-Assess** is a comprehensive API for creating intelligent certification assessments and personalized learning presentations.

### Core Features

🤖 **AI-Powered Assessment Generation**
- LLM-based question generation with RAG context enhancement
- Adaptive difficulty and domain balancing
- Quality validation and Bloom's taxonomy integration

📊 **Intelligent Gap Analysis**
- Confidence pattern analysis and overconfidence detection
- Skill level assessment across certification domains
- Personalized remediation planning with priority actions

📱 **Dynamic Presentation Generation**
- Integration with PresGen-Core for slide creation
- Content adaptation based on learning gaps
- Bulk processing with concurrent generation

### Authentication

Most endpoints require authentication using JWT tokens. Get started with:

1. **Demo Token**: `POST /api/v1/auth/demo-token` for development
2. **Login**: `POST /api/v1/auth/login` with credentials
3. **Use Token**: Include `Authorization: Bearer <token>` header

### Rate Limiting

API requests are rate-limited to 100 calls per 15-minute window per IP address.
Rate limit headers are included in responses.
        """,
        version="3.0.0",
        contact={
            "name": "PresGen-Assess API Support",
            "email": "support@presgen-assess.com"
        },
        license_info={
            "name": "MIT License",
            "url": "https://opensource.org/licenses/MIT"
        },
        docs_url="/docs" if settings.debug else None,
        redoc_url="/redoc" if settings.debug else None,
        lifespan=lifespan,
        tags_metadata=[
            {
                "name": "authentication",
                "description": "User authentication and authorization endpoints"
            },
            {
                "name": "ai-services",
                "description": "AI-powered services for assessment and analysis"
            },
            {
                "name": "llm",
                "description": "Large Language Model services for content generation"
            },
            {
                "name": "assessment-engine",
                "description": "Comprehensive assessment generation and validation"
            },
            {
                "name": "gap-analysis",
                "description": "Learning gap identification and remediation planning"
            },
            {
                "name": "presentations",
                "description": "Personalized presentation generation and management"
            },
            {
                "name": "certifications",
                "description": "Certification profile management"
            },
            {
                "name": "assessments",
                "description": "Assessment CRUD operations"
            },
            {
                "name": "knowledge",
                "description": "Knowledge base and RAG context management"
            },
            {
                "name": "workflows",
                "description": "End-to-end workflow orchestration"
            }
        ]
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
    if settings.enable_rate_limiting:
        app.add_middleware(
            RateLimitingMiddleware,
            calls_per_window=getattr(settings, 'rate_limit_calls', 100),
            window_minutes=getattr(settings, 'rate_limit_window_minutes', 15)
        )

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


# Application instance (conditional for testing)
import os
if os.getenv("TESTING") != "1":
    app = create_app()
else:
    app = None