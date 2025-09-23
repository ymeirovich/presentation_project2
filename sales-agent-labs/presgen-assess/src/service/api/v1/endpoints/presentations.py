"""Presentation Service API endpoints for personalized presentation generation."""

import logging
from typing import Dict, List, Optional

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from src.services.presentation_service import PresentationGenerationService

logger = logging.getLogger(__name__)

router = APIRouter()


# Request/Response Models
class PresentationRequest(BaseModel):
    """Request model for personalized presentation generation."""
    assessment_results: Dict = Field(..., description="Assessment results data")
    gap_analysis: Dict = Field(..., description="Gap analysis results")
    certification_profile: Dict = Field(..., description="Certification profile information")
    target_slide_count: int = Field(default=20, ge=1, le=40, description="Target number of slides")
    presentation_title: Optional[str] = Field(default=None, description="Custom presentation title")


class BulkPresentationRequest(BaseModel):
    """Request model for bulk presentation generation."""
    generation_requests: List[Dict] = Field(..., description="List of presentation generation requests")
    max_concurrent: int = Field(default=5, ge=1, le=10, description="Maximum concurrent generations")


class PresentationResponse(BaseModel):
    """Response model for presentation generation."""
    success: bool
    generation_id: str
    presentation_url: Optional[str] = None
    slide_count: int
    quality_metrics: Dict
    gap_coverage: Dict
    rag_sources_used: List[str]
    estimated_duration_minutes: int


class BulkPresentationResponse(BaseModel):
    """Response model for bulk presentation generation."""
    success: bool
    total_requests: int
    successful_generations: List[str]
    failed_generations: List[Dict]
    success_rate: float
    total_processing_time_seconds: float


class PresentationStatusResponse(BaseModel):
    """Response model for presentation status."""
    generation_id: str
    status: str
    progress_percentage: float
    estimated_completion_minutes: Optional[int] = None
    result_url: Optional[str] = None
    error_message: Optional[str] = None


class HealthCheckResponse(BaseModel):
    """Response model for health check."""
    status: str
    presgen_core_accessible: bool
    service_ready: bool
    max_concurrent_generations: int
    error: Optional[str] = None


# Initialize Presentation Service (will be mocked in tests)
try:
    presentation_service = PresentationGenerationService()
except Exception:
    # Fallback for testing/mocking scenarios
    presentation_service = None


@router.post("/generate", response_model=PresentationResponse, status_code=status.HTTP_200_OK)
async def generate_personalized_presentation(request: PresentationRequest) -> PresentationResponse:
    """
    Generate a personalized presentation based on assessment and gap analysis.

    Creates a tailored presentation that addresses identified learning gaps
    and provides focused content for exam preparation.
    """
    try:
        logger.info(f"🔄 Generating personalized presentation with {request.target_slide_count} slides")

        result = await presentation_service.generate_personalized_presentation(
            assessment_results=request.assessment_results,
            gap_analysis=request.gap_analysis,
            certification_profile=request.certification_profile,
            target_slide_count=request.target_slide_count,
            presentation_title=request.presentation_title
        )

        if not result.get("success", False):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Presentation generation failed: {result.get('error', 'Unknown error')}"
            )

        logger.info(f"✅ Generated presentation with {result.get('slide_count', 0)} slides")

        return PresentationResponse(
            success=result["success"],
            generation_id=result["generation_id"],
            presentation_url=result.get("presentation_url"),
            slide_count=result["slide_count"],
            quality_metrics=result["quality_metrics"],
            gap_coverage=result["gap_coverage"],
            rag_sources_used=result["rag_sources_used"],
            estimated_duration_minutes=result["estimated_duration_minutes"]
        )

    except Exception as e:
        logger.error(f"❌ Presentation generation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate presentation: {str(e)}"
        )


@router.post("/bulk/generate", response_model=BulkPresentationResponse, status_code=status.HTTP_200_OK)
async def generate_bulk_presentations(request: BulkPresentationRequest) -> BulkPresentationResponse:
    """
    Generate multiple presentations concurrently.

    Processes multiple presentation generation requests in parallel
    for efficient batch processing of user assessments.
    """
    try:
        logger.info(f"🔄 Starting bulk generation of {len(request.generation_requests)} presentations")

        result = await presentation_service.generate_bulk_presentations(
            generation_requests=request.generation_requests,
            max_concurrent=request.max_concurrent
        )

        if not result.get("success", False):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Bulk generation failed: {result.get('error', 'Unknown error')}"
            )

        logger.info(f"✅ Bulk generation completed - {len(result['successful_generations'])} successful")

        return BulkPresentationResponse(
            success=result["success"],
            total_requests=result["total_requests"],
            successful_generations=result["successful_generations"],
            failed_generations=result["failed_generations"],
            success_rate=result["success_rate"],
            total_processing_time_seconds=result["total_processing_time_seconds"]
        )

    except Exception as e:
        logger.error(f"❌ Bulk presentation generation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate bulk presentations: {str(e)}"
        )


@router.get("/status/{generation_id}", response_model=PresentationStatusResponse)
async def get_presentation_status(generation_id: str) -> PresentationStatusResponse:
    """
    Get the status of a presentation generation request.

    Provides real-time status updates for long-running presentation
    generation tasks with progress tracking.
    """
    try:
        logger.info(f"🔄 Checking status for generation {generation_id}")

        result = await presentation_service.get_presentation_status(generation_id)

        return PresentationStatusResponse(
            generation_id=generation_id,
            status=result["status"],
            progress_percentage=result["progress_percentage"],
            estimated_completion_minutes=result.get("estimated_completion_minutes"),
            result_url=result.get("result_url"),
            error_message=result.get("error_message")
        )

    except Exception as e:
        logger.error(f"❌ Failed to get presentation status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get presentation status: {str(e)}"
        )


@router.post("/content/adapt", status_code=status.HTTP_200_OK)
async def adapt_content_for_presentation(
    course_outline: Dict,
    target_slide_count: int,
    gap_analysis: Dict
) -> Dict:
    """
    Adapt course content for optimal presentation structure.

    Optimizes content organization and slide distribution based on
    learning gaps and presentation constraints.
    """
    try:
        logger.info(f"🔄 Adapting content for {target_slide_count} slides")

        result = presentation_service._adapt_content_for_presentation(
            course_outline=course_outline,
            target_slide_count=target_slide_count,
            gap_analysis=gap_analysis
        )

        logger.info("✅ Content adaptation completed")
        return result

    except Exception as e:
        logger.error(f"❌ Content adaptation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to adapt content: {str(e)}"
        )


@router.post("/structure/optimize", status_code=status.HTTP_200_OK)
async def structure_presentation_content(
    content_outline: List[str],
    learning_objectives: List[str],
    target_slide_count: int,
    difficulty_level: str
) -> Dict:
    """
    Structure and optimize presentation content organization.

    Creates an optimal presentation structure with logical flow
    and appropriate content distribution across slides.
    """
    try:
        logger.info("🔄 Structuring presentation content")

        result = presentation_service._structure_presentation_content(
            content_outline=content_outline,
            learning_objectives=learning_objectives,
            target_slide_count=target_slide_count,
            difficulty_level=difficulty_level
        )

        logger.info("✅ Content structuring completed")
        return result

    except Exception as e:
        logger.error(f"❌ Content structuring failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to structure content: {str(e)}"
        )


@router.post("/quality/analyze", status_code=status.HTTP_200_OK)
async def analyze_presentation_quality(
    presentation_content: Dict,
    gap_analysis: Dict,
    target_slide_count: int
) -> Dict:
    """
    Analyze presentation quality and coverage metrics.

    Evaluates how well the presentation addresses learning gaps
    and meets quality standards for effective learning.
    """
    try:
        logger.info("🔄 Analyzing presentation quality")

        # Analyze gap coverage
        gap_coverage = presentation_service._analyze_gap_coverage(
            presentation_content=presentation_content,
            gap_analysis=gap_analysis
        )

        # Calculate quality metrics
        quality_metrics = presentation_service._calculate_quality_metrics(
            presentation_content=presentation_content,
            target_slide_count=target_slide_count,
            gap_coverage=gap_coverage
        )

        result = {
            "gap_coverage": gap_coverage,
            "quality_metrics": quality_metrics,
            "recommendations": []
        }

        # Add recommendations based on analysis
        if gap_coverage["coverage_percentage"] < 80:
            result["recommendations"].append("Consider adding more content to address learning gaps")

        if quality_metrics["overall_quality_score"] < 0.7:
            result["recommendations"].append("Review content organization and slide distribution")

        logger.info("✅ Quality analysis completed")
        return result

    except Exception as e:
        logger.error(f"❌ Quality analysis failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to analyze presentation quality: {str(e)}"
        )


@router.get("/health", response_model=HealthCheckResponse)
async def presentation_health_check() -> HealthCheckResponse:
    """
    Check presentation service health and PresGen-Core connectivity.

    Verifies that the presentation service and PresGen-Core API
    are accessible and ready to process generation requests.
    """
    try:
        logger.info("🔄 Performing presentation service health check")

        health_result = await presentation_service.health_check()

        return HealthCheckResponse(
            status=health_result["status"],
            presgen_core_accessible=health_result["presgen_core_accessible"],
            service_ready=health_result["service_ready"],
            max_concurrent_generations=health_result["max_concurrent_generations"],
            error=health_result.get("error")
        )

    except Exception as e:
        logger.error(f"❌ Presentation health check failed: {e}")
        return HealthCheckResponse(
            status="unhealthy",
            presgen_core_accessible=False,
            service_ready=False,
            max_concurrent_generations=0,
            error=str(e)
        )


@router.get("/capabilities")
async def get_presentation_capabilities() -> Dict:
    """
    Get detailed information about presentation service capabilities.

    Returns comprehensive information about supported features,
    limitations, and configuration options for presentation generation.
    """
    try:
        return {
            "supported_formats": ["google_slides", "powerpoint", "pdf"],
            "slide_limits": {
                "minimum": 1,
                "maximum": 40,
                "recommended_range": [15, 25]
            },
            "content_types": [
                "learning_objectives",
                "concept_explanations",
                "examples",
                "practice_questions",
                "summary_slides"
            ],
            "customization_options": {
                "presentation_title": True,
                "difficulty_adaptation": True,
                "gap_focus": True,
                "time_estimation": True,
                "source_attribution": True
            },
            "quality_metrics": [
                "content_relevance",
                "gap_coverage",
                "slide_distribution",
                "learning_flow",
                "source_attribution"
            ],
            "integration": {
                "presgen_core": True,
                "rag_enhancement": True,
                "bulk_processing": True,
                "status_tracking": True
            }
        }

    except Exception as e:
        logger.error(f"❌ Failed to retrieve capabilities: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve presentation capabilities: {str(e)}"
        )