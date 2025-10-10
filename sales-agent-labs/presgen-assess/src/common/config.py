"""Configuration management for PresGen-Assess (lightweight env loader)."""

import os
from pathlib import Path
from typing import Optional
from dataclasses import dataclass

# Get the project root directory (where .env should be)
PROJECT_ROOT = Path(__file__).parent.parent.parent
ENV_FILE = PROJECT_ROOT / ".env"

# Basic .env loader (handles KEY=VALUE lines)
if ENV_FILE.exists():
    with ENV_FILE.open() as env_fp:
        for raw_line in env_fp:
            line = raw_line.strip()
            if not line or line.startswith('#'):
                continue
            if '=' not in line:
                continue
            key, value = line.split('=', 1)
            os.environ.setdefault(key.strip(), value.strip())


@dataclass
class Settings:
    """Application settings loaded from environment variables."""

    # Database Configuration
    database_url: str = os.getenv(
        "DATABASE_URL",
        "postgresql+asyncpg://presgen_assess_user:secure_password@localhost:5432/presgen_assess",
    )
    chroma_db_path: str = os.getenv("CHROMA_DB_PATH", "./knowledge-base/embeddings")

    # OpenAI API Configuration
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "test-key")
    openai_org_id: Optional[str] = os.getenv("OPENAI_ORG_ID")

    # Google Cloud & OAuth Configuration
    google_application_credentials: Optional[str] = os.getenv(
        "GOOGLE_APPLICATION_CREDENTIALS",
        "./config/google-service-account.json",
    )
    google_cloud_project: Optional[str] = os.getenv("GOOGLE_CLOUD_PROJECT")
    oauth_client_json: Optional[str] = os.getenv("OAUTH_CLIENT_JSON")
    google_user_token_path: Optional[str] = os.getenv("GOOGLE_USER_TOKEN_PATH")
    google_drive_parent_folder_id: Optional[str] = os.getenv("GOOGLE_DRIVE_PARENT_FOLDER_ID")

    # Google Sheets Authentication Method
    use_oauth_for_sheets: bool = os.getenv("USE_OAUTH_FOR_SHEETS", "false").lower() == "true"
    oauth_sheets_client: str = os.getenv(
        "OAUTH_SHEETS_CLIENT",
        "/Users/yitzchak/Documents/learn/presentation_project/sales-agent-labs/oauth_slides_client.json",
    )

    # Standardized OAuth Token Path
    oauth_token_path: str = os.getenv(
        "OAUTH_TOKEN_PATH",
        "/Users/yitzchak/Documents/learn/presentation_project/sales-agent-labs/token.json",
    )

    # PresGen Module Integration (40-slide support)
    presgen_core_url: str = os.getenv("PRESGEN_CORE_URL", "http://localhost:8080")
    presgen_avatar_url: str = os.getenv("PRESGEN_AVATAR_URL", "http://localhost:8002")
    presgen_core_max_slides: int = int(os.getenv("PRESGEN_CORE_MAX_SLIDES", "40"))
    presgen_avatar_max_slides: int = int(os.getenv("PRESGEN_AVATAR_MAX_SLIDES", "40"))
    presgen_use_mock: Optional[bool] = (
        None
        if os.getenv("PRESGEN_USE_MOCK") is None
        else os.getenv("PRESGEN_USE_MOCK").lower() == "true"
    )
    presgen_core_voice_profile: str = os.getenv("PRESGEN_CORE_VOICE_PROFILE", "OpenAI Demo Voice (Your Audio)")
    presgen_core_quality_level: str = os.getenv("PRESGEN_CORE_QUALITY_LEVEL", "fast")
    presgen_core_use_cache: bool = os.getenv("PRESGEN_CORE_USE_CACHE", "false").lower() == "true"
    presgen_core_timeout_seconds: float = float(os.getenv("PRESGEN_CORE_TIMEOUT_SECONDS", "600"))
    presgen_avatar_timeout_seconds: float = float(os.getenv("PRESGEN_AVATAR_TIMEOUT_SECONDS", "900"))
    avatar_output_dir: Path = Path(
        os.getenv("AVATAR_OUTPUT_DIR", PROJECT_ROOT / "presgen-assess" / "avatar-output")
    ).resolve()

    # Workflow Settings (Async-aware)
    max_concurrent_workflows: int = int(os.getenv("MAX_CONCURRENT_WORKFLOWS", "10"))
    assessment_timeout_minutes: int = int(os.getenv("ASSESSMENT_TIMEOUT_MINUTES", "60"))
    async_workflow_enabled: bool = os.getenv("ASYNC_WORKFLOW_ENABLED", "true").lower() == "true"
    workflow_resume_token_ttl_hours: int = int(os.getenv("WORKFLOW_RESUME_TOKEN_TTL_HOURS", "72"))
    max_slides_supported: int = int(os.getenv("MAX_SLIDES_SUPPORTED", "40"))

    # Performance Settings
    presentation_generation_timeout_seconds: int = int(os.getenv("PRESENTATION_GENERATION_TIMEOUT_SECONDS", "600"))
    avatar_generation_timeout_seconds: int = int(os.getenv("AVATAR_GENERATION_TIMEOUT_SECONDS", "900"))
    rag_source_citation_required: bool = os.getenv("RAG_SOURCE_CITATION_REQUIRED", "true").lower() == "true"

    # Development Settings
    debug: bool = os.getenv("DEBUG", "false").lower() == "true"
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    enable_cors: bool = os.getenv("ENABLE_CORS", "true").lower() == "true"

    # Rate Limiting Settings
    enable_rate_limiting: bool = os.getenv("ENABLE_RATE_LIMITING", "true").lower() == "true"
    rate_limit_calls: int = int(os.getenv("RATE_LIMIT_CALLS", "100"))
    rate_limit_window_minutes: int = int(os.getenv("RATE_LIMIT_WINDOW_MINUTES", "15"))

    # Redis Configuration
    redis_url: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")

    # API Configuration
    api_v1_prefix: str = os.getenv("API_V1_PREFIX", "/api/v1")
    secret_key: str = os.getenv("SECRET_KEY", "change-me-in-production")


# Global settings instance
settings = Settings()

# Debug logging to verify settings are loaded correctly
import logging
import sys
logger = logging.getLogger(__name__)
print(f"📁 ENV_FILE path: {ENV_FILE}", file=sys.stderr)
print(f"🔍 ENV_FILE exists: {ENV_FILE.exists()}", file=sys.stderr)
print(f"🗄️  Database URL loaded: {settings.database_url}", file=sys.stderr)
print(f"🔧 Port Configuration (Standardized 2025-10-04):", file=sys.stderr)
print(f"  📡 PresGen-Core URL: {settings.presgen_core_url}", file=sys.stderr)
print(f"  📡 PresGen-Avatar URL: {settings.presgen_avatar_url}", file=sys.stderr)
print(f"  📡 PresGen-Core Max Slides: {settings.presgen_core_max_slides}", file=sys.stderr)
logger.info(f"📁 ENV_FILE path: {ENV_FILE}")
logger.info(f"🔍 ENV_FILE exists: {ENV_FILE.exists()}")
logger.info(f"🗄️  Database URL loaded: {settings.database_url}")
logger.info(f"🔧 Port Configuration (Standardized 2025-10-04):")
logger.info(f"  📡 PresGen-Core URL: {settings.presgen_core_url}")
logger.info(f"  📡 PresGen-Avatar URL: {settings.presgen_avatar_url}")
logger.info(f"  📡 PresGen-Core Max Slides: {settings.presgen_core_max_slides}")


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
