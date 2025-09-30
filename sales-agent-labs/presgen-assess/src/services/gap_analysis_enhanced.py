"""Enhanced Gap Analysis Service with Database Persistence.

Sprint 1 Deliverable: Gap Analysis with database storage, text summary generation,
and integration with existing GapAnalysisEngine.
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional
from uuid import UUID, uuid4
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.service.database import get_db_session as get_async_session
from src.models.workflow import WorkflowExecution
from src.models.gap_analysis import GapAnalysisResult, ContentOutline, RecommendedCourse
from src.services.gap_analysis import GapAnalysisEngine
from src.services.llm_service import LLMService
from src.common.structured_logger import StructuredLogger
from src.common.feature_flags import is_feature_enabled


class EnhancedGapAnalysisService:
    """Gap Analysis with database persistence and content outline generation.

    Sprint 1: Extends existing GapAnalysisEngine with database storage.
    """

    def __init__(self):
        """Initialize enhanced gap analysis service."""
        self.gap_engine = GapAnalysisEngine()
        self.llm_service = LLMService()
        self.logger = StructuredLogger("gap_analysis")

    async def analyze_and_persist(
        self,
        workflow_id: UUID,
        assessment_responses: List[Dict[str, Any]],
        certification_profile: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Perform gap analysis and persist results to database.

        Sprint 1: Main entry point for Gap Analysis with database persistence.

        Args:
            workflow_id: UUID of workflow execution
            assessment_responses: List of assessment responses
            certification_profile: Certification profile data

        Returns:
            Dict with gap analysis results and database IDs
        """
        start_time = asyncio.get_event_loop().time()

        # Log start
        self.logger.log_gap_analysis_start(
            workflow_id=str(workflow_id),
            question_count=len(assessment_responses),
            certification_profile_id=str(certification_profile.get("id", "unknown"))
        )

        try:
            # Step 1: Perform gap analysis using existing engine
            assessment_results = self._format_assessment_results(
                assessment_responses,
                certification_profile
            )

            gap_analysis = await self.gap_engine.analyze_assessment_results(
                assessment_results=assessment_results,
                certification_profile=certification_profile,
                confidence_ratings=self._extract_confidence_ratings(assessment_responses)
            )

            # Step 2: Generate plain language text summary
            text_summary = await self._generate_text_summary(
                gap_analysis,
                certification_profile
            )

            # Step 3: Calculate severity scores
            severity_scores = self._calculate_severity_scores(gap_analysis)

            # Step 4: Extract skill gaps
            skill_gaps = self._extract_skill_gaps(gap_analysis)

            # Step 5: Calculate performance by domain
            performance_by_domain = gap_analysis.get("domain_scores", {})

            # Step 6: Prepare charts data
            charts_data = self._prepare_charts_data(
                gap_analysis,
                skill_gaps,
                performance_by_domain
            )

            # Step 7: Persist to database
            gap_analysis_id = await self._persist_gap_analysis(
                workflow_id=workflow_id,
                overall_score=gap_analysis.get("overall_readiness_score", 0.0),
                total_questions=len(assessment_responses),
                correct_answers=self._count_correct_answers(assessment_responses),
                incorrect_answers=self._count_incorrect_answers(assessment_responses),
                skill_gaps=skill_gaps,
                performance_by_domain=performance_by_domain,
                severity_scores=severity_scores,
                text_summary=text_summary,
                charts_data=charts_data,
                certification_profile_id=UUID(str(certification_profile.get("id")))
            )

            processing_time_ms = (asyncio.get_event_loop().time() - start_time) * 1000

            # Log completion
            self.logger.log_gap_analysis_complete(
                workflow_id=str(workflow_id),
                overall_score=gap_analysis.get("overall_readiness_score", 0.0),
                skill_gaps_count=len(skill_gaps),
                processing_time_ms=processing_time_ms
            )

            return {
                "success": True,
                "gap_analysis_id": str(gap_analysis_id),
                "workflow_id": str(workflow_id),
                "overall_score": gap_analysis.get("overall_readiness_score", 0.0),
                "skill_gaps_count": len(skill_gaps),
                "text_summary": text_summary,
                "processing_time_ms": processing_time_ms
            }

        except Exception as e:
            self.logger.log_workflow_error(
                workflow_id=str(workflow_id),
                error=str(e),
                step="gap_analysis_persistence",
                traceback=None
            )
            raise

    async def generate_content_outlines(
        self,
        gap_analysis_id: UUID,
        workflow_id: UUID,
        skill_gaps: List[Dict[str, Any]],
        certification_profile: Dict[str, Any]
    ) -> List[UUID]:
        """Generate content outlines for skill gaps via RAG retrieval.

        Sprint 1: Content outline generation (placeholder for full RAG in Sprint 2).

        Args:
            gap_analysis_id: Gap analysis result ID
            workflow_id: Workflow execution ID
            skill_gaps: List of identified skill gaps
            certification_profile: Certification profile data

        Returns:
            List of content outline IDs
        """
        content_outline_ids = []

        for skill_gap in skill_gaps:
            # Placeholder: Simple content mapping (full RAG retrieval in Sprint 2)
            content_items = self._generate_placeholder_content_items(
                skill_gap,
                certification_profile
            )

            content_outline_id = await self._persist_content_outline(
                gap_analysis_id=gap_analysis_id,
                workflow_id=workflow_id,
                skill_id=skill_gap.get("skill_id"),
                skill_name=skill_gap.get("skill_name"),
                exam_domain=skill_gap.get("exam_domain"),
                exam_guide_section=skill_gap.get("exam_subsection", "General"),
                content_items=content_items,
                rag_retrieval_score=0.75  # Placeholder score
            )

            content_outline_ids.append(content_outline_id)

        return content_outline_ids

    async def generate_course_recommendations(
        self,
        gap_analysis_id: UUID,
        workflow_id: UUID,
        skill_gaps: List[Dict[str, Any]],
        certification_profile: Dict[str, Any]
    ) -> List[UUID]:
        """Generate course recommendations for skill gaps.

        Sprint 1: Course recommendation generation.

        Args:
            gap_analysis_id: Gap analysis result ID
            workflow_id: Workflow execution ID
            skill_gaps: List of identified skill gaps
            certification_profile: Certification profile data

        Returns:
            List of recommended course IDs
        """
        course_ids = []

        for skill_gap in skill_gaps:
            course_data = self._generate_course_recommendation(
                skill_gap,
                certification_profile
            )

            course_id = await self._persist_recommended_course(
                gap_analysis_id=gap_analysis_id,
                workflow_id=workflow_id,
                skill_id=skill_gap.get("skill_id"),
                skill_name=skill_gap.get("skill_name"),
                exam_domain=skill_gap.get("exam_domain"),
                exam_subsection=skill_gap.get("exam_subsection"),
                course_data=course_data,
                priority=skill_gap.get("severity", 5)
            )

            course_ids.append(course_id)

        return course_ids

    # Private methods

    def _format_assessment_results(
        self,
        assessment_responses: List[Dict[str, Any]],
        certification_profile: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Format assessment responses for GapAnalysisEngine."""
        # Calculate overall score
        correct_count = sum(1 for r in assessment_responses if r.get("is_correct", False))
        overall_score = (correct_count / len(assessment_responses)) * 100 if assessment_responses else 0

        # Calculate domain scores
        domain_scores = {}
        domain_questions = {}

        for response in assessment_responses:
            domain = response.get("domain", "General")
            if domain not in domain_questions:
                domain_questions[domain] = {"correct": 0, "total": 0}

            domain_questions[domain]["total"] += 1
            if response.get("is_correct", False):
                domain_questions[domain]["correct"] += 1

        for domain, counts in domain_questions.items():
            domain_scores[domain] = (counts["correct"] / counts["total"]) * 100 if counts["total"] > 0 else 0

        return {
            "assessment_id": str(uuid4()),
            "user_id": "workflow_user",
            "certification_profile_id": str(certification_profile.get("id")),
            "score": overall_score,
            "domain_scores": domain_scores,
            "questions": assessment_responses,
            "answers": {r.get("question_id"): r.get("user_answer") for r in assessment_responses}
        }

    def _extract_confidence_ratings(
        self,
        assessment_responses: List[Dict[str, Any]]
    ) -> Dict[str, float]:
        """Extract confidence ratings from responses."""
        return {
            r.get("question_id"): r.get("confidence", 3.0)
            for r in assessment_responses
            if "question_id" in r
        }

    async def _generate_text_summary(
        self,
        gap_analysis: Dict[str, Any],
        certification_profile: Dict[str, Any]
    ) -> str:
        """Generate plain language text summary of gap analysis results.

        Sprint 1: Text summary generation using LLM.
        """
        start_time = asyncio.get_event_loop().time()

        overall_score = gap_analysis.get("overall_readiness_score", 0)
        skill_assessments = gap_analysis.get("skill_assessments", [])
        domain_gaps = gap_analysis.get("identified_gaps", [])

        # Build prompt for LLM
        prompt = f"""Generate a plain language summary of this assessment gap analysis:

Overall Score: {overall_score:.1f}%
Certification: {certification_profile.get('name', 'Unknown')}

Skill Assessments:
{self._format_skill_assessments_for_prompt(skill_assessments)}

Domain Gaps:
{self._format_domain_gaps_for_prompt(domain_gaps)}

Generate a concise, student-friendly summary (300-500 words) that includes:
1. Overall performance
2. Strongest areas (3-5 sentences)
3. Areas needing improvement (3-5 sentences)
4. Critical skill gaps with severity and question counts
5. Recommended next steps

Use encouraging, actionable language. Avoid technical jargon."""

        try:
            summary = await self.llm_service.generate_text(
                prompt=prompt,
                max_tokens=600,
                temperature=0.7
            )

            generation_time_ms = (asyncio.get_event_loop().time() - start_time) * 1000
            self.logger.log_text_summary_generation(
                workflow_id="unknown",  # Will be set by caller
                summary_length=len(summary),
                generation_time_ms=generation_time_ms
            )

            return summary

        except Exception as e:
            logging.error(f"Text summary generation failed: {e}")
            # Fallback to template-based summary
            return self._generate_template_summary(gap_analysis, certification_profile)

    def _generate_template_summary(
        self,
        gap_analysis: Dict[str, Any],
        certification_profile: Dict[str, Any]
    ) -> str:
        """Generate template-based summary as fallback."""
        overall_score = gap_analysis.get("overall_readiness_score", 0)
        skill_assessments = gap_analysis.get("skill_assessments", [])
        domain_gaps = gap_analysis.get("identified_gaps", [])

        # Find strongest and weakest areas
        sorted_assessments = sorted(
            skill_assessments,
            key=lambda x: x.get("proficiency_score", 0),
            reverse=True
        )
        strongest = sorted_assessments[:2] if len(sorted_assessments) >= 2 else sorted_assessments
        weakest = sorted_assessments[-2:] if len(sorted_assessments) >= 2 else []

        summary = f"""You scored {overall_score:.1f}% overall on this {certification_profile.get('name', 'certification')} assessment.

Your strongest areas are:
"""

        for skill in strongest:
            score = skill.get("proficiency_score", 0)
            name = skill.get("skill_name", "Unknown")
            summary += f"- {name} ({score:.1f}%) - {'Well above' if score >= 80 else 'Above'} passing threshold\n"

        summary += "\nAreas needing improvement:\n"

        for skill in weakest:
            score = skill.get("proficiency_score", 0)
            name = skill.get("skill_name", "Unknown")
            summary += f"- {name} ({score:.1f}%) - Below recommended proficiency\n"

        if domain_gaps:
            summary += f"\nCritical skill gaps identified ({len(domain_gaps)} total):\n"
            for i, gap in enumerate(domain_gaps[:3], 1):
                summary += f"{i}. {gap.get('domain_name', 'Unknown')} - {gap.get('gap_description', 'Needs review')}\n"

        summary += "\nRecommended next steps:\n"
        summary += "- Focus study time on areas with lowest scores\n"
        summary += "- Review exam guide sections for identified gaps\n"
        summary += "- Practice with targeted exercises\n"

        return summary

    def _format_skill_assessments_for_prompt(
        self,
        skill_assessments: List[Dict[str, Any]]
    ) -> str:
        """Format skill assessments for LLM prompt."""
        formatted = []
        for skill in skill_assessments[:10]:  # Limit to top 10
            name = skill.get("skill_name", "Unknown")
            score = skill.get("proficiency_score", 0)
            formatted.append(f"- {name}: {score:.1f}%")
        return "\n".join(formatted)

    def _format_domain_gaps_for_prompt(
        self,
        domain_gaps: List[Dict[str, Any]]
    ) -> str:
        """Format domain gaps for LLM prompt."""
        formatted = []
        for gap in domain_gaps[:5]:  # Limit to top 5
            domain = gap.get("domain_name", "Unknown")
            description = gap.get("gap_description", "Needs review")
            formatted.append(f"- {domain}: {description}")
        return "\n".join(formatted)

    def _calculate_severity_scores(
        self,
        gap_analysis: Dict[str, Any]
    ) -> Dict[str, int]:
        """Calculate severity scores (0-10) for each skill gap."""
        severity_scores = {}
        skill_assessments = gap_analysis.get("skill_assessments", [])

        for skill in skill_assessments:
            skill_id = skill.get("skill_name", "unknown").lower().replace(" ", "_")
            score = skill.get("proficiency_score", 0)

            # Calculate severity: lower score = higher severity
            if score >= 90:
                severity = 1
            elif score >= 80:
                severity = 3
            elif score >= 70:
                severity = 5
            elif score >= 60:
                severity = 7
            else:
                severity = 9

            severity_scores[skill_id] = severity

        return severity_scores

    def _extract_skill_gaps(
        self,
        gap_analysis: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Extract skill gaps from gap analysis results."""
        skill_gaps = []
        skill_assessments = gap_analysis.get("skill_assessments", [])

        for skill in skill_assessments:
            score = skill.get("proficiency_score", 0)

            # Only include gaps (score < 80%)
            if score < 80:
                skill_id = skill.get("skill_name", "unknown").lower().replace(" ", "_")
                severity = 9 - int(score / 10)  # 0-90% maps to severity 9-0

                skill_gaps.append({
                    "skill_id": skill_id,
                    "skill_name": skill.get("skill_name", "Unknown"),
                    "exam_domain": skill.get("domain", "General"),
                    "exam_subsection": skill.get("subsection"),
                    "severity": min(max(severity, 0), 10),
                    "confidence_delta": skill.get("confidence_calibration", "unknown"),
                    "question_ids": []
                })

        return skill_gaps

    def _count_correct_answers(
        self,
        assessment_responses: List[Dict[str, Any]]
    ) -> int:
        """Count correct answers."""
        return sum(1 for r in assessment_responses if r.get("is_correct", False))

    def _count_incorrect_answers(
        self,
        assessment_responses: List[Dict[str, Any]]
    ) -> int:
        """Count incorrect answers."""
        return sum(1 for r in assessment_responses if not r.get("is_correct", False))

    def _prepare_charts_data(
        self,
        gap_analysis: Dict[str, Any],
        skill_gaps: List[Dict[str, Any]],
        performance_by_domain: Dict[str, float]
    ) -> Dict[str, Any]:
        """Prepare data for dashboard charts."""
        return {
            "bar_chart": {
                "type": "bar",
                "data": performance_by_domain,
                "title": "Performance by Domain"
            },
            "radar_chart": {
                "type": "radar",
                "data": {sg["skill_name"]: 100 - (sg["severity"] * 10) for sg in skill_gaps[:8]},
                "title": "Skill Coverage"
            },
            "scatter_plot": {
                "type": "scatter",
                "data": [],  # Will be populated from responses
                "title": "Confidence vs Performance"
            }
        }

    def _generate_placeholder_content_items(
        self,
        skill_gap: Dict[str, Any],
        certification_profile: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Generate placeholder content items (full RAG in Sprint 2)."""
        skill_name = skill_gap.get("skill_name", "Unknown")
        domain = skill_gap.get("exam_domain", "General")

        return [
            {
                "topic": f"{skill_name} Fundamentals",
                "source": f"{certification_profile.get('name', 'Certification')} Study Guide",
                "page_ref": "Chapter TBD",
                "summary": f"Core concepts and principles of {skill_name} in {domain}."
            },
            {
                "topic": f"{skill_name} Best Practices",
                "source": "Official Documentation",
                "page_ref": "Section TBD",
                "summary": f"Industry best practices and common patterns for {skill_name}."
            }
        ]

    def _generate_course_recommendation(
        self,
        skill_gap: Dict[str, Any],
        certification_profile: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate course recommendation for skill gap."""
        skill_name = skill_gap.get("skill_name", "Unknown")
        severity = skill_gap.get("severity", 5)

        # Determine difficulty level based on severity
        if severity >= 8:
            difficulty = "beginner"
            duration = 60
        elif severity >= 5:
            difficulty = "intermediate"
            duration = 45
        else:
            difficulty = "advanced"
            duration = 30

        return {
            "course_title": f"Mastering {skill_name}",
            "course_description": f"Comprehensive course covering {skill_name} concepts, best practices, and exam-relevant scenarios.",
            "estimated_duration_minutes": duration,
            "difficulty_level": difficulty,
            "learning_objectives": [
                f"Understand core {skill_name} principles",
                f"Apply {skill_name} in practical scenarios",
                f"Master exam topics related to {skill_name}"
            ],
            "content_outline": {
                "sections": [
                    {"title": "Introduction", "duration_minutes": int(duration * 0.2)},
                    {"title": "Core Concepts", "duration_minutes": int(duration * 0.4)},
                    {"title": "Practical Applications", "duration_minutes": int(duration * 0.3)},
                    {"title": "Review and Practice", "duration_minutes": int(duration * 0.1)}
                ]
            }
        }

    # Database persistence methods

    async def _persist_gap_analysis(
        self,
        workflow_id: UUID,
        overall_score: float,
        total_questions: int,
        correct_answers: int,
        incorrect_answers: int,
        skill_gaps: List[Dict[str, Any]],
        performance_by_domain: Dict[str, float],
        severity_scores: Dict[str, int],
        text_summary: str,
        charts_data: Dict[str, Any],
        certification_profile_id: UUID
    ) -> UUID:
        """Persist gap analysis results to database."""
        async with get_async_session() as session:
            gap_result = GapAnalysisResult(
                id=uuid4(),
                workflow_id=workflow_id,
                overall_score=overall_score,
                total_questions=total_questions,
                correct_answers=correct_answers,
                incorrect_answers=incorrect_answers,
                skill_gaps=skill_gaps,
                performance_by_domain=performance_by_domain,
                severity_scores=severity_scores,
                text_summary=text_summary,
                charts_data=charts_data,
                certification_profile_id=certification_profile_id
            )

            session.add(gap_result)
            await session.commit()
            await session.refresh(gap_result)

            # Log persistence
            self.logger.log_gap_analysis_persistence(
                workflow_id=str(workflow_id),
                gap_analysis_id=str(gap_result.id),
                content_outlines_count=0,  # Will be set later
                recommended_courses_count=0  # Will be set later
            )

            return gap_result.id

    async def _persist_content_outline(
        self,
        gap_analysis_id: UUID,
        workflow_id: UUID,
        skill_id: str,
        skill_name: str,
        exam_domain: str,
        exam_guide_section: str,
        content_items: List[Dict[str, Any]],
        rag_retrieval_score: float
    ) -> UUID:
        """Persist content outline to database."""
        async with get_async_session() as session:
            content_outline = ContentOutline(
                id=uuid4(),
                gap_analysis_id=gap_analysis_id,
                workflow_id=workflow_id,
                skill_id=skill_id,
                skill_name=skill_name,
                exam_domain=exam_domain,
                exam_guide_section=exam_guide_section,
                content_items=content_items,
                rag_retrieval_score=rag_retrieval_score
            )

            session.add(content_outline)
            await session.commit()
            await session.refresh(content_outline)

            return content_outline.id

    async def _persist_recommended_course(
        self,
        gap_analysis_id: UUID,
        workflow_id: UUID,
        skill_id: str,
        skill_name: str,
        exam_domain: str,
        exam_subsection: Optional[str],
        course_data: Dict[str, Any],
        priority: int
    ) -> UUID:
        """Persist recommended course to database."""
        async with get_async_session() as session:
            course = RecommendedCourse(
                id=uuid4(),
                gap_analysis_id=gap_analysis_id,
                workflow_id=workflow_id,
                skill_id=skill_id,
                skill_name=skill_name,
                exam_domain=exam_domain,
                exam_subsection=exam_subsection,
                course_title=course_data["course_title"],
                course_description=course_data["course_description"],
                estimated_duration_minutes=course_data["estimated_duration_minutes"],
                difficulty_level=course_data["difficulty_level"],
                learning_objectives=course_data["learning_objectives"],
                content_outline=course_data["content_outline"],
                priority=priority
            )

            session.add(course)
            await session.commit()
            await session.refresh(course)

            return course.id