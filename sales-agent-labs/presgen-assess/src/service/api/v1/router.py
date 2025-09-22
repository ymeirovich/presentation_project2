"""Main API v1 router for PresGen-Assess."""

from fastapi import APIRouter

from src.service.api.v1.endpoints import (
    assessments,
    certifications,
    knowledge,
    workflows
)

api_router = APIRouter()

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
    assessments.router,
    prefix="/assessments",
    tags=["assessments"]
)

api_router.include_router(
    workflows.router,
    prefix="/workflows",
    tags=["workflows"]
)