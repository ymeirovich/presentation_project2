"""Main API v1 router for PresGen-Assess."""

from fastapi import APIRouter

from src.service.api.v1.endpoints import (
    assessments,
    certifications,
    knowledge,
    knowledge_prompts,
    google_forms,
    workflows,
    llm,
    engine,
    gap_analysis,
    gap_analysis_dashboard,
    presentations,
    auth,
    monitoring,
    ai_question_generation
)

api_router = APIRouter()

# Authentication endpoints (no auth required)
api_router.include_router(
    auth.router,
    prefix="/auth",
    tags=["authentication"]
)

# Include endpoint routers
api_router.include_router(
    certifications.router,
    prefix="/certifications",
    tags=["certifications"]
)

api_router.include_router(
    knowledge.router,
    prefix="/knowledge",
    tags=["knowledge"]
)

api_router.include_router(
    knowledge_prompts.router,
    prefix="/knowledge-prompts",
    tags=["knowledge-prompts"]
)

api_router.include_router(
    google_forms.router,
    prefix="/google-forms",
    tags=["google-forms"]
)

api_router.include_router(
    assessments.router,
    prefix="/assessments",
    tags=["assessments"]
)

api_router.include_router(
    workflows.router,
    prefix="/workflows",
    tags=["workflows"]
)

# Phase 2 Service Integration - AI-Powered Assessment and Analysis
api_router.include_router(
    llm.router,
    prefix="/llm",
    tags=["llm", "ai-services"]
)

api_router.include_router(
    engine.router,
    prefix="/engine",
    tags=["assessment-engine", "ai-services"]
)

api_router.include_router(
    gap_analysis.router,
    prefix="/gap-analysis",
    tags=["gap-analysis", "ai-services"]
)

# Sprint 1: Gap Analysis Dashboard
api_router.include_router(
    gap_analysis_dashboard.router,
    prefix="/gap-analysis-dashboard",
    tags=["gap-analysis-dashboard", "sprint-1"]
)

api_router.include_router(
    presentations.router,
    prefix="/presentations",
    tags=["presentations", "ai-services"]
)

# Sprint 3: Monitoring and production readiness endpoints
api_router.include_router(
    monitoring.router,
    prefix="/monitoring",
    tags=["monitoring", "health", "production"]
)

# Sprint 4: AI Question Generation
api_router.include_router(
    ai_question_generation.router,
    prefix="/ai-question-generator",
    tags=["AI Question Generation", "ai-services"]
)
