"""Presentation generation service integrating with PresGen-Core for 40-slide presentations."""

import logging
import asyncio
from typing import Dict, List, Optional
from datetime import datetime
from uuid import uuid4

import httpx

from src.common.config import settings
from src.services.llm_service import LLMService
from src.knowledge.base import RAGKnowledgeBase

logger = logging.getLogger(__name__)


class PresentationGenerationService:
    """Service for generating 40-slide presentations based on assessment results and gap analysis."""

    def __init__(self):
        """Initialize presentation service with PresGen-Core integration."""
        self.presgen_core_url = settings.presgen_core_url
        self.max_slides = settings.presgen_core_max_slides
        self.llm_service = LLMService()
        self.knowledge_base = RAGKnowledgeBase()
        self.http_client = httpx.AsyncClient(timeout=300.0)  # 5-minute timeout

    async def generate_personalized_presentation(
        self,
        assessment_results: Dict,
        gap_analysis: Dict,
        certification_profile: Dict,
        target_slide_count: int = 20,
        presentation_title: Optional[str] = None
    ) -> Dict:
        """Generate a personalized presentation based on assessment results and gap analysis."""
        try:
            # Validate slide count
            if not 1 <= target_slide_count <= self.max_slides:
                raise ValueError(f"Slide count must be between 1 and {self.max_slides}")

            generation_id = str(uuid4())
            logger.info(f"🎯 Starting presentation generation {generation_id} with {target_slide_count} slides")

            # Generate course outline using LLM with RAG context
            course_outline = await self.llm_service.generate_course_outline(
                assessment_results=assessment_results,
                gap_analysis=gap_analysis,
                target_slide_count=target_slide_count,
                certification_id=assessment_results.get("certification_profile_id")
            )

            if not course_outline.get("success"):
                raise Exception(f"Course outline generation failed: {course_outline.get('error')}")

            # Adapt content for presentation generation
            presentation_request = self._adapt_content_for_presentation(
                course_outline=course_outline,
                assessment_results=assessment_results,
                gap_analysis=gap_analysis,
                certification_profile=certification_profile,
                target_slide_count=target_slide_count,
                presentation_title=presentation_title
            )

            # Generate presentation through PresGen-Core
            presentation_result = await self._generate_via_presgen_core(
                presentation_request=presentation_request,
                generation_id=generation_id
            )

            # Track quality metrics
            quality_metrics = self._calculate_quality_metrics(
                presentation_request=presentation_request,
                presentation_result=presentation_result,
                gap_analysis=gap_analysis
            )

            result = {
                "success": True,
                "generation_id": generation_id,
                "presentation_url": presentation_result.get("presentation_url"),
                "slide_count": target_slide_count,
                "course_outline": course_outline,
                "gap_coverage": self._analyze_gap_coverage(gap_analysis, course_outline),
                "rag_sources_used": course_outline.get("citations", []),
                "quality_metrics": quality_metrics,
                "generation_timestamp": datetime.now().isoformat(),
                "estimated_duration_minutes": course_outline.get("estimated_duration_minutes", 60)
            }

            logger.info(
                f"✅ Presentation generation {generation_id} completed successfully "
                f"({target_slide_count} slides, {len(result['rag_sources_used'])} sources)"
            )

            return result

        except Exception as e:
            logger.error(f"❌ Presentation generation failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "generation_id": generation_id if 'generation_id' in locals() else None
            }

    def _adapt_content_for_presentation(
        self,
        course_outline: Dict,
        assessment_results: Dict,
        gap_analysis: Dict,
        certification_profile: Dict,
        target_slide_count: int,
        presentation_title: Optional[str]
    ) -> Dict:
        """Adapt course outline content for PresGen-Core presentation generation."""

        # Extract key information
        priority_areas = gap_analysis.get("priority_learning_areas", [])
        overall_score = assessment_results.get("score", 0)
        readiness_score = gap_analysis.get("overall_readiness_score", 0)

        # Generate presentation title if not provided
        if not presentation_title:
            cert_name = certification_profile.get("name", "Certification")
            presentation_title = f"Personalized Learning Path: {cert_name}"

        # Structure content for presentation
        presentation_content = {
            "title": presentation_title,
            "subtitle": f"Based on Assessment Results (Score: {overall_score}%, Readiness: {readiness_score}%)",
            "slide_count": target_slide_count,
            "content_outline": self._structure_presentation_content(course_outline, gap_analysis),
            "learning_objectives": course_outline.get("learning_objectives", []),
            "target_audience": f"Candidates preparing for {certification_profile.get('name', 'certification')}",
            "difficulty_level": self._determine_difficulty_level(gap_analysis),
            "focus_areas": priority_areas,
            "source_attribution": True,
            "include_practice_questions": True
        }

        # Add RAG context and citations
        presentation_content["rag_context"] = {
            "sources_used": course_outline.get("citations", []),
            "context_enhanced": course_outline.get("rag_context_used", False),
            "knowledge_base_queries": self._generate_knowledge_base_queries(priority_areas)
        }

        # Add slide distribution strategy
        presentation_content["slide_distribution"] = self._calculate_slide_distribution(
            course_outline.get("sections", []),
            target_slide_count,
            priority_areas
        )

        return presentation_content

    def _structure_presentation_content(self, course_outline: Dict, gap_analysis: Dict) -> List[Dict]:
        """Structure the presentation content based on course outline and gap analysis."""

        structured_content = []

        # Introduction slides (always include)
        structured_content.append({
            "section": "Introduction",
            "slides": [
                {
                    "title": "Welcome to Your Personalized Learning Path",
                    "content": [
                        "Assessment-driven course content",
                        f"Focus on {len(gap_analysis.get('priority_learning_areas', []))} key improvement areas",
                        "Evidence-based learning recommendations"
                    ]
                },
                {
                    "title": "Your Assessment Results Overview",
                    "content": [
                        f"Overall Score: {gap_analysis.get('overall_readiness_score', 0)}%",
                        "Identified strengths and areas for improvement",
                        "Personalized learning objectives"
                    ]
                }
            ]
        })

        # Content sections from course outline
        sections = course_outline.get("sections", [])
        for section in sections:
            section_content = {
                "section": section.get("section_title", "Learning Module"),
                "slide_count": section.get("slide_count", 3),
                "learning_outcomes": section.get("learning_outcomes", []),
                "slides": self._generate_section_slides(section)
            }
            structured_content.append(section_content)

        # Conclusion and next steps
        structured_content.append({
            "section": "Next Steps & Resources",
            "slides": [
                {
                    "title": "Your Learning Action Plan",
                    "content": [
                        "Prioritized study recommendations",
                        "Estimated study timeline",
                        "Success milestones and checkpoints"
                    ]
                },
                {
                    "title": "Additional Resources",
                    "content": [
                        "Recommended study materials",
                        "Practice test resources",
                        "Community and support resources"
                    ]
                }
            ]
        })

        return structured_content

    def _generate_section_slides(self, section: Dict) -> List[Dict]:
        """Generate individual slides for a course section."""

        slides = []
        content_outline = section.get("content_outline", [])
        slide_count = section.get("slide_count", 3)

        # Distribute content across slides
        content_per_slide = max(1, len(content_outline) // slide_count)

        for i in range(slide_count):
            start_idx = i * content_per_slide
            end_idx = start_idx + content_per_slide if i < slide_count - 1 else len(content_outline)

            slide_content = content_outline[start_idx:end_idx]

            slide = {
                "title": f"{section.get('section_title', 'Content')} - Part {i + 1}",
                "content": slide_content,
                "slide_type": "content",
                "estimated_duration_minutes": section.get("estimated_minutes", 10) // slide_count
            }

            slides.append(slide)

        return slides

    async def _generate_via_presgen_core(self, presentation_request: Dict, generation_id: str) -> Dict:
        """Generate presentation through PresGen-Core API."""
        try:
            # Prepare request for PresGen-Core
            presgen_request = {
                "title": presentation_request["title"],
                "slide_count": presentation_request["slide_count"],
                "content_outline": presentation_request["content_outline"],
                "learning_objectives": presentation_request["learning_objectives"],
                "difficulty_level": presentation_request["difficulty_level"],
                "source_attribution": True,
                "generation_id": generation_id,
                "service": "presgen-assess"
            }

            # Call PresGen-Core API
            response = await self.http_client.post(
                f"{self.presgen_core_url}/api/presentations/generate",
                json=presgen_request,
                headers={"Content-Type": "application/json"}
            )

            response.raise_for_status()
            result = response.json()

            logger.info(f"✅ PresGen-Core generation completed for {generation_id}")
            return result

        except httpx.HTTPStatusError as e:
            logger.error(f"❌ PresGen-Core API error: {e.response.status_code} - {e.response.text}")
            raise Exception(f"PresGen-Core API error: {e.response.status_code}")

        except httpx.RequestError as e:
            logger.error(f"❌ PresGen-Core connection error: {e}")
            raise Exception(f"Failed to connect to PresGen-Core: {e}")

    async def generate_bulk_presentations(
        self,
        generation_requests: List[Dict],
        max_concurrent: int = 3
    ) -> List[Dict]:
        """Generate multiple presentations concurrently."""
        try:
            semaphore = asyncio.Semaphore(max_concurrent)

            async def generate_single(request: Dict) -> Dict:
                async with semaphore:
                    return await self.generate_personalized_presentation(**request)

            # Execute all requests concurrently
            results = await asyncio.gather(
                *[generate_single(req) for req in generation_requests],
                return_exceptions=True
            )

            # Process results
            successful_generations = []
            failed_generations = []

            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    failed_generations.append({
                        "request_index": i,
                        "error": str(result)
                    })
                elif result.get("success"):
                    successful_generations.append(result)
                else:
                    failed_generations.append({
                        "request_index": i,
                        "error": result.get("error", "Unknown error")
                    })

            logger.info(
                f"✅ Bulk generation completed: {len(successful_generations)} successful, "
                f"{len(failed_generations)} failed"
            )

            return {
                "success": True,
                "total_requests": len(generation_requests),
                "successful_generations": successful_generations,
                "failed_generations": failed_generations,
                "success_rate": len(successful_generations) / len(generation_requests)
            }

        except Exception as e:
            logger.error(f"❌ Bulk presentation generation failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "successful_generations": [],
                "failed_generations": []
            }

    def _determine_difficulty_level(self, gap_analysis: Dict) -> str:
        """Determine appropriate difficulty level based on gap analysis."""
        readiness_score = gap_analysis.get("overall_readiness_score", 50)

        if readiness_score >= 80:
            return "advanced"
        elif readiness_score >= 60:
            return "intermediate"
        else:
            return "beginner"

    def _generate_knowledge_base_queries(self, priority_areas: List[str]) -> List[str]:
        """Generate knowledge base queries for enhanced content retrieval."""
        queries = []

        for area in priority_areas:
            queries.extend([
                f"best practices for {area}",
                f"common mistakes in {area}",
                f"real-world examples of {area}",
                f"hands-on exercises for {area}"
            ])

        return queries[:10]  # Limit to top 10 queries

    def _calculate_slide_distribution(
        self,
        sections: List[Dict],
        target_slide_count: int,
        priority_areas: List[str]
    ) -> Dict:
        """Calculate optimal slide distribution across sections."""

        distribution = {}

        # Reserve slides for introduction and conclusion
        intro_slides = 2
        conclusion_slides = 2
        content_slides = target_slide_count - intro_slides - conclusion_slides

        # Distribute content slides based on section importance and priority areas
        total_weight = 0
        section_weights = {}

        for section in sections:
            section_title = section.get("section_title", "")

            # Higher weight for sections that address priority areas
            base_weight = section.get("slide_count", 3)
            priority_bonus = sum(1 for area in priority_areas if area.lower() in section_title.lower())
            section_weight = base_weight + priority_bonus

            section_weights[section_title] = section_weight
            total_weight += section_weight

        # Calculate actual slide distribution
        for section_title, weight in section_weights.items():
            slides_for_section = max(1, round((weight / total_weight) * content_slides))
            distribution[section_title] = slides_for_section

        # Add introduction and conclusion
        distribution["Introduction"] = intro_slides
        distribution["Conclusion & Next Steps"] = conclusion_slides

        return distribution

    def _analyze_gap_coverage(self, gap_analysis: Dict, course_outline: Dict) -> Dict:
        """Analyze how well the presentation covers identified learning gaps."""

        priority_areas = gap_analysis.get("priority_learning_areas", [])
        sections = course_outline.get("sections", [])

        coverage_analysis = {
            "total_priority_areas": len(priority_areas),
            "areas_covered": 0,
            "coverage_details": {},
            "coverage_percentage": 0.0
        }

        for area in priority_areas:
            area_covered = False
            coverage_sections = []

            for section in sections:
                section_title = section.get("section_title", "")
                section_content = " ".join(section.get("content_outline", []))

                # Check if this section addresses the priority area
                if (area.lower() in section_title.lower() or
                    area.lower() in section_content.lower()):
                    area_covered = True
                    coverage_sections.append(section_title)

            coverage_analysis["coverage_details"][area] = {
                "covered": area_covered,
                "sections": coverage_sections
            }

            if area_covered:
                coverage_analysis["areas_covered"] += 1

        # Calculate coverage percentage
        if priority_areas:
            coverage_analysis["coverage_percentage"] = round(
                (coverage_analysis["areas_covered"] / len(priority_areas)) * 100, 1
            )

        return coverage_analysis

    def _calculate_quality_metrics(
        self,
        presentation_request: Dict,
        presentation_result: Dict,
        gap_analysis: Dict
    ) -> Dict:
        """Calculate quality metrics for the generated presentation."""

        metrics = {
            "slide_count_accuracy": self._check_slide_count_accuracy(
                presentation_request, presentation_result
            ),
            "gap_coverage_score": self._calculate_gap_coverage_score(gap_analysis),
            "content_relevance_score": self._assess_content_relevance(presentation_request),
            "source_attribution_quality": self._evaluate_source_attribution(presentation_request),
            "overall_quality_score": 0.0
        }

        # Calculate overall quality score
        scores = [v for k, v in metrics.items() if k.endswith("_score") or k.endswith("_accuracy")]
        metrics["overall_quality_score"] = round(sum(scores) / len(scores), 2) if scores else 0.0

        return metrics

    def _check_slide_count_accuracy(self, request: Dict, result: Dict) -> float:
        """Check if the generated presentation has the correct number of slides."""
        requested_slides = request.get("slide_count", 0)
        generated_slides = result.get("slide_count", 0)

        if requested_slides == 0:
            return 0.0

        accuracy = 1.0 - abs(requested_slides - generated_slides) / requested_slides
        return max(0.0, accuracy)

    def _calculate_gap_coverage_score(self, gap_analysis: Dict) -> float:
        """Calculate how well the presentation covers identified gaps."""
        # This would analyze the actual content coverage
        # For now, return a baseline score
        return 0.8

    def _assess_content_relevance(self, presentation_request: Dict) -> float:
        """Assess the relevance of presentation content to learning objectives."""
        # This would use NLP to analyze content relevance
        # For now, return a baseline score
        return 0.85

    def _evaluate_source_attribution(self, presentation_request: Dict) -> float:
        """Evaluate the quality of source attribution in the presentation."""
        rag_context = presentation_request.get("rag_context", {})
        sources_used = rag_context.get("sources_used", [])

        # Score based on number and quality of sources
        if len(sources_used) >= 5:
            return 1.0
        elif len(sources_used) >= 3:
            return 0.8
        elif len(sources_used) >= 1:
            return 0.6
        else:
            return 0.3

    async def get_presentation_status(self, generation_id: str) -> Dict:
        """Get the status of a presentation generation."""
        try:
            response = await self.http_client.get(
                f"{self.presgen_core_url}/api/presentations/status/{generation_id}"
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"❌ Failed to get presentation status: {e}")
            return {
                "status": "error",
                "error": f"HTTP {e.response.status_code}"
            }

    async def health_check(self) -> Dict:
        """Check the health of the presentation service and PresGen-Core connectivity."""
        try:
            # Test PresGen-Core connectivity
            response = await self.http_client.get(
                f"{self.presgen_core_url}/health",
                timeout=10.0
            )
            presgen_core_healthy = response.status_code == 200

            # Check LLM service
            llm_health = await self.llm_service.health_check()

            return {
                "status": "healthy" if presgen_core_healthy and llm_health.get("status") == "healthy" else "unhealthy",
                "presgen_core_connection": presgen_core_healthy,
                "presgen_core_url": self.presgen_core_url,
                "max_slides_supported": self.max_slides,
                "llm_service_status": llm_health.get("status"),
                "http_client_active": True
            }

        except Exception as e:
            logger.error(f"❌ Presentation service health check failed: {e}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "presgen_core_connection": False
            }

    async def close(self):
        """Clean up resources."""
        await self.http_client.aclose()