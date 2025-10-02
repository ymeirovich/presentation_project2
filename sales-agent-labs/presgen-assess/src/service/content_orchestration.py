"""
Content Orchestration Service for Sprint 3

Orchestrates content preparation for per-skill presentation generation.
Each service call prepares content for ONE skill gap (not all skills).
"""

import logging
from typing import Optional, Dict, Any
from uuid import UUID
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from src.schemas.presentation import PresentationContentSpec, TemplateType
from src.models.workflow import WorkflowExecution
from src.models.gap_analysis import GapAnalysisResult, ContentOutline
from src.models.gaps import RecommendedCourse

logger = logging.getLogger(__name__)


class ContentOrchestrationService:
    """
    Orchestrates content preparation for presentation generation.

    Sprint 3: Prepares content for ONE skill at a time (per-skill approach).
    """

    def __init__(self, db_session: AsyncSession):
        self.db = db_session

    async def prepare_presentation_content(
        self,
        workflow_id: UUID,
        course_id: UUID,
        custom_title: Optional[str] = None
    ) -> PresentationContentSpec:
        """
        Prepare content specification for a single skill presentation.

        Steps:
        1. Fetch course and extract skill information
        2. Fetch gap analysis for this specific skill
        3. Fetch content outline for this skill
        4. Fetch workflow metadata
        5. Build PresentationContentSpec for this ONE skill

        Args:
            workflow_id: Workflow execution ID
            course_id: Course/skill to generate presentation for
            custom_title: Optional custom presentation title

        Returns:
            PresentationContentSpec for ONE skill presentation

        Raises:
            ValueError: If course, gap analysis, or content outline not found
        """
        logger.info(f"📋 Preparing presentation content | workflow={workflow_id} | course={course_id}")

        # Step 1: Fetch course and skill information
        course = await self._fetch_course(course_id)
        if not course:
            raise ValueError(f"Course {course_id} not found")

        logger.info(f"  ✓ Course found: {course.course_title} | skill={course.skill_id}")

        # Step 2: Fetch gap analysis for this workflow
        gap_analysis = await self._fetch_gap_analysis(workflow_id)
        if not gap_analysis:
            raise ValueError(f"Gap analysis not found for workflow {workflow_id}")

        # Extract the specific skill gap from the gap analysis
        skill_gap = self._extract_skill_gap(gap_analysis, course.skill_id)
        if not skill_gap:
            logger.warning(f"  ⚠️ Skill gap not found in gap analysis for skill_id={course.skill_id}")
            # Create a default skill gap if not found
            skill_gap = {
                "skill_id": course.skill_id,
                "skill_name": course.skill_name,
                "severity": 5,  # Default medium severity
                "confidence_delta": 0
            }

        logger.info(f"  ✓ Skill gap extracted: severity={skill_gap.get('severity', 0)}")

        # Step 3: Fetch content outline for this skill
        content_outline = await self._fetch_content_outline(workflow_id, course.skill_id)
        if not content_outline:
            logger.warning(f"  ⚠️ Content outline not found for skill_id={course.skill_id}")
            # Create a minimal content outline
            content_outline_dict = {
                "skill_id": course.skill_id,
                "skill_name": course.skill_name,
                "content_items": []
            }
        else:
            content_outline_dict = {
                "skill_id": content_outline.skill_id,
                "skill_name": content_outline.skill_name,
                "exam_domain": content_outline.exam_domain,
                "exam_guide_section": content_outline.exam_guide_section,
                "content_items": content_outline.content_items or [],
                "rag_retrieval_score": float(content_outline.rag_retrieval_score) if content_outline.rag_retrieval_score else None
            }

        logger.info(f"  ✓ Content outline loaded: {len(content_outline_dict['content_items'])} items")

        # Step 4: Fetch workflow metadata
        workflow = await self._fetch_workflow(workflow_id)
        if not workflow:
            raise ValueError(f"Workflow {workflow_id} not found")

        # Extract user information
        user_email = None
        if hasattr(workflow, 'user_id') and workflow.user_id:
            # In a real implementation, you'd fetch the user email from a users table
            # For now, we'll leave it None
            pass

        logger.info(f"  ✓ Workflow loaded: cert={workflow.certification_name or 'Unknown'}")

        # Step 5: Build content specification
        content_spec = PresentationContentSpec(
            workflow_id=workflow_id,
            skill_id=course.skill_id,
            skill_name=course.skill_name,
            title=custom_title or self._generate_title(course.skill_name, workflow),
            subtitle=self._generate_subtitle(gap_analysis),
            skill_gap=skill_gap,
            content_outline=content_outline_dict,
            template_type=TemplateType.SINGLE_SKILL,  # Always single skill in Sprint 3
            template_id="short_form_skill",
            exam_name=workflow.certification_name or "Certification Exam",
            assessment_title=self._extract_assessment_title(workflow),
            learner_name=None,  # Could be extracted from user if available
            user_email=user_email,
            assessment_date=gap_analysis.created_at or datetime.utcnow(),
            overall_score=float(gap_analysis.overall_score)
        )

        logger.info(
            f"✅ Content spec prepared | "
            f"skill={course.skill_name} | "
            f"template={content_spec.template_type} | "
            f"slides_est={self._estimate_slide_count(content_spec)}"
        )

        return content_spec

    async def _fetch_course(self, course_id: UUID) -> Optional[RecommendedCourse]:
        """Fetch course/recommended course from database."""
        stmt = select(RecommendedCourse).where(RecommendedCourse.id == str(course_id))
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def _fetch_gap_analysis(self, workflow_id: UUID) -> Optional[GapAnalysisResult]:
        """Fetch gap analysis results from database."""
        stmt = select(GapAnalysisResult).where(
            GapAnalysisResult.workflow_id == workflow_id
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def _fetch_content_outline(
        self,
        workflow_id: UUID,
        skill_id: str
    ) -> Optional[ContentOutline]:
        """Fetch content outline for a specific skill."""
        stmt = select(ContentOutline).where(
            ContentOutline.workflow_id == workflow_id,
            ContentOutline.skill_id == skill_id
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def _fetch_workflow(self, workflow_id: UUID) -> WorkflowExecution:
        """Fetch workflow execution details."""
        stmt = select(WorkflowExecution).where(WorkflowExecution.id == workflow_id)
        result = await self.db.execute(stmt)
        workflow = result.scalar_one_or_none()
        if not workflow:
            raise ValueError(f"Workflow {workflow_id} not found")
        return workflow

    def _extract_skill_gap(
        self,
        gap_analysis: GapAnalysisResult,
        skill_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Extract a specific skill gap from the gap analysis results.

        Gap analysis stores skill_gaps as a JSON array of objects.
        """
        if not gap_analysis.skill_gaps:
            return None

        # skill_gaps is already a list (from JSON column)
        for gap in gap_analysis.skill_gaps:
            if gap.get("skill_id") == skill_id:
                return gap

        return None

    def _generate_title(
        self,
        skill_name: str,
        workflow: WorkflowExecution
    ) -> str:
        """Generate presentation title."""
        cert_name = workflow.certification_name or "Certification"
        return f"{cert_name} - {skill_name}"

    def _generate_subtitle(self, gap_analysis: GapAnalysisResult) -> str:
        """Generate presentation subtitle."""
        date_str = gap_analysis.created_at.strftime('%B %d, %Y') if gap_analysis.created_at else "Recent"
        return f"Skill Gap Analysis - {date_str}"

    def _extract_assessment_title(self, workflow: WorkflowExecution) -> str:
        """Extract assessment title for Drive folder naming."""
        # Use certification name, or fall back to a default
        if workflow.certification_name:
            return workflow.certification_name
        return "Assessment"

    def _estimate_slide_count(self, content_spec: PresentationContentSpec) -> int:
        """
        Estimate total slide count for short-form presentation.

        Sprint 3: 7-11 slides per skill presentation
        - Title slide: 1
        - Skill introduction: 1-2
        - Gap analysis for this skill: 2-3
        - Learning content: 3-5
        - Summary: 1
        """
        # Base slides
        base_slides = 2  # Title + Summary

        # Skill intro slides
        skill_intro_slides = 2

        # Content slides (based on number of content items)
        content_items = content_spec.content_outline.get('content_items', [])
        content_slides = min(len(content_items), 5)  # Cap at 5 slides

        total = base_slides + skill_intro_slides + content_slides
        return max(7, min(total, 11))  # Ensure 7-11 range
