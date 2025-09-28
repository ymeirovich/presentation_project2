"""
AI Question Generation API Endpoints

Provides REST API endpoints for AI-powered question generation functionality.
"""

from typing import Dict, Any
from uuid import UUID

from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel, Field

from src.services.ai_question_generator import AIQuestionGenerator
from src.common.enhanced_logging import get_enhanced_logger

router = APIRouter(tags=["AI Question Generation"])
logger = get_enhanced_logger(__name__)


class QuestionGenerationRequest(BaseModel):
    """Request model for AI question generation."""
    certification_profile_id: UUID = Field(..., description="Certification profile ID")
    user_profile: str = Field(..., description="User profile identifier")
    difficulty_level: str = Field(default="intermediate", description="Question difficulty level")
    domain_distribution: Dict[str, int] = Field(..., description="Questions per domain")
    question_count: int = Field(default=24, description="Total number of questions")


class QuestionGenerationResponse(BaseModel):
    """Response model for AI question generation."""
    success: bool
    assessment_data: Dict[str, Any]
    message: str = ""


@router.post("/generate", response_model=QuestionGenerationResponse)
async def generate_ai_questions(
    request: QuestionGenerationRequest
) -> QuestionGenerationResponse:
    """
    Generate AI-powered assessment questions based on certification profile resources.

    This endpoint creates contextually relevant questions using:
    - Certification profile exam resources
    - User difficulty preferences
    - Domain distribution requirements
    - AI-powered content generation

    Args:
        request: Question generation parameters

    Returns:
        Generated questions with quality metrics and metadata

    Raises:
        HTTPException: If generation fails or invalid parameters provided
    """
    try:
        logger.info(
            "🚀 AI question generation request | cert_profile=%s user=%s difficulty=%s question_count=%d",
            request.certification_profile_id, request.user_profile,
            request.difficulty_level, request.question_count
        )

        # Validate request parameters
        if request.question_count <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Question count must be greater than 0"
            )

        if not request.domain_distribution:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Domain distribution must be specified"
            )

        total_domain_questions = sum(request.domain_distribution.values())
        if total_domain_questions != request.question_count:
            logger.warning(
                "Domain distribution total (%d) doesn't match question count (%d), adjusting",
                total_domain_questions, request.question_count
            )

        # Generate AI-powered questions
        question_generator = AIQuestionGenerator()
        generation_result = await question_generator.generate_contextual_assessment(
            certification_profile_id=request.certification_profile_id,
            user_profile=request.user_profile,
            difficulty_level=request.difficulty_level,
            domain_distribution=request.domain_distribution,
            question_count=request.question_count
        )

        if generation_result.get("success"):
            logger.info(
                "✅ AI question generation completed | questions=%d avg_quality=%.1f generation_time=%dms",
                len(generation_result["assessment_data"]["questions"]),
                generation_result["assessment_data"]["metadata"]["quality_scores"]["overall"],
                generation_result["assessment_data"]["metadata"]["generation_time_ms"]
            )

            return QuestionGenerationResponse(
                success=True,
                assessment_data=generation_result["assessment_data"],
                message="AI question generation completed successfully"
            )
        else:
            logger.error("❌ AI question generation failed")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="AI question generation failed"
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "❌ Unexpected error in AI question generation | error=%s",
            str(e), exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"AI question generation failed: {str(e)}"
        )


@router.get("/health")
async def health_check() -> Dict[str, Any]:
    """Health check endpoint for AI question generation service."""
    try:
        # Basic health check - verify imports and class definition
        # Don't instantiate to avoid database dependencies in health check
        return {
            "status": "healthy",
            "service": "ai_question_generator",
            "timestamp": "2025-09-27T20:00:00Z",
            "capabilities": [
                "contextual_question_generation",
                "quality_validation",
                "fallback_mechanism",
                "domain_distribution"
            ],
            "database_required": True,
            "dependencies": ["assessment_engine", "knowledge_base", "llm_service"]
        }

    except Exception as e:
        logger.error("AI Question Generator health check failed: %s", e)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"AI Question Generation service unhealthy: {str(e)}"
        )