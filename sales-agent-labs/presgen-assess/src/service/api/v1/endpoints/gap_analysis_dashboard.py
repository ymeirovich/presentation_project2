"""Gap Analysis Dashboard API endpoints for Sprint 1.

Provides endpoints to retrieve Gap Analysis results, content outlines,
and course recommendations for the dashboard UI.
"""

import logging
from typing import Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, status, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from src.service.database import get_db
from src.models.gap_analysis import (
    GapAnalysisResult as GapAnalysisResultModel,
    ContentOutline as ContentOutlineModel,
    RecommendedCourse as RecommendedCourseModel
)
from src.schemas.gap_analysis import (
    GapAnalysisResult,
    ContentOutlineItem,
    RecommendedCourse
)
from src.common.logging_config import get_gap_analysis_logger

logger = get_gap_analysis_logger()
router = APIRouter()


@router.get(
    "/workflow/{workflow_id}",
    response_model=GapAnalysisResult,
    status_code=status.HTTP_200_OK
)
async def get_gap_analysis_by_workflow(
    workflow_id: UUID,
    db: AsyncSession = Depends(get_db)
) -> GapAnalysisResult:
    """
    Retrieve Gap Analysis results for a workflow.

    Returns complete gap analysis data including:
    - Overall score and statistics
    - Skill gaps with severity scores
    - Performance by domain
    - Text summary
    - Charts data

    Args:
        workflow_id: UUID of the workflow execution
        db: Database session

    Returns:
        GapAnalysisResult: Complete gap analysis data

    Raises:
        404: Gap analysis not found for workflow
        500: Database error
    """
    try:
        logger.info(f"Fetching gap analysis for workflow: {workflow_id}")

        # Query database for gap analysis result (most recent)
        result = await db.execute(
            select(GapAnalysisResultModel)
            .where(GapAnalysisResultModel.workflow_id == workflow_id)
            .order_by(GapAnalysisResultModel.created_at.desc())
            .limit(1)
        )
        gap_analysis_db = result.scalar_one_or_none()

        if not gap_analysis_db:
            logger.warning(f"Gap analysis not found for workflow: {workflow_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Gap analysis not found for workflow {workflow_id}"
            )

        # Convert database model to response schema
        gap_analysis_response = GapAnalysisResult(
            workflow_id=gap_analysis_db.workflow_id,
            overall_score=gap_analysis_db.overall_score,
            total_questions=gap_analysis_db.total_questions,
            correct_answers=gap_analysis_db.correct_answers,
            incorrect_answers=gap_analysis_db.incorrect_answers,
            skill_gaps=gap_analysis_db.skill_gaps,
            performance_by_domain=gap_analysis_db.performance_by_domain,
            text_summary=gap_analysis_db.text_summary,
            charts_data=gap_analysis_db.charts_data,
            generated_at=gap_analysis_db.created_at
        )

        logger.info(f"✅ Gap analysis retrieved: {len(gap_analysis_response.skill_gaps)} skill gaps found")
        return gap_analysis_response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to retrieve gap analysis: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve gap analysis: {str(e)}"
        )


@router.get(
    "/workflow/{workflow_id}/content-outlines",
    response_model=List[ContentOutlineItem],
    status_code=status.HTTP_200_OK
)
async def get_content_outlines(
    workflow_id: UUID,
    db: AsyncSession = Depends(get_db)
) -> List[ContentOutlineItem]:
    """
    Retrieve content outlines for a workflow's skill gaps.

    Returns RAG-retrieved content mapped to each skill gap,
    including exam guide sections and learning resources.

    Args:
        workflow_id: UUID of the workflow execution
        db: Database session

    Returns:
        List[ContentOutlineItem]: Content outlines for all skill gaps

    Raises:
        404: Gap analysis not found
        500: Database error
    """
    try:
        logger.info(f"Fetching content outlines for workflow: {workflow_id}")

        # First verify gap analysis exists (get most recent)
        gap_result = await db.execute(
            select(GapAnalysisResultModel)
            .where(GapAnalysisResultModel.workflow_id == workflow_id)
            .order_by(GapAnalysisResultModel.created_at.desc())
            .limit(1)
        )
        gap_analysis = gap_result.scalar_one_or_none()

        if not gap_analysis:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Gap analysis not found for workflow {workflow_id}"
            )

        # Query content outlines
        result = await db.execute(
            select(ContentOutlineModel).where(
                ContentOutlineModel.gap_analysis_id == gap_analysis.id
            )
        )
        content_outlines_db = result.scalars().all()

        # Convert to response schemas
        content_outlines = [
            ContentOutlineItem(
                skill_id=outline.skill_id,
                skill_name=outline.skill_name,
                exam_domain=outline.exam_domain,
                exam_guide_section=outline.exam_guide_section,
                content_items=outline.content_items,
                rag_retrieval_score=outline.rag_retrieval_score
            )
            for outline in content_outlines_db
        ]

        logger.info(f"✅ Retrieved {len(content_outlines)} content outlines")
        return content_outlines

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to retrieve content outlines: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve content outlines: {str(e)}"
        )


@router.get(
    "/workflow/{workflow_id}/recommended-courses",
    response_model=List[RecommendedCourse],
    status_code=status.HTTP_200_OK
)
async def get_recommended_courses(
    workflow_id: UUID,
    db: AsyncSession = Depends(get_db)
) -> List[RecommendedCourse]:
    """
    Retrieve recommended courses for a workflow's skill gaps.

    Returns personalized course recommendations ordered by priority
    (severity of skill gap). Each course includes:
    - Learning objectives
    - Content outline
    - Generation status
    - Duration estimate

    Args:
        workflow_id: UUID of the workflow execution
        db: Database session

    Returns:
        List[RecommendedCourse]: Courses ordered by priority (high to low)

    Raises:
        404: Gap analysis not found
        500: Database error
    """
    try:
        logger.info(f"Fetching recommended courses for workflow: {workflow_id}")

        # First verify gap analysis exists (get most recent)
        gap_result = await db.execute(
            select(GapAnalysisResultModel)
            .where(GapAnalysisResultModel.workflow_id == workflow_id)
            .order_by(GapAnalysisResultModel.created_at.desc())
            .limit(1)
        )
        gap_analysis = gap_result.scalar_one_or_none()

        if not gap_analysis:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Gap analysis not found for workflow {workflow_id}"
            )

        # Query recommended courses, ordered by priority descending
        result = await db.execute(
            select(RecommendedCourseModel)
            .where(RecommendedCourseModel.gap_analysis_id == gap_analysis.id)
            .order_by(RecommendedCourseModel.priority.desc())
        )
        courses_db = result.scalars().all()

        # Convert to response schemas
        courses = [
            RecommendedCourse(
                id=course.id,
                workflow_id=course.workflow_id,
                skill_id=course.skill_id,
                skill_name=course.skill_name,
                exam_domain=course.exam_domain,
                exam_subsection=course.exam_subsection,
                course_title=course.course_title,
                course_description=course.course_description,
                estimated_duration_minutes=course.estimated_duration_minutes,
                difficulty_level=course.difficulty_level,
                learning_objectives=course.learning_objectives,
                content_outline=course.content_outline,
                generation_status=course.generation_status,
                priority=course.priority
            )
            for course in courses_db
        ]

        logger.info(f"✅ Retrieved {len(courses)} recommended courses")
        return courses

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to retrieve recommended courses: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve recommended courses: {str(e)}"
        )


@router.get(
    "/workflow/{workflow_id}/answers",
    status_code=status.HTTP_200_OK
)
async def get_assessment_answers(
    workflow_id: UUID,
    db: AsyncSession = Depends(get_db)
) -> Dict:
    """
    Retrieve assessment answers with explanations for correct/incorrect responses.

    Returns detailed answer information including:
    - Question text
    - User's answer
    - Correct answer
    - Explanation for the correct answer
    - Whether the user was correct
    - Domain and difficulty level

    This endpoint powers the Answers tab on the Gap Analysis Dashboard.

    Args:
        workflow_id: UUID of the workflow execution
        db: Database session

    Returns:
        Dict: Contains lists of correct and incorrect answers with explanations

    Raises:
        404: Workflow or assessment data not found
        500: Database error
    """
    try:
        logger.info(f"Fetching assessment answers for workflow: {workflow_id}")

        # Get workflow with assessment data
        from src.models.workflow import WorkflowExecution

        result = await db.execute(
            select(WorkflowExecution).where(WorkflowExecution.id == workflow_id)
        )
        workflow = result.scalar_one_or_none()

        if not workflow:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Workflow {workflow_id} not found"
            )

        # Extract questions and responses from workflow
        assessment_data = workflow.assessment_data or {}
        questions = assessment_data.get("questions", [])
        responses = workflow.collected_responses or []

        # Create a map of question_id to question data
        question_map = {q.get("id"): q for q in questions}

        # Process responses and categorize as correct/incorrect
        correct_answers = []
        incorrect_answers = []

        for response in responses:
            question_id = response.get("question_id")
            question = question_map.get(question_id, {})

            if not question:
                continue

            user_answer = response.get("answer")
            correct_answer = question.get("correct_answer")
            is_correct = user_answer == correct_answer

            answer_detail = {
                "question_id": question_id,
                "question_text": question.get("question_text", ""),
                "user_answer": user_answer,
                "correct_answer": correct_answer,
                "explanation": question.get("explanation", "No explanation available."),
                "domain": question.get("domain", "General"),
                "difficulty": question.get("difficulty", "intermediate"),
                "options": question.get("options", []),
                "is_correct": is_correct
            }

            if is_correct:
                correct_answers.append(answer_detail)
            else:
                incorrect_answers.append(answer_detail)

        logger.info(f"✅ Retrieved {len(correct_answers)} correct and {len(incorrect_answers)} incorrect answers")

        return {
            "workflow_id": str(workflow_id),
            "total_questions": len(questions),
            "correct_count": len(correct_answers),
            "incorrect_count": len(incorrect_answers),
            "correct_answers": correct_answers,
            "incorrect_answers": incorrect_answers,
            "score_percentage": round((len(correct_answers) / len(questions) * 100), 2) if questions else 0
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to retrieve assessment answers: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve assessment answers: {str(e)}"
        )


@router.get(
    "/workflow/{workflow_id}/summary",
    status_code=status.HTTP_200_OK
)
async def get_gap_analysis_summary(
    workflow_id: UUID,
    db: AsyncSession = Depends(get_db)
) -> Dict:
    """
    Retrieve Gap Analysis summary dashboard data.

    Returns a consolidated summary including:
    - Overall score and statistics
    - Top 5 skill gaps
    - Performance by domain (chart data)
    - Text summary
    - Count of content outlines and courses

    This endpoint is optimized for dashboard initial load.

    Args:
        workflow_id: UUID of the workflow execution
        db: Database session

    Returns:
        Dict: Dashboard summary data

    Raises:
        404: Gap analysis not found
        500: Database error
    """
    try:
        logger.info(f"Fetching gap analysis summary for workflow: {workflow_id}")

        # Query gap analysis
        gap_result = await db.execute(
            select(GapAnalysisResultModel).where(
                GapAnalysisResultModel.workflow_id == workflow_id
            )
        )
        gap_analysis = gap_result.scalar_one_or_none()

        if not gap_analysis:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Gap analysis not found for workflow {workflow_id}"
            )

        # Count content outlines
        content_count_result = await db.execute(
            select(ContentOutlineModel).where(
                ContentOutlineModel.gap_analysis_id == gap_analysis.id
            )
        )
        content_outlines_count = len(content_count_result.scalars().all())

        # Count recommended courses
        courses_count_result = await db.execute(
            select(RecommendedCourseModel).where(
                RecommendedCourseModel.gap_analysis_id == gap_analysis.id
            )
        )
        courses_count = len(courses_count_result.scalars().all())

        # Get top 5 skill gaps by severity
        skill_gaps = gap_analysis.skill_gaps
        top_skill_gaps = sorted(
            skill_gaps,
            key=lambda x: x.get("severity", 0),
            reverse=True
        )[:5]

        summary = {
            "workflow_id": str(workflow_id),
            "overall_score": gap_analysis.overall_score,
            "total_questions": gap_analysis.total_questions,
            "correct_answers": gap_analysis.correct_answers,
            "incorrect_answers": gap_analysis.incorrect_answers,
            "text_summary": gap_analysis.text_summary,
            "performance_by_domain": gap_analysis.performance_by_domain,
            "top_skill_gaps": top_skill_gaps,
            "total_skill_gaps": len(skill_gaps),
            "content_outlines_count": content_outlines_count,
            "recommended_courses_count": courses_count,
            "charts_data": gap_analysis.charts_data or {},
            "generated_at": gap_analysis.created_at.isoformat()
        }

        logger.info(f"✅ Gap analysis summary retrieved")
        return summary

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to retrieve gap analysis summary: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve gap analysis summary: {str(e)}"
        )


@router.post(
    "/courses/{course_id}/generate",
    status_code=status.HTTP_202_ACCEPTED
)
async def trigger_course_generation(
    course_id: UUID,
    db: AsyncSession = Depends(get_db)
) -> Dict:
    """
    Trigger course generation for a recommended course.

    Updates the course status to 'in_progress' and triggers
    the PresGen-Core + PresGen-Avatar workflow (Sprint 3-4).

    Args:
        course_id: UUID of the recommended course
        db: Database session

    Returns:
        Dict: Status update with workflow info

    Raises:
        404: Course not found
        409: Course already generated or in progress
        500: Database error
    """
    try:
        logger.info(f"Triggering course generation for course: {course_id}")

        # Query recommended course
        result = await db.execute(
            select(RecommendedCourseModel).where(
                RecommendedCourseModel.id == course_id
            )
        )
        course = result.scalar_one_or_none()

        if not course:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Recommended course {course_id} not found"
            )

        # Check if already generated or in progress
        if course.generation_status in ["completed", "in_progress"]:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Course generation already {course.generation_status}"
            )

        # Update status to in_progress
        course.generation_status = "in_progress"
        await db.commit()

        logger.info(f"✅ Course generation triggered for: {course.course_title}")

        # TODO Sprint 3-4: Trigger PresGen-Core + PresGen-Avatar workflow
        return {
            "success": True,
            "course_id": str(course_id),
            "status": "in_progress",
            "message": "Course generation workflow initiated",
            "estimated_duration_minutes": course.estimated_duration_minutes
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to trigger course generation: {e}", exc_info=True)
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to trigger course generation: {str(e)}"
        )


@router.get("/health")
async def gap_analysis_dashboard_health() -> Dict:
    """
    Health check for Gap Analysis Dashboard API.

    Returns:
        Dict: Health status
    """
    return {
        "status": "healthy",
        "service": "gap_analysis_dashboard",
        "sprint": "Sprint 1",
        "endpoints": [
            "GET /workflow/{workflow_id}",
            "GET /workflow/{workflow_id}/content-outlines",
            "GET /workflow/{workflow_id}/recommended-courses",
            "GET /workflow/{workflow_id}/answers",
            "GET /workflow/{workflow_id}/summary",
            "POST /courses/{course_id}/generate"
        ]
    }