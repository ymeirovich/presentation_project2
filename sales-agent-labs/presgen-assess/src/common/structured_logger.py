"""Structured logging for Sprint 0+ features.

Sprint 0 Deliverable: Enhanced structured logging for Gap Analysis → Avatar workflow.
Integrates with existing logging_config.py file logging system.
"""

import logging
import time
from typing import Dict, Any, Optional
from uuid import UUID

from src.common.enhanced_logging import (
    set_correlation_id,
    get_correlation_id,
)


# Mapping of service names to logger getters
_LOGGER_GETTERS = {}


def _get_logger_for_service(service_name: str) -> logging.Logger:
    """Get logger for a specific service using existing logging_config."""
    # Lazy import to avoid circular dependencies
    if not _LOGGER_GETTERS:
        from src.common.logging_config import (
            get_gap_analysis_logger,
            get_sheets_export_logger,
            get_presgen_core_logger,
            get_presgen_avatar_logger,
            get_workflow_logger,
        )
        _LOGGER_GETTERS.update({
            "gap_analysis": get_gap_analysis_logger,
            "sheets_export": get_sheets_export_logger,
            "presgen_core": get_presgen_core_logger,
            "presgen_avatar": get_presgen_avatar_logger,
            "workflow_orchestrator": get_workflow_logger,
        })

    getter = _LOGGER_GETTERS.get(service_name)
    if getter:
        return getter()
    else:
        # Fallback to generic logger
        from src.common.logging_config import setup_file_logging
        return setup_file_logging(service_name)


class StructuredLogger:
    """Structured logger for workflow stages with correlation ID tracking.

    Integrates with existing logging_config.py to write to src/logs/*.log files.
    """

    def __init__(self, service_name: str):
        """Initialize structured logger for a service.

        Args:
            service_name: Name of the service (e.g., 'gap_analysis', 'sheets_export')
        """
        self.service_name = service_name
        self.logger = _get_logger_for_service(service_name)

    def _build_log_context(
        self,
        event: str,
        workflow_id: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Build common log context with correlation ID."""
        context = {
            "event": event,
            "service": self.service_name,
            "correlation_id": get_correlation_id() or "no-correlation",
        }

        if workflow_id:
            context["workflow_id"] = str(workflow_id) if isinstance(workflow_id, UUID) else workflow_id

        context.update(kwargs)
        return context

    # Sprint 1: AI Question Generation
    def log_ai_generation_start(
        self,
        workflow_id: str,
        certification_profile_id: str,
        question_count: int,
        difficulty: str
    ):
        """Log start of AI question generation."""
        context = self._build_log_context(
            event="ai_generation_start",
            workflow_id=workflow_id,
            certification_profile_id=str(certification_profile_id),
            question_count=question_count,
            difficulty=difficulty,
        )
        self.logger.info("AI question generation started", extra=context)

    def log_ai_generation_complete(
        self,
        workflow_id: str,
        questions_generated: int,
        quality_score: float,
        generation_time_ms: float
    ):
        """Log completion of AI question generation."""
        context = self._build_log_context(
            event="ai_generation_complete",
            workflow_id=workflow_id,
            questions_generated=questions_generated,
            quality_score=quality_score,
            generation_time_ms=generation_time_ms,
        )
        self.logger.info("AI question generation completed", extra=context)

    def log_ai_generation_error(
        self,
        workflow_id: str,
        error: str,
        fallback_used: bool = False
    ):
        """Log AI question generation error."""
        context = self._build_log_context(
            event="ai_generation_error",
            workflow_id=workflow_id,
            error=error,
            fallback_used=fallback_used,
        )
        self.logger.error("AI question generation failed", extra=context)

    # Sprint 1: Gap Analysis Dashboard
    def log_gap_analysis_start(
        self,
        workflow_id: str,
        question_count: int,
        certification_profile_id: str
    ):
        """Log start of gap analysis processing."""
        context = self._build_log_context(
            event="gap_analysis_start",
            workflow_id=workflow_id,
            question_count=question_count,
            certification_profile_id=str(certification_profile_id),
        )
        self.logger.info("Gap analysis started", extra=context)

    def log_gap_analysis_complete(
        self,
        workflow_id: str,
        overall_score: float,
        skill_gaps_count: int,
        processing_time_ms: float
    ):
        """Log completion of gap analysis."""
        context = self._build_log_context(
            event="gap_analysis_complete",
            workflow_id=workflow_id,
            overall_score=overall_score,
            skill_gaps_count=skill_gaps_count,
            processing_time_ms=processing_time_ms,
        )
        self.logger.info("Gap analysis completed", extra=context)

    def log_gap_analysis_persistence(
        self,
        workflow_id: str,
        gap_analysis_id: str,
        content_outlines_count: int,
        recommended_courses_count: int
    ):
        """Log Gap Analysis data persistence to database."""
        context = self._build_log_context(
            event="gap_analysis_persistence",
            workflow_id=workflow_id,
            gap_analysis_id=str(gap_analysis_id),
            content_outlines_count=content_outlines_count,
            recommended_courses_count=recommended_courses_count,
        )
        self.logger.info("Gap Analysis data persisted to database", extra=context)

    def log_text_summary_generation(
        self,
        workflow_id: str,
        summary_length: int,
        generation_time_ms: float
    ):
        """Log generation of plain language text summary."""
        context = self._build_log_context(
            event="text_summary_generation",
            workflow_id=workflow_id,
            summary_length=summary_length,
            generation_time_ms=generation_time_ms,
        )
        self.logger.info("Text summary generated", extra=context)

    # Sprint 1: Dashboard UI Interactions
    def log_dashboard_load(
        self,
        workflow_id: str,
        user_id: str,
        load_time_ms: float
    ):
        """Log Gap Analysis Dashboard load."""
        context = self._build_log_context(
            event="dashboard_load",
            workflow_id=workflow_id,
            user_id=user_id,
            load_time_ms=load_time_ms,
        )
        self.logger.info("Gap Analysis Dashboard loaded", extra=context)

    def log_dashboard_tab_switch(
        self,
        workflow_id: str,
        from_tab: str,
        to_tab: str
    ):
        """Log tab switch in dashboard."""
        context = self._build_log_context(
            event="dashboard_tab_switch",
            workflow_id=workflow_id,
            from_tab=from_tab,
            to_tab=to_tab,
        )
        self.logger.info("Dashboard tab switched", extra=context)

    def log_chart_interaction(
        self,
        workflow_id: str,
        chart_type: str,
        interaction_type: str  # hover, click, expand
    ):
        """Log user interaction with charts."""
        context = self._build_log_context(
            event="chart_interaction",
            workflow_id=workflow_id,
            chart_type=chart_type,
            interaction_type=interaction_type,
        )
        self.logger.info("Chart interaction", extra=context)

    # Sprint 2: Google Sheets Export
    def log_sheets_export_start(
        self,
        workflow_id: str,
        user_id: str,
        export_format: str = "4-tab"
    ):
        """Log start of Google Sheets export."""
        context = self._build_log_context(
            event="sheets_export_start",
            workflow_id=workflow_id,
            user_id=user_id,
            export_format=export_format,
        )
        self.logger.info("Google Sheets export started", extra=context)

    def log_sheets_export_complete(
        self,
        workflow_id: str,
        sheet_id: str,
        sheet_url: str,
        export_time_ms: float,
        tabs_created: int = 4
    ):
        """Log completion of Google Sheets export."""
        context = self._build_log_context(
            event="sheets_export_complete",
            workflow_id=workflow_id,
            sheet_id=sheet_id,
            sheet_url=sheet_url,
            export_time_ms=export_time_ms,
            tabs_created=tabs_created,
        )
        self.logger.info("Google Sheets export completed", extra=context)

    def log_sheets_export_error(
        self,
        workflow_id: str,
        error: str,
        error_type: str  # api_error, data_error, permission_error
    ):
        """Log Google Sheets export error."""
        context = self._build_log_context(
            event="sheets_export_error",
            workflow_id=workflow_id,
            error=error,
            error_type=error_type,
        )
        self.logger.error("Google Sheets export failed", extra=context)

    # Sprint 2: RAG Content Retrieval
    def log_rag_retrieval_start(
        self,
        workflow_id: str,
        skill_gap_id: str,
        query: str
    ):
        """Log start of RAG content retrieval."""
        context = self._build_log_context(
            event="rag_retrieval_start",
            workflow_id=workflow_id,
            skill_gap_id=str(skill_gap_id),
            query=query[:100],  # Truncate long queries
        )
        self.logger.info("RAG content retrieval started", extra=context)

    def log_rag_retrieval_complete(
        self,
        workflow_id: str,
        skill_gap_id: str,
        content_items_found: int,
        retrieval_time_ms: float,
        avg_relevance_score: float
    ):
        """Log completion of RAG content retrieval."""
        context = self._build_log_context(
            event="rag_retrieval_complete",
            workflow_id=workflow_id,
            skill_gap_id=str(skill_gap_id),
            content_items_found=content_items_found,
            retrieval_time_ms=retrieval_time_ms,
            avg_relevance_score=avg_relevance_score,
        )
        self.logger.info("RAG content retrieval completed", extra=context)

    # Sprint 3: PresGen-Core Integration
    def log_presgen_core_request(
        self,
        workflow_id: str,
        skill_gap_id: str,
        slide_count: int
    ):
        """Log PresGen-Core presentation generation request."""
        context = self._build_log_context(
            event="presgen_core_request",
            workflow_id=workflow_id,
            skill_gap_id=str(skill_gap_id),
            slide_count=slide_count,
        )
        self.logger.info("PresGen-Core request initiated", extra=context)

    def log_presgen_core_complete(
        self,
        workflow_id: str,
        presentation_id: str,
        slides_generated: int,
        generation_time_ms: float
    ):
        """Log PresGen-Core presentation generation completion."""
        context = self._build_log_context(
            event="presgen_core_complete",
            workflow_id=workflow_id,
            presentation_id=presentation_id,
            slides_generated=slides_generated,
            generation_time_ms=generation_time_ms,
        )
        self.logger.info("PresGen-Core presentation generated", extra=context)

    # Sprint 4: PresGen-Avatar Integration
    def log_avatar_generation_start(
        self,
        workflow_id: str,
        course_id: str,
        mode: str = "presentation-only"
    ):
        """Log start of PresGen-Avatar course generation."""
        context = self._build_log_context(
            event="avatar_generation_start",
            workflow_id=workflow_id,
            course_id=str(course_id),
            mode=mode,
        )
        self.logger.info("PresGen-Avatar course generation started", extra=context)

    def log_avatar_generation_progress(
        self,
        workflow_id: str,
        course_id: str,
        elapsed_seconds: float,
        progress_percentage: Optional[float] = None
    ):
        """Log PresGen-Avatar generation progress update."""
        context = self._build_log_context(
            event="avatar_generation_progress",
            workflow_id=workflow_id,
            course_id=str(course_id),
            elapsed_seconds=elapsed_seconds,
        )
        if progress_percentage is not None:
            context["progress_percentage"] = progress_percentage

        self.logger.info("PresGen-Avatar generation progress", extra=context)

    def log_avatar_generation_complete(
        self,
        workflow_id: str,
        course_id: str,
        video_url: str,
        total_time_seconds: float,
        video_duration_seconds: float
    ):
        """Log completion of PresGen-Avatar course generation."""
        context = self._build_log_context(
            event="avatar_generation_complete",
            workflow_id=workflow_id,
            course_id=str(course_id),
            video_url=video_url,
            total_time_seconds=total_time_seconds,
            video_duration_seconds=video_duration_seconds,
        )
        self.logger.info("PresGen-Avatar course generated", extra=context)

    def log_course_launch(
        self,
        workflow_id: str,
        course_id: str,
        user_id: str,
        launch_method: str  # video_player, download, external_link
    ):
        """Log course launch action."""
        context = self._build_log_context(
            event="course_launch",
            workflow_id=workflow_id,
            course_id=str(course_id),
            user_id=user_id,
            launch_method=launch_method,
        )
        self.logger.info("Course launched", extra=context)

    # Generic workflow logging
    def log_workflow_error(
        self,
        workflow_id: str,
        error: str,
        step: str,
        traceback: Optional[str] = None
    ):
        """Log workflow error."""
        context = self._build_log_context(
            event="workflow_error",
            workflow_id=workflow_id,
            error=error,
            step=step,
        )
        if traceback:
            context["traceback"] = traceback

        self.logger.error("Workflow error occurred", extra=context)

    def log_feature_flag_check(
        self,
        feature_name: str,
        enabled: bool,
        workflow_id: Optional[str] = None
    ):
        """Log feature flag check."""
        context = self._build_log_context(
            event="feature_flag_check",
            feature_name=feature_name,
            enabled=enabled,
        )
        if workflow_id:
            context["workflow_id"] = workflow_id

        self.logger.info(f"Feature flag '{feature_name}' checked: {enabled}", extra=context)


# Pre-configured structured loggers for each service
def get_gap_analysis_logger() -> StructuredLogger:
    """Get structured logger for Gap Analysis service."""
    return StructuredLogger("gap_analysis")


def get_sheets_export_logger() -> StructuredLogger:
    """Get structured logger for Google Sheets export service."""
    return StructuredLogger("sheets_export")


def get_presgen_core_logger() -> StructuredLogger:
    """Get structured logger for PresGen-Core integration."""
    return StructuredLogger("presgen_core")


def get_presgen_avatar_logger() -> StructuredLogger:
    """Get structured logger for PresGen-Avatar integration."""
    return StructuredLogger("presgen_avatar")


def get_workflow_logger() -> StructuredLogger:
    """Get structured logger for workflow orchestration."""
    return StructuredLogger("workflow_orchestrator")