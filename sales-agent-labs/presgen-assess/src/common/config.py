"""Configuration management for PresGen-Assess."""

import os
from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings with environment variable support."""

    # Database Configuration
    database_url: str = Field(
        default="postgresql+asyncpg://presgen_assess_user:secure_password@localhost:5432/presgen_assess",
        alias="DATABASE_URL"
    )
    chroma_db_path: str = Field(default="./knowledge-base/embeddings", alias="CHROMA_DB_PATH")

    # OpenAI API Configuration
    openai_api_key: str = Field(..., alias="OPENAI_API_KEY")
    openai_org_id: Optional[str] = Field(default=None, alias="OPENAI_ORG_ID")

    # Google Cloud Configuration
    google_application_credentials: Optional[str] = Field(
        default="./config/google-service-account.json",
        alias="GOOGLE_APPLICATION_CREDENTIALS"
    )
    google_cloud_project: Optional[str] = Field(default=None, alias="GOOGLE_CLOUD_PROJECT")

    # PresGen Module Integration (40-slide support)
    presgen_core_url: str = Field(default="http://localhost:8001", alias="PRESGEN_CORE_URL")
    presgen_avatar_url: str = Field(default="http://localhost:8002", alias="PRESGEN_AVATAR_URL")
    presgen_core_max_slides: int = Field(default=40, alias="PRESGEN_CORE_MAX_SLIDES")
    presgen_avatar_max_slides: int = Field(default=40, alias="PRESGEN_AVATAR_MAX_SLIDES")

    # Workflow Settings (Async-aware)
    max_concurrent_workflows: int = Field(default=10, alias="MAX_CONCURRENT_WORKFLOWS")
    assessment_timeout_minutes: int = Field(default=60, alias="ASSESSMENT_TIMEOUT_MINUTES")
    async_workflow_enabled: bool = Field(default=True, alias="ASYNC_WORKFLOW_ENABLED")
    workflow_resume_token_ttl_hours: int = Field(default=72, alias="WORKFLOW_RESUME_TOKEN_TTL_HOURS")
    max_slides_supported: int = Field(default=40, alias="MAX_SLIDES_SUPPORTED")

    # Performance Settings
    presentation_generation_timeout_seconds: int = Field(
        default=600, alias="PRESENTATION_GENERATION_TIMEOUT_SECONDS"
    )
    avatar_generation_timeout_seconds: int = Field(
        default=900, alias="AVATAR_GENERATION_TIMEOUT_SECONDS"
    )
    rag_source_citation_required: bool = Field(default=True, alias="RAG_SOURCE_CITATION_REQUIRED")

    # Development Settings
    debug: bool = Field(default=False, alias="DEBUG")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    enable_cors: bool = Field(default=True, alias="ENABLE_CORS")

    # Redis Configuration
    redis_url: str = Field(default="redis://localhost:6379/0", alias="REDIS_URL")

    # API Configuration
    api_v1_prefix: str = Field(default="/api/v1", alias="API_V1_PREFIX")
    secret_key: str = Field(default="change-me-in-production", alias="SECRET_KEY")

    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = Settings()


def get_database_url() -> str:
    """Get database URL for SQLAlchemy."""
    return settings.database_url


def get_async_database_url() -> str:
    """Get async database URL for asyncpg."""
    url = settings.database_url
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+asyncpg://", 1)
    elif not url.startswith("postgresql+asyncpg://"):
        return f"postgresql+asyncpg://{url}"
    return url