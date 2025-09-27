"""Enhanced PresGen integration service for connecting with PresGen-Core ecosystem."""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

import httpx
from pydantic import BaseModel, Field

from src.common.enhanced_logging import get_enhanced_logger
from src.common.config import settings
from src.services.form_response_processor import FormResponseProcessor


class PresGenRequest(BaseModel):
    """Request model for PresGen-Core integration."""
    assessment_id: str = Field(..., description="Assessment workflow ID")
    certification_profile: Dict[str, Any] = Field(..., description="Certification profile data")
    gap_analysis_results: Dict[str, Any] = Field(..., description="Gap analysis results")
    presentation_requirements: Dict[str, Any] = Field(default_factory=dict, description="Presentation customization")
    target_slide_count: int = Field(default=20, ge=1, le=40, description="Number of slides to generate")
    avatar_enabled: bool = Field(default=True, description="Enable avatar video generation")
    delivery_format: str = Field(default="presentation_with_video", description="Final delivery format")


class PresGenResponse(BaseModel):
    """Response model from PresGen-Core."""
    success: bool = Field(..., description="Operation success status")
    presgen_job_id: str = Field(..., description="PresGen job tracking ID")
    presentation_url: Optional[str] = Field(None, description="Generated presentation URL")
    video_url: Optional[str] = Field(None, description="Generated avatar video URL")
    estimated_completion_time: Optional[datetime] = Field(None, description="Estimated completion time")
    status: str = Field(..., description="Current generation status")
    error_message: Optional[str] = Field(None, description="Error details if failed")


class PresGenIntegrationService:
    """Service for integrating with PresGen-Core ecosystem for presentation and video generation."""

    def __init__(self):
        self.logger = get_enhanced_logger(__name__)
        self.presgen_core_url = getattr(settings, 'presgen_core_url', 'http://localhost:8080')
        self.response_processor = FormResponseProcessor()
        self._job_cache: Dict[str, Dict] = {}

    async def trigger_presgen_workflow(
        self,
        workflow_id: UUID,
        assessment_data: Dict[str, Any],
        gap_analysis_results: Dict[str, Any],
        certification_profile: Dict[str, Any],
        presentation_requirements: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Trigger PresGen-Core workflow for presentation and video generation."""
        correlation_id = f"presgen_{workflow_id}"

        self.logger.info("Triggering PresGen workflow", extra={
            "workflow_id": str(workflow_id),
            "correlation_id": correlation_id,
            "certification_name": certification_profile.get("certification_name"),
            "gap_areas_count": len(gap_analysis_results.get("gap_areas", []))
        })

        try:
            # Prepare PresGen request
            presgen_request = PresGenRequest(
                assessment_id=str(workflow_id),
                certification_profile=certification_profile,
                gap_analysis_results=gap_analysis_results,
                presentation_requirements=presentation_requirements or {},
                target_slide_count=presentation_requirements.get("slide_count", 20) if presentation_requirements else 20,
                avatar_enabled=presentation_requirements.get("avatar_enabled", True) if presentation_requirements else True
            )

            # Check if PresGen-Core is available
            if await self._check_presgen_availability():
                # Send request to PresGen-Core
                result = await self._send_presgen_request(presgen_request)
            else:
                # Use fallback local generation
                result = await self._generate_presentation_fallback(presgen_request)

            # Cache job for tracking
            if result["success"]:
                self._job_cache[result["presgen_job_id"]] = {
                    "workflow_id": str(workflow_id),
                    "created_at": datetime.utcnow().isoformat(),
                    "status": result["status"],
                    "correlation_id": correlation_id
                }

            return result

        except Exception as e:
            self.logger.error("PresGen workflow trigger failed", extra={
                "workflow_id": str(workflow_id),
                "correlation_id": correlation_id,
                "error": str(e)
            })
            return {
                "success": False,
                "error": f"PresGen integration failed: {str(e)}",
                "fallback_available": True
            }

    async def _check_presgen_availability(self) -> bool:
        """Check if PresGen-Core service is available."""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.presgen_core_url}/health")
                return response.status_code == 200
        except Exception as e:
            self.logger.warning("PresGen-Core not available", extra={
                "presgen_core_url": self.presgen_core_url,
                "error": str(e)
            })
            return False

    async def _send_presgen_request(self, request: PresGenRequest) -> Dict[str, Any]:
        """Send request to PresGen-Core service."""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.presgen_core_url}/api/v1/generate-presentation",
                    json=request.model_dump(),
                    headers={"Content-Type": "application/json"}
                )

                if response.status_code == 200:
                    result = response.json()
                    self.logger.info("PresGen request successful", extra={
                        "presgen_job_id": result.get("presgen_job_id"),
                        "assessment_id": request.assessment_id,
                        "status": result.get("status")
                    })
                    return result
                else:
                    error_msg = f"PresGen-Core returned {response.status_code}: {response.text}"
                    self.logger.error("PresGen request failed", extra={
                        "status_code": response.status_code,
                        "response_text": response.text,
                        "assessment_id": request.assessment_id
                    })
                    return {
                        "success": False,
                        "error": error_msg
                    }

        except Exception as e:
            self.logger.error("PresGen request exception", extra={
                "assessment_id": request.assessment_id,
                "error": str(e)
            })
            return {
                "success": False,
                "error": f"PresGen communication failed: {str(e)}"
            }

    async def _generate_presentation_fallback(self, request: PresGenRequest) -> Dict[str, Any]:
        """Fallback presentation generation when PresGen-Core is unavailable."""
        self.logger.info("Using fallback presentation generation", extra={
            "assessment_id": request.assessment_id
        })

        try:
            # Generate a simple presentation structure
            presentation_data = await self._create_fallback_presentation_structure(
                request.gap_analysis_results,
                request.certification_profile,
                request.target_slide_count
            )

            fallback_job_id = f"fallback_{uuid4()}"

            return {
                "success": True,
                "presgen_job_id": fallback_job_id,
                "status": "completed_fallback",
                "presentation_data": presentation_data,
                "avatar_enabled": False,
                "fallback_mode": True,
                "message": "Generated using fallback mode - PresGen-Core unavailable"
            }

        except Exception as e:
            self.logger.error("Fallback generation failed", extra={
                "assessment_id": request.assessment_id,
                "error": str(e)
            })
            return {
                "success": False,
                "error": f"Fallback generation failed: {str(e)}"
            }

    async def _create_fallback_presentation_structure(
        self,
        gap_analysis_results: Dict[str, Any],
        certification_profile: Dict[str, Any],
        target_slide_count: int
    ) -> Dict[str, Any]:
        """Create a basic presentation structure for fallback mode."""
        gaps = gap_analysis_results.get("gap_areas", [])
        cert_name = certification_profile.get("certification_name", "Certification")

        # Basic slide structure
        slides = []

        # Title slide
        slides.append({
            "type": "title",
            "title": f"{cert_name} - Personalized Learning Plan",
            "subtitle": "Based on Assessment Results",
            "content": []
        })

        # Assessment summary slide
        slides.append({
            "type": "summary",
            "title": "Assessment Summary",
            "content": [
                f"Assessment completed for {cert_name}",
                f"Identified {len(gaps)} key improvement areas",
                "Personalized learning recommendations generated"
            ]
        })

        # Gap analysis slides (up to target_slide_count - 3 for intro/conclusion)
        available_slides = max(1, target_slide_count - 3)
        gaps_per_slide = max(1, len(gaps) // available_slides) if gaps else 1

        for i in range(0, len(gaps), gaps_per_slide):
            slide_gaps = gaps[i:i + gaps_per_slide]
            slides.append({
                "type": "gap_analysis",
                "title": f"Improvement Area {i//gaps_per_slide + 1}",
                "content": [
                    f"Topic: {gap.get('domain', 'Unknown')}" for gap in slide_gaps
                ] + [
                    f"Recommendation: {gap.get('recommendation', 'Study this topic')}" for gap in slide_gaps
                ]
            })

        # Conclusion slide
        slides.append({
            "type": "conclusion",
            "title": "Next Steps",
            "content": [
                "Review identified improvement areas",
                "Follow personalized learning recommendations",
                "Track progress and reassess periodically"
            ]
        })

        return {
            "presentation_title": f"{cert_name} - Learning Plan",
            "slide_count": len(slides),
            "slides": slides,
            "generated_at": datetime.utcnow().isoformat(),
            "fallback_mode": True
        }

    async def get_presgen_job_status(self, presgen_job_id: str) -> Dict[str, Any]:
        """Get status of a PresGen job."""
        try:
            # Check cache first
            if presgen_job_id in self._job_cache:
                cached_job = self._job_cache[presgen_job_id]

                # For fallback jobs, return completed status
                if presgen_job_id.startswith("fallback_"):
                    return {
                        "success": True,
                        "presgen_job_id": presgen_job_id,
                        "status": "completed",
                        "workflow_id": cached_job["workflow_id"],
                        "created_at": cached_job["created_at"],
                        "fallback_mode": True
                    }

            # Query PresGen-Core for real jobs
            if await self._check_presgen_availability():
                return await self._query_presgen_status(presgen_job_id)
            else:
                return {
                    "success": False,
                    "error": "PresGen-Core unavailable for status check",
                    "presgen_job_id": presgen_job_id
                }

        except Exception as e:
            self.logger.error("Failed to get PresGen job status", extra={
                "presgen_job_id": presgen_job_id,
                "error": str(e)
            })
            return {
                "success": False,
                "error": str(e),
                "presgen_job_id": presgen_job_id
            }

    async def _query_presgen_status(self, presgen_job_id: str) -> Dict[str, Any]:
        """Query PresGen-Core for job status."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    f"{self.presgen_core_url}/api/v1/jobs/{presgen_job_id}/status"
                )

                if response.status_code == 200:
                    result = response.json()

                    # Update cache
                    if presgen_job_id in self._job_cache:
                        self._job_cache[presgen_job_id]["status"] = result.get("status")

                    return result
                else:
                    return {
                        "success": False,
                        "error": f"Status query failed: {response.status_code}",
                        "presgen_job_id": presgen_job_id
                    }

        except Exception as e:
            return {
                "success": False,
                "error": f"Status query exception: {str(e)}",
                "presgen_job_id": presgen_job_id
            }

    async def generate_learning_content_from_gaps(
        self,
        gap_analysis_results: Dict[str, Any],
        certification_profile: Dict[str, Any],
        content_format: str = "slides"
    ) -> Dict[str, Any]:
        """Generate targeted learning content based on gap analysis."""
        try:
            gaps = gap_analysis_results.get("gap_areas", [])
            cert_name = certification_profile.get("certification_name", "Certification")

            self.logger.info("Generating learning content from gaps", extra={
                "certification_name": cert_name,
                "gap_count": len(gaps),
                "content_format": content_format
            })

            learning_modules = []

            for i, gap in enumerate(gaps, 1):
                domain = gap.get("domain", f"Area {i}")
                difficulty = gap.get("difficulty_level", "intermediate")

                module = {
                    "module_id": f"module_{i}",
                    "title": f"Mastering {domain}",
                    "domain": domain,
                    "difficulty_level": difficulty,
                    "learning_objectives": [
                        f"Understand core concepts in {domain}",
                        f"Apply {domain} principles in practical scenarios",
                        f"Demonstrate proficiency in {domain} assessments"
                    ],
                    "content_outline": self._generate_content_outline(gap),
                    "estimated_study_time_hours": self._estimate_study_time(gap),
                    "recommended_resources": self._generate_resource_recommendations(gap, certification_profile)
                }

                learning_modules.append(module)

            learning_plan = {
                "certification_name": cert_name,
                "generated_at": datetime.utcnow().isoformat(),
                "total_modules": len(learning_modules),
                "estimated_total_hours": sum(m.get("estimated_study_time_hours", 0) for m in learning_modules),
                "difficulty_distribution": self._analyze_difficulty_distribution(learning_modules),
                "learning_modules": learning_modules,
                "study_sequence": self._recommend_study_sequence(learning_modules)
            }

            return {
                "success": True,
                "learning_plan": learning_plan,
                "content_format": content_format
            }

        except Exception as e:
            self.logger.error("Failed to generate learning content", extra={
                "error": str(e),
                "certification_name": certification_profile.get("certification_name", "Unknown")
            })
            return {
                "success": False,
                "error": f"Learning content generation failed: {str(e)}"
            }

    def _generate_content_outline(self, gap: Dict[str, Any]) -> List[str]:
        """Generate content outline for a specific gap area."""
        domain = gap.get("domain", "General")
        topics = gap.get("topics", [])

        outline = [
            f"Introduction to {domain}",
            f"Key Concepts and Terminology",
        ]

        # Add specific topics if available
        for topic in topics[:3]:  # Limit to top 3 topics
            outline.append(f"Deep Dive: {topic}")

        outline.extend([
            f"Best Practices in {domain}",
            f"Common Pitfalls and How to Avoid Them",
            f"Practical Examples and Case Studies",
            f"Assessment Preparation Tips"
        ])

        return outline

    def _estimate_study_time(self, gap: Dict[str, Any]) -> int:
        """Estimate study time in hours for a gap area."""
        difficulty = gap.get("difficulty_level", "intermediate")
        topic_count = len(gap.get("topics", []))

        base_hours = {
            "beginner": 8,
            "intermediate": 12,
            "advanced": 16,
            "expert": 20
        }.get(difficulty, 12)

        # Adjust based on topic count
        adjusted_hours = base_hours + (topic_count * 2)

        return min(adjusted_hours, 40)  # Cap at 40 hours per module

    def _generate_resource_recommendations(
        self,
        gap: Dict[str, Any],
        certification_profile: Dict[str, Any]
    ) -> List[Dict[str, str]]:
        """Generate resource recommendations for a gap area."""
        domain = gap.get("domain", "General")
        cert_name = certification_profile.get("certification_name", "")

        resources = [
            {
                "type": "official_documentation",
                "title": f"Official {cert_name} Documentation - {domain}",
                "description": f"Official documentation covering {domain} concepts",
                "priority": "high"
            },
            {
                "type": "practice_tests",
                "title": f"{domain} Practice Questions",
                "description": f"Targeted practice questions for {domain}",
                "priority": "high"
            },
            {
                "type": "video_tutorial",
                "title": f"{domain} Video Tutorial Series",
                "description": f"Comprehensive video tutorials on {domain}",
                "priority": "medium"
            },
            {
                "type": "hands_on_lab",
                "title": f"{domain} Practical Lab Exercises",
                "description": f"Hands-on exercises to practice {domain} skills",
                "priority": "high"
            }
        ]

        return resources

    def _analyze_difficulty_distribution(self, modules: List[Dict]) -> Dict[str, int]:
        """Analyze difficulty distribution across learning modules."""
        distribution = {"beginner": 0, "intermediate": 0, "advanced": 0, "expert": 0}

        for module in modules:
            difficulty = module.get("difficulty_level", "intermediate")
            if difficulty in distribution:
                distribution[difficulty] += 1

        return distribution

    def _recommend_study_sequence(self, modules: List[Dict]) -> List[str]:
        """Recommend optimal study sequence for learning modules."""
        # Sort by difficulty level (beginner first, expert last)
        difficulty_order = {"beginner": 1, "intermediate": 2, "advanced": 3, "expert": 4}

        sorted_modules = sorted(
            modules,
            key=lambda m: difficulty_order.get(m.get("difficulty_level", "intermediate"), 2)
        )

        return [module["module_id"] for module in sorted_modules]

    async def get_integration_statistics(self) -> Dict[str, Any]:
        """Get statistics about PresGen integration usage."""
        try:
            total_jobs = len(self._job_cache)
            fallback_jobs = len([job_id for job_id in self._job_cache.keys() if job_id.startswith("fallback_")])
            presgen_available = await self._check_presgen_availability()

            return {
                "success": True,
                "statistics": {
                    "total_presgen_jobs": total_jobs,
                    "fallback_jobs": fallback_jobs,
                    "presgen_core_jobs": total_jobs - fallback_jobs,
                    "presgen_core_available": presgen_available,
                    "presgen_core_url": self.presgen_core_url,
                    "fallback_rate": (fallback_jobs / total_jobs * 100) if total_jobs > 0 else 0
                }
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }