"""
Sprint 3: Per-Skill Presentation Generation API Endpoints

Endpoints for generating individual skill-focused presentations (3-7 minutes each).
Each skill gap gets its own presentation, not one comprehensive presentation.
"""

import logging
from typing import List
from uuid import UUID, uuid4
from datetime import datetime

from fastapi import APIRouter, HTTPException, status, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from src.service.database import get_db_session
from src.schemas.presentation import (
    PresentationGenerationRequest,
    BatchPresentationGenerationRequest,
    PresentationGenerationResponse,
    BatchPresentationGenerationResponse,
    PresentationJobStatus,
    GeneratedPresentation as GeneratedPresentationSchema,
    PresentationListResponse
)
from src.models.presentation import GeneratedPresentation
from src.models.gaps import RecommendedCourse
from src.service.content_orchestration import ContentOrchestrationService
from src.service.background_jobs import job_queue

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post(
    "/workflows/{workflow_id}/courses/{course_id}/generate-presentation",
    response_model=PresentationGenerationResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Generate presentation for a single skill/course"
)
async def generate_single_presentation(
    workflow_id: UUID,
    course_id: UUID,
    request: PresentationGenerationRequest,
    db: AsyncSession = Depends(get_db_session)
) -> PresentationGenerationResponse:
    """
    Generate presentation for a single skill gap.

    Sprint 3: Creates ONE short-form presentation (3-7 minutes, 7-11 slides)
    for the specified course/skill.

    This is an async operation - returns immediately with job_id.
    Use status endpoint to check progress.

    Args:
        workflow_id: Workflow execution ID
        course_id: Course/skill to generate presentation for
        request: Generation request with optional custom title

    Returns:
        PresentationGenerationResponse with job_id and estimated duration
    """
    try:
        logger.info(
            f"📋 Generate presentation request | "
            f"workflow={workflow_id} | course={course_id}"
        )

        # Validate that workflow_id and course_id match in request
        if request.workflow_id != workflow_id or request.course_id != course_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Workflow ID or Course ID in request doesn't match URL parameters"
            )

        # Check if course exists
        course_stmt = select(RecommendedCourse).where(
            RecommendedCourse.id == str(course_id)
        )
        course_result = await db.execute(course_stmt)
        course = course_result.scalar_one_or_none()

        if not course:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Course {course_id} not found"
            )

        # Check if presentation already exists for this skill
        existing_stmt = select(GeneratedPresentation).where(
            GeneratedPresentation.workflow_id == str(workflow_id),
            GeneratedPresentation.skill_id == course.skill_id,
            GeneratedPresentation.generation_status == 'completed'
        )
        existing_result = await db.execute(existing_stmt)
        existing = existing_result.scalar_one_or_none()

        if existing:
            logger.warning(
                f"⚠️  Presentation already exists for skill={course.skill_id}. "
                f"Returning existing presentation."
            )
            # Return existing presentation as if it's a new job
            return PresentationGenerationResponse(
                success=True,
                job_id=existing.job_id or "completed",
                presentation_id=UUID(existing.id),
                message=f"Presentation already exists for {course.skill_name}",
                estimated_duration_seconds=0,
                status_check_url=f"/api/v1/workflows/{workflow_id}/presentations/{existing.id}/status"
            )

        # Prepare content specification using ContentOrchestrationService
        orchestrator = ContentOrchestrationService(db)
        content_spec = await orchestrator.prepare_presentation_content(
            workflow_id=workflow_id,
            course_id=course_id,
            custom_title=request.custom_title
        )

        # Create presentation record
        presentation_id = uuid4()
        presentation = GeneratedPresentation(
            id=str(presentation_id),
            workflow_id=str(workflow_id),
            skill_id=course.skill_id,
            skill_name=course.skill_name,
            course_id=str(course_id),
            assessment_title=content_spec.assessment_title,
            user_email=content_spec.user_email,
            presentation_title=content_spec.title,
            generation_status='pending',
            template_name='Skill-Focused Presentation',
            created_at=datetime.utcnow()
        )

        db.add(presentation)
        await db.commit()

        # Enqueue background job
        job_id = await job_queue.enqueue(
            presentation_id=presentation_id,
            content_spec=content_spec,
            db_session=db
        )

        # Update presentation with job_id
        presentation.job_id = job_id
        await db.commit()

        logger.info(
            f"✅ Presentation generation started | "
            f"job_id={job_id} | "
            f"skill={course.skill_name}"
        )

        return PresentationGenerationResponse(
            success=True,
            job_id=job_id,
            presentation_id=presentation_id,
            message=f"Presentation generation started for {course.skill_name}",
            estimated_duration_seconds=300,  # 5 minutes estimate (3-7 min range)
            status_check_url=f"/api/v1/workflows/{workflow_id}/presentations/{presentation_id}/status"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to start presentation generation: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to initiate presentation generation: {str(e)}"
        )


@router.post(
    "/workflows/{workflow_id}/generate-all-presentations",
    response_model=BatchPresentationGenerationResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Generate presentations for all courses in workflow"
)
async def generate_all_presentations(
    workflow_id: UUID,
    request: BatchPresentationGenerationRequest,
    db: AsyncSession = Depends(get_db_session)
) -> BatchPresentationGenerationResponse:
    """
    Generate presentations for ALL courses/skills in a workflow.

    Sprint 3: Creates multiple parallel jobs (one per skill).
    Returns immediately with list of job IDs.

    Args:
        workflow_id: Workflow execution ID
        request: Batch generation request with max_concurrent setting

    Returns:
        BatchPresentationGenerationResponse with list of started jobs
    """
    try:
        logger.info(
            f"📋 Batch generate presentations | "
            f"workflow={workflow_id} | "
            f"max_concurrent={request.max_concurrent}"
        )

        # Fetch all courses for this workflow
        courses_stmt = select(RecommendedCourse).where(
            RecommendedCourse.workflow_id == str(workflow_id)
        )
        courses_result = await db.execute(courses_stmt)
        courses = courses_result.scalars().all()

        if not courses:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No courses found for workflow {workflow_id}"
            )

        logger.info(f"  Found {len(courses)} courses to process")

        jobs = []
        orchestrator = ContentOrchestrationService(db)

        # Generate presentation for each course
        for course in courses:
            # Check if already exists
            existing_stmt = select(GeneratedPresentation).where(
                GeneratedPresentation.workflow_id == str(workflow_id),
                GeneratedPresentation.skill_id == course.skill_id,
                GeneratedPresentation.generation_status == 'completed'
            )
            existing_result = await db.execute(existing_stmt)
            if existing_result.scalar_one_or_none():
                logger.info(f"  ⏭️  Skipping {course.skill_name} - already exists")
                continue

            # Prepare content spec
            content_spec = await orchestrator.prepare_presentation_content(
                workflow_id=workflow_id,
                course_id=UUID(course.id),
                custom_title=None
            )

            # Create presentation record
            presentation_id = uuid4()
            presentation = GeneratedPresentation(
                id=str(presentation_id),
                workflow_id=str(workflow_id),
                skill_id=course.skill_id,
                skill_name=course.skill_name,
                course_id=course.id,
                assessment_title=content_spec.assessment_title,
                user_email=content_spec.user_email,
                presentation_title=content_spec.title,
                generation_status='pending',
                template_name='Skill-Focused Presentation',
                created_at=datetime.utcnow()
            )

            db.add(presentation)
            await db.commit()

            # Enqueue job
            job_id = await job_queue.enqueue(
                presentation_id=presentation_id,
                content_spec=content_spec,
                db_session=db
            )

            presentation.job_id = job_id
            await db.commit()

            jobs.append({
                "job_id": job_id,
                "presentation_id": str(presentation_id),
                "skill_name": course.skill_name
            })

            logger.info(f"  ✓ Started job for {course.skill_name}")

        # Estimate total duration (parallel execution)
        # If max_concurrent=3 and 9 jobs, then ~3 batches * 5min = ~15min
        batches = (len(jobs) + request.max_concurrent - 1) // request.max_concurrent
        estimated_total_seconds = batches * 300  # 5 minutes per batch

        logger.info(
            f"✅ Batch generation started | "
            f"jobs={len(jobs)} | "
            f"est_duration={estimated_total_seconds}s"
        )

        return BatchPresentationGenerationResponse(
            success=True,
            jobs=jobs,
            message=f"Started generation for {len(jobs)} skill presentations",
            total_presentations=len(jobs),
            estimated_total_duration_seconds=estimated_total_seconds
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Batch generation failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start batch generation: {str(e)}"
        )


@router.get(
    "/workflows/{workflow_id}/presentations/{presentation_id}/status",
    response_model=PresentationJobStatus,
    summary="Get presentation generation status"
)
async def get_presentation_status(
    workflow_id: UUID,
    presentation_id: UUID,
    db: AsyncSession = Depends(get_db_session)
) -> PresentationJobStatus:
    """
    Get status of a presentation generation job.

    Returns real-time progress (0-100%) and current step.
    """
    try:
        # Fetch presentation from database
        stmt = select(GeneratedPresentation).where(
            GeneratedPresentation.id == str(presentation_id),
            GeneratedPresentation.workflow_id == str(workflow_id)
        )
        result = await db.execute(stmt)
        presentation = result.scalar_one_or_none()

        if not presentation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Presentation {presentation_id} not found"
            )

        # Get job status from queue if still in progress
        if presentation.job_id and presentation.generation_status in ['pending', 'generating']:
            queue_status = job_queue.get_job_status(presentation.job_id)
            if queue_status:
                return queue_status

        # Return status from database
        return PresentationJobStatus(
            job_id=presentation.job_id or "",
            presentation_id=presentation_id,
            status=presentation.generation_status,
            progress=presentation.job_progress or 100,
            current_step="Complete" if presentation.generation_status == 'completed' else None,
            error_message=presentation.job_error_message
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to get status: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve presentation status: {str(e)}"
        )


@router.get(
    "/workflows/{workflow_id}/presentations",
    response_model=PresentationListResponse,
    summary="List all presentations for workflow"
)
async def list_presentations(
    workflow_id: UUID,
    db: AsyncSession = Depends(get_db_session)
) -> PresentationListResponse:
    """
    List all presentations for a workflow with statistics.

    Returns all presentations (completed, generating, pending, failed)
    with count summaries.
    """
    try:
        # Fetch all presentations
        stmt = select(GeneratedPresentation).where(
            GeneratedPresentation.workflow_id == str(workflow_id)
        ).order_by(GeneratedPresentation.created_at.desc())

        result = await db.execute(stmt)
        presentations = result.scalars().all()

        # Get counts by status
        counts_stmt = select(
            GeneratedPresentation.generation_status,
            func.count(GeneratedPresentation.id)
        ).where(
            GeneratedPresentation.workflow_id == str(workflow_id)
        ).group_by(GeneratedPresentation.generation_status)

        counts_result = await db.execute(counts_stmt)
        counts = dict(counts_result.all())

        # Convert to schema
        presentation_schemas = [
            GeneratedPresentationSchema(
                id=UUID(p.id),
                workflow_id=UUID(p.workflow_id),
                skill_id=p.skill_id,
                skill_name=p.skill_name,
                course_id=UUID(p.course_id) if p.course_id else None,
                assessment_title=p.assessment_title,
                user_email=p.user_email,
                drive_folder_path=p.drive_folder_path,
                presentation_title=p.presentation_title,
                presentation_url=p.presentation_url,
                download_url=p.download_url,
                drive_file_id=p.drive_file_id,
                generation_status=p.generation_status,
                generation_started_at=p.generation_started_at,
                generation_completed_at=p.generation_completed_at,
                generation_duration_ms=p.generation_duration_ms,
                estimated_duration_minutes=p.estimated_duration_minutes,
                job_id=p.job_id,
                job_progress=p.job_progress or 0,
                job_error_message=p.job_error_message,
                template_name=p.template_name,
                total_slides=p.total_slides,
                file_size_mb=p.file_size_mb,
                thumbnail_url=p.thumbnail_url,
                created_at=p.created_at,
                updated_at=p.updated_at
            )
            for p in presentations
        ]

        return PresentationListResponse(
            workflow_id=workflow_id,
            presentations=presentation_schemas,
            total_count=len(presentations),
            completed_count=counts.get('completed', 0),
            pending_count=counts.get('pending', 0),
            generating_count=counts.get('generating', 0),
            failed_count=counts.get('failed', 0)
        )

    except Exception as e:
        logger.error(f"❌ Failed to list presentations: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list presentations: {str(e)}"
        )
