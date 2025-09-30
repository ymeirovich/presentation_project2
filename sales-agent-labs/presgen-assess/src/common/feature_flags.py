"""Feature flag management for PresGen-Assess.

Sprint 0 Deliverable: Feature flag system for controlled rollout of new features.
"""

import os
from typing import Dict, Optional
from pydantic import Field
from pydantic_settings import BaseSettings


class FeatureFlagSettings(BaseSettings):
    """Feature flags for gradual rollout of new functionality."""

    # Sprint 1: AI Question Generation + Gap Analysis Dashboard
    enable_ai_question_generation: bool = Field(
        default=False,
        alias="ENABLE_AI_QUESTION_GENERATION",
        description="Enable AI-powered question generation using RAG"
    )
    enable_gap_dashboard_enhancements: bool = Field(
        default=False,
        alias="ENABLE_GAP_DASHBOARD_ENHANCEMENTS",
        description="Enable enhanced Gap Analysis Dashboard with tabs, text summary, charts"
    )

    # Sprint 2: Google Sheets Export
    enable_sheets_export: bool = Field(
        default=False,
        alias="ENABLE_SHEETS_EXPORT",
        description="Enable on-demand Google Sheets export (4-tab format)"
    )

    # Sprint 3: PresGen-Core Integration
    enable_presgen_core_integration: bool = Field(
        default=False,
        alias="ENABLE_PRESGEN_CORE_INTEGRATION",
        description="Enable PresGen-Core integration for slide generation"
    )

    # Sprint 4: PresGen-Avatar Integration
    enable_presgen_avatar_integration: bool = Field(
        default=False,
        alias="ENABLE_PRESGEN_AVATAR_INTEGRATION",
        description="Enable PresGen-Avatar integration (Presentation-only mode)"
    )

    # Sprint 5: Advanced Features
    enable_course_timer_tracker: bool = Field(
        default=False,
        alias="ENABLE_COURSE_TIMER_TRACKER",
        description="Enable timer tracker for course generation progress"
    )
    enable_video_player_integration: bool = Field(
        default=False,
        alias="ENABLE_VIDEO_PLAYER_INTEGRATION",
        description="Enable in-app video player for generated courses"
    )

    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"


# Global feature flags instance
_feature_flags: Optional[FeatureFlagSettings] = None


def get_feature_flags() -> FeatureFlagSettings:
    """Get feature flags instance (singleton pattern)."""
    global _feature_flags
    if _feature_flags is None:
        _feature_flags = FeatureFlagSettings()
    return _feature_flags


def is_feature_enabled(feature_name: str) -> bool:
    """Check if a specific feature flag is enabled.

    Args:
        feature_name: Name of the feature flag attribute

    Returns:
        bool: True if feature is enabled, False otherwise

    Example:
        >>> if is_feature_enabled("enable_ai_question_generation"):
        >>>     # Use AI question generation
        >>>     pass
    """
    flags = get_feature_flags()
    return getattr(flags, feature_name, False)


def get_all_feature_flags() -> Dict[str, bool]:
    """Get all feature flags as a dictionary.

    Returns:
        Dict mapping feature names to their enabled status
    """
    flags = get_feature_flags()
    return {
        "enable_ai_question_generation": flags.enable_ai_question_generation,
        "enable_gap_dashboard_enhancements": flags.enable_gap_dashboard_enhancements,
        "enable_sheets_export": flags.enable_sheets_export,
        "enable_presgen_core_integration": flags.enable_presgen_core_integration,
        "enable_presgen_avatar_integration": flags.enable_presgen_avatar_integration,
        "enable_course_timer_tracker": flags.enable_course_timer_tracker,
        "enable_video_player_integration": flags.enable_video_player_integration,
    }


def reload_feature_flags() -> None:
    """Force reload of feature flags from environment.

    Useful for testing or when environment variables change.
    """
    global _feature_flags
    _feature_flags = None