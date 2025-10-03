"""
Content Orchestration Service for Sprint 3

Orchestrates content preparation for per-skill presentation generation.
Each service call prepares content for ONE skill gap (not all skills).
"""

import logging
import json
from typing import Optional, Dict, Any
from uuid import UUID
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from sqlalchemy.orm import selectinload

from src.schemas.presentation import PresentationContentSpec, TemplateType
from src.models.workflow import WorkflowExecution
from src.models.gap_analysis import GapAnalysisResult, ContentOutline, RecommendedCourse

logger = logging.getLogger(__name__)


def normalize_uuid_for_sqlite(uuid_value: UUID) -> str:
    """Convert UUID to SQLite-compatible string (no hyphens)."""
    return str(uuid_value).replace('-', '')


def parse_json_field(value):
    """Parse JSON string from SQLite to Python dict/list."""
    if value is None:
        return None
    if isinstance(value, str):
        return json.loads(value)
    return value


def parse_datetime_field(value):
    """Parse datetime string from SQLite to Python datetime."""
    if value is None:
        return None
    if isinstance(value, str):
        # SQLite stores datetime as strings, parse them
        try:
            # Try with timezone fix first
            return datetime.fromisoformat(value.replace('Z', '+00:00'))
        except ValueError:
            try:
                # Try without modification
                return datetime.fromisoformat(value)
            except ValueError:
                # If it's not a valid datetime, return None
                # This can happen if the field is empty or invalid
                return None
    return value


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
        # Use raw SQL to bypass PGUUID type processor issues with SQLite
        course_id_str = normalize_uuid_for_sqlite(course_id)
        stmt = text("SELECT * FROM recommended_courses WHERE id = :course_id")
        result = await self.db.execute(stmt, {"course_id": course_id_str})
        row = result.fetchone()

        if not row:
            return None

        # Map row to RecommendedCourse object (parse JSON and datetime fields)
        course = RecommendedCourse()
        course.id = row[0]
        course.gap_analysis_id = row[1]
        course.workflow_id = row[2]
        course.skill_id = row[3]
        course.skill_name = row[4]
        course.exam_domain = row[5]
        course.exam_subsection = row[6]
        course.course_title = row[7]
        course.course_description = row[8]
        course.estimated_duration_minutes = row[9]
        course.difficulty_level = row[10]
        course.learning_objectives = parse_json_field(row[11])
        course.content_outline = parse_json_field(row[12])
        course.generation_status = row[13]
        course.generation_started_at = parse_datetime_field(row[14])
        course.generation_completed_at = parse_datetime_field(row[15])
        course.generation_error = row[16]
        course.video_url = row[17]
        course.presentation_url = row[18]
        course.download_url = row[19]
        course.priority = row[20]
        course.recommended_at = parse_datetime_field(row[21])
        course.created_at = parse_datetime_field(row[22])
        course.updated_at = parse_datetime_field(row[23])
        return course

    async def _fetch_gap_analysis(self, workflow_id: UUID) -> Optional[GapAnalysisResult]:
        """Fetch gap analysis results from database."""
        # Use raw SQL to bypass PGUUID type processor issues with SQLite
        workflow_id_str = normalize_uuid_for_sqlite(workflow_id)
        stmt = text("SELECT * FROM gap_analysis_results WHERE workflow_id = :workflow_id")
        result = await self.db.execute(stmt, {"workflow_id": workflow_id_str})
        row = result.fetchone()

        if not row:
            return None

        # Map row to GapAnalysisResult object (parse JSON and datetime fields)
        gap = GapAnalysisResult()
        gap.id = row[0]
        gap.workflow_id = row[1]
        gap.overall_score = row[2]
        gap.total_questions = row[3]
        gap.correct_answers = row[4]
        gap.incorrect_answers = row[5]
        gap.skill_gaps = parse_json_field(row[6])
        gap.performance_by_domain = parse_json_field(row[7])
        gap.severity_scores = parse_json_field(row[8])
        gap.text_summary = row[9]
        gap.charts_data = parse_json_field(row[10])
        gap.certification_profile_id = row[11]
        gap.generated_at = parse_datetime_field(row[12])
        gap.created_at = parse_datetime_field(row[13])
        gap.updated_at = parse_datetime_field(row[14])
        return gap

    async def _fetch_content_outline(
        self,
        workflow_id: UUID,
        skill_id: str
    ) -> Optional[ContentOutline]:
        """Fetch content outline for a specific skill."""
        # Use raw SQL to bypass PGUUID type processor issues with SQLite
        workflow_id_str = normalize_uuid_for_sqlite(workflow_id)
        stmt = text("SELECT * FROM content_outlines WHERE workflow_id = :workflow_id AND skill_id = :skill_id")
        result = await self.db.execute(stmt, {"workflow_id": workflow_id_str, "skill_id": skill_id})
        row = result.fetchone()

        if not row:
            return None

        # Map row to ContentOutline object (parse JSON and datetime fields)
        outline = ContentOutline()
        outline.id = row[0]
        outline.gap_analysis_id = row[1]
        outline.workflow_id = row[2]
        outline.skill_id = row[3]
        outline.skill_name = row[4]
        outline.exam_domain = row[5]
        outline.exam_guide_section = row[6]
        outline.content_items = parse_json_field(row[7])
        outline.rag_retrieval_score = row[8]
        outline.retrieved_at = parse_datetime_field(row[9])
        outline.created_at = parse_datetime_field(row[10])
        outline.updated_at = parse_datetime_field(row[11])
        return outline

    async def _fetch_workflow(self, workflow_id: UUID) -> WorkflowExecution:
        """Fetch workflow execution details."""
        # Use raw SQL to bypass PGUUID type processor issues with SQLite
        workflow_id_str = normalize_uuid_for_sqlite(workflow_id)
        stmt = text("SELECT * FROM workflow_executions WHERE id = :workflow_id")
        result = await self.db.execute(stmt, {"workflow_id": workflow_id_str})
        row = result.fetchone()

        if not row:
            raise ValueError(f"Workflow {workflow_id} not found")

        # Map row to WorkflowExecution object (parse datetime fields)
        workflow = WorkflowExecution()
        workflow.id = row[0]
        workflow.status = row[1]
        workflow.certification_id = row[2]
        workflow.certification_name = row[3]
        workflow.form_url = row[4]
        workflow.form_id = row[5]
        workflow.assessment_results_id = row[6]
        workflow.gap_analysis_id = row[7]
        workflow.current_step = row[8]
        workflow.error_message = row[9]
        workflow.created_at = parse_datetime_field(row[10])
        workflow.updated_at = parse_datetime_field(row[11])
        workflow.completed_at = parse_datetime_field(row[12])
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
