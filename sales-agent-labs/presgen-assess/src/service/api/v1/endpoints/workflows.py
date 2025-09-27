"""Async workflow management API endpoints."""

from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.common.logging_config import get_workflow_logger
from src.models.workflow import WorkflowExecution
from src.schemas.workflow import (
    WorkflowCreate,
    WorkflowResponse,
    WorkflowResumeRequest,
    WorkflowStatusUpdate
)
from src.schemas.google_forms import AssessmentWorkflowRequest, FormSettings
from src.service.database import get_db
from src.services.workflow_orchestrator import WorkflowOrchestrator
from src.services.response_ingestion_service import ResponseIngestionService

logger = get_workflow_logger()

router = APIRouter()


@router.post("/", response_model=WorkflowResponse, status_code=status.HTTP_201_CREATED)
async def create_workflow(
    workflow_data: WorkflowCreate,
    db: AsyncSession = Depends(get_db)
) -> WorkflowResponse:
    """Create a new async workflow."""
    try:
        # Map WorkflowCreate data to WorkflowExecution fields
        workflow_dict = workflow_data.model_dump(exclude_none=True)

        # Ensure required fields exist for ORM compatibility and UI expectations
        workflow_dict.setdefault('current_step', 'initiated')
        workflow_dict.setdefault('execution_status', 'pending')
        workflow_dict['status'] = workflow_dict.get('execution_status', 'pending')
        workflow_dict.setdefault('progress', 0)

        # Backfill slide count tracking so downstream steps have defaults
        if 'requested_slide_count' not in workflow_dict:
            requested_slides = (
                workflow_dict.get('parameters', {}).get('slide_count')
                if isinstance(workflow_dict.get('parameters'), dict)
                else None
            )
            if requested_slides:
                workflow_dict['requested_slide_count'] = requested_slides

        # Map schema field names to database column names
        google_sheet_url = workflow_dict.pop('google_sheet_url', None)
        if google_sheet_url:
            workflow_dict['sheet_url_input'] = google_sheet_url

        logger.info(
            "📥 Creating workflow | user_id=%s profile_id=%s workflow_type=%s",
            workflow_dict.get('user_id'),
            workflow_dict.get('certification_profile_id'),
            workflow_dict.get('workflow_type'),
        )

        workflow = WorkflowExecution(**workflow_dict)
        db.add(workflow)
        await db.commit()
        await db.refresh(workflow)

        logger.info(
            "✅ Workflow created | id=%s status=%s current_step=%s",
            workflow.id,
            workflow.status,
            workflow.current_step,
        )

        # Auto-trigger orchestration for assessment_generation workflows
        if workflow.workflow_type == "assessment_generation":
            try:
                logger.info("🚀 Auto-triggering orchestration for assessment_generation workflow")

                # Convert workflow parameters to assessment_data format
                assessment_data = {
                    "questions": [
                        {
                            "id": f"q{i+1}",
                            "question_text": f"Sample question {i+1} for {workflow.parameters.get('title', 'Assessment')}",
                            "question_type": "multiple_choice",
                            "options": ["A) Option 1", "B) Option 2", "C) Option 3", "D) Option 4"],
                            "correct_answer": "A"
                        } for i in range(min(5, workflow.parameters.get('question_count', 24) // 5))
                    ],
                    "metadata": {
                        "certification_name": workflow.parameters.get('title', 'Assessment'),
                        "difficulty_level": workflow.parameters.get('difficulty_level', 'beginner'),
                        "question_count": workflow.parameters.get('question_count', 24),
                        "domain_distribution": workflow.parameters.get('domain_distribution', {})
                    }
                }

                form_settings = FormSettings(
                    collect_email=True,
                    require_login=False
                )

                orchestrator = WorkflowOrchestrator()
                orchestration_result = await orchestrator.execute_assessment_to_form_workflow(
                    certification_profile_id=workflow.certification_profile_id,
                    user_id=workflow.user_id,
                    assessment_data=assessment_data,
                    form_settings=form_settings
                )

                if orchestration_result.get("success"):
                    logger.info(f"✅ Auto-orchestration successful for workflow {workflow.id}")
                else:
                    logger.warning(f"⚠️ Auto-orchestration failed for workflow {workflow.id}: {orchestration_result.get('error')}")

            except Exception as e:
                logger.error(f"❌ Auto-orchestration error for workflow {workflow.id}: {e}")

        return WorkflowResponse.model_validate(workflow)

    except Exception as e:
        await db.rollback()
        logger.exception("❌ Failed to create workflow")
        logger.error("❌ Payload causing failure: %s", workflow_data.model_dump())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create workflow: {str(e)}"
        )


@router.get("/", response_model=List[WorkflowResponse])
async def list_workflows(
    status_filter: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db)
) -> List[WorkflowResponse]:
    """List workflows with optional status filtering."""
    try:
        stmt = select(WorkflowExecution).offset(skip).limit(limit).order_by(WorkflowExecution.created_at.desc())

        if status_filter:
            stmt = stmt.where(WorkflowExecution.status == status_filter)

        result = await db.execute(stmt)
        workflows = result.scalars().all()

        return [WorkflowResponse.model_validate(workflow) for workflow in workflows]

    except Exception as e:
        logger.error(f"❌ Failed to list workflows: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve workflows"
        )


@router.get("/{workflow_id}", response_model=WorkflowResponse)
async def get_workflow(
    workflow_id: UUID,
    db: AsyncSession = Depends(get_db)
) -> WorkflowResponse:
    """Get a specific workflow by ID."""
    try:
        logger.info("🔍 Fetching workflow detail | id=%s", workflow_id)
        stmt = select(WorkflowExecution).where(WorkflowExecution.id == workflow_id)
        result = await db.execute(stmt)
        workflow = result.scalar_one_or_none()

        if not workflow:
            logger.warning("⚠️ Workflow not found | id=%s", workflow_id)
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Workflow with ID {workflow_id} not found"
            )

        response = WorkflowResponse.model_validate(workflow)
        logger.info(
            "📤 Workflow detail retrieved | id=%s status=%s step=%s",
            workflow_id,
            response.status,
            response.current_step,
        )
        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("❌ Failed to get workflow %s", workflow_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve workflow"
        )




@router.get("/token/{resume_token}", response_model=WorkflowResponse)
async def get_workflow_by_token(
    resume_token: str,
    db: AsyncSession = Depends(get_db)
) -> WorkflowResponse:
    """Get workflow by resume token."""
    try:
        stmt = select(WorkflowExecution).where(WorkflowExecution.resume_token == resume_token)
        result = await db.execute(stmt)
        workflow = result.scalar_one_or_none()

        if not workflow:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Invalid or expired resume token"
            )

        # Check if token is expired (tokens expire after 24 hours)
        from datetime import datetime, timedelta
        if workflow.created_at < datetime.utcnow() - timedelta(hours=24):
            raise HTTPException(
                status_code=status.HTTP_410_GONE,
                detail="Resume token has expired"
            )

        return WorkflowResponse.model_validate(workflow)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to get workflow by token: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve workflow"
        )


@router.post("/{workflow_id}/resume", response_model=WorkflowResponse)
async def resume_workflow(
    workflow_id: UUID,
    resume_data: WorkflowResumeRequest,
    db: AsyncSession = Depends(get_db)
) -> WorkflowResponse:
    """Resume a workflow with provided data."""
    try:
        stmt = select(WorkflowExecution).where(WorkflowExecution.id == workflow_id)
        result = await db.execute(stmt)
        workflow = result.scalar_one_or_none()

        if not workflow:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Workflow with ID {workflow_id} not found"
            )

        # Check if workflow can be resumed
        if workflow.status not in ["awaiting_completion", "sheet_url_provided"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Workflow cannot be resumed from status: {workflow.status}"
            )

        # Update workflow with resume data
        for field, value in resume_data.model_dump(exclude_unset=True).items():
            if field == "google_sheet_url":
                setattr(workflow, "sheet_url_input", value)
            else:
                setattr(workflow, field, value)

        # Update status based on what was provided
        if resume_data.google_sheet_url:
            workflow.status = "sheet_url_provided"

        await db.commit()
        await db.refresh(workflow)

        logger.info(f"✅ Resumed workflow: {workflow_id}")
        return WorkflowResponse.model_validate(workflow)

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"❌ Failed to resume workflow {workflow_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to resume workflow"
        )


@router.put("/{workflow_id}/status", response_model=WorkflowResponse)
async def update_workflow_status(
    workflow_id: UUID,
    status_update: WorkflowStatusUpdate,
    db: AsyncSession = Depends(get_db)
) -> WorkflowResponse:
    """Update workflow status."""
    try:
        stmt = select(WorkflowExecution).where(WorkflowExecution.id == workflow_id)
        result = await db.execute(stmt)
        workflow = result.scalar_one_or_none()

        if not workflow:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Workflow with ID {workflow_id} not found"
            )

        # Update status and progress
        workflow.status = status_update.status
        if status_update.progress is not None:
            workflow.progress = status_update.progress
        if status_update.error_message:
            workflow.error_message = status_update.error_message

        await db.commit()
        await db.refresh(workflow)

        logger.info(f"✅ Updated workflow status: {workflow_id} -> {status_update.status}")
        return WorkflowResponse.model_validate(workflow)

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"❌ Failed to update workflow status {workflow_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update workflow status"
        )


@router.delete("/{workflow_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_workflow(
    workflow_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Delete a workflow."""
    try:
        stmt = select(WorkflowExecution).where(WorkflowExecution.id == workflow_id)
        result = await db.execute(stmt)
        workflow = result.scalar_one_or_none()

        if not workflow:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Workflow with ID {workflow_id} not found"
            )

        await db.delete(workflow)
        await db.commit()

        logger.info(f"✅ Deleted workflow: {workflow_id}")

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"❌ Failed to delete workflow {workflow_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete workflow"
        )


# Sprint 2 Enhancement: Workflow Orchestration Endpoints

@router.post("/assessment-to-form")
async def create_assessment_form_workflow(
    request: AssessmentWorkflowRequest,
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Create and execute assessment-to-form workflow with orchestration."""
    try:
        logger.info("🚀 Starting assessment-to-form workflow orchestration")

        orchestrator = WorkflowOrchestrator()

        # Execute orchestrated workflow
        result = await orchestrator.execute_assessment_to_form_workflow(
            certification_profile_id=request.certification_profile_id,
            user_id=request.user_id,
            assessment_data=request.assessment_data,
            form_settings=request.form_settings
        )

        if result["success"]:
            logger.info(f"✅ Assessment-to-form workflow created successfully: {result['workflow_id']}")
        else:
            logger.error(f"❌ Assessment-to-form workflow failed: {result.get('error')}")

        return result

    except Exception as e:
        logger.error(f"❌ Assessment-to-form workflow error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Workflow execution failed: {str(e)}"
        )


@router.post("/{workflow_id}/force-ingest-responses")
async def force_ingest_responses(
    workflow_id: UUID,
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Manually trigger response ingestion for a workflow."""
    try:
        logger.info(f"🔄 Forcing response ingestion for workflow: {workflow_id}")

        ingestion_service = ResponseIngestionService()
        result = await ingestion_service.force_ingest_workflow_responses(workflow_id)

        if result["success"]:
            logger.info(f"✅ Response ingestion completed for workflow: {workflow_id}")
        else:
            logger.error(f"❌ Response ingestion failed for workflow: {workflow_id}")

        return result

    except Exception as e:
        logger.error(f"❌ Response ingestion error for workflow {workflow_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Response ingestion failed: {str(e)}"
        )


@router.post("/{workflow_id}/process-responses")
async def process_workflow_responses(
    workflow_id: UUID,
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Process collected responses and generate analysis."""
    try:
        logger.info(f"📊 Processing responses for workflow: {workflow_id}")

        orchestrator = WorkflowOrchestrator()
        result = await orchestrator.process_completed_responses(workflow_id)

        if result["success"]:
            logger.info(f"✅ Response processing completed for workflow: {workflow_id}")
        else:
            logger.error(f"❌ Response processing failed for workflow: {workflow_id}")

        return result

    except Exception as e:
        logger.error(f"❌ Response processing error for workflow {workflow_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Response processing failed: {str(e)}"
        )


@router.get("/{workflow_id}/orchestration-status")
async def get_orchestration_status(
    workflow_id: UUID,
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Get detailed orchestration status for a workflow."""
    try:
        logger.info(f"📋 Getting orchestration status for workflow: {workflow_id}")

        orchestrator = WorkflowOrchestrator()
        result = await orchestrator.get_workflow_status(workflow_id)

        return result

    except Exception as e:
        logger.error(f"❌ Error getting orchestration status for workflow {workflow_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get orchestration status: {str(e)}"
        )


@router.get("/active/orchestration")
async def list_active_orchestrated_workflows(
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """List all active workflows with orchestration details."""
    try:
        logger.info("📋 Listing active orchestrated workflows")

        orchestrator = WorkflowOrchestrator()
        result = await orchestrator.list_active_workflows()

        return result

    except Exception as e:
        logger.error(f"❌ Error listing active orchestrated workflows: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list active workflows: {str(e)}"
        )


@router.get("/ingestion/stats")
async def get_ingestion_statistics(
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Get response ingestion statistics."""
    try:
        logger.info("📊 Getting ingestion statistics")

        ingestion_service = ResponseIngestionService()
        result = await ingestion_service.get_ingestion_stats()

        return {
            "success": True,
            "stats": result
        }

    except Exception as e:
        logger.error(f"❌ Error getting ingestion statistics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get ingestion statistics: {str(e)}"
        )


@router.post("/{workflow_id}/trigger-orchestration")
async def trigger_workflow_orchestration(
    workflow_id: UUID,
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Trigger assessment-to-form orchestration for an existing workflow."""
    try:
        logger.info(f"🚀 Triggering orchestration for workflow: {workflow_id}")

        # Get the workflow
        stmt = select(WorkflowExecution).where(WorkflowExecution.id == workflow_id)
        result = await db.execute(stmt)
        workflow = result.scalar_one_or_none()

        if not workflow:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Workflow with ID {workflow_id} not found"
            )

        if workflow.workflow_type != "assessment_generation":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Orchestration only supported for assessment_generation workflows, got: {workflow.workflow_type}"
            )

        # Convert workflow parameters to assessment_data format
        assessment_data = {
            "questions": [
                {
                    "id": f"q{i+1}",
                    "question_text": f"Sample question {i+1} for {workflow.parameters.get('title', 'Assessment')}",
                    "question_type": "multiple_choice",
                    "options": ["A) Option 1", "B) Option 2", "C) Option 3", "D) Option 4"],
                    "correct_answer": "A"
                } for i in range(min(5, workflow.parameters.get('question_count', 24) // 5))
            ],
            "metadata": {
                "certification_name": workflow.parameters.get('title', 'Assessment'),
                "difficulty_level": workflow.parameters.get('difficulty_level', 'beginner'),
                "question_count": workflow.parameters.get('question_count', 24),
                "domain_distribution": workflow.parameters.get('domain_distribution', {})
            }
        }

        form_settings = FormSettings(
            collect_email=True,
            require_login=False
        )

        orchestrator = WorkflowOrchestrator()
        orchestration_result = await orchestrator.execute_assessment_to_form_workflow(
            certification_profile_id=workflow.certification_profile_id,
            user_id=workflow.user_id,
            assessment_data=assessment_data,
            form_settings=form_settings
        )

        if orchestration_result.get("success"):
            logger.info(f"✅ Orchestration successful for workflow {workflow_id}")
            return {
                "success": True,
                "message": "Workflow orchestration triggered successfully",
                "workflow_id": str(workflow_id),
                "orchestration_result": orchestration_result
            }
        else:
            logger.error(f"❌ Orchestration failed for workflow {workflow_id}: {orchestration_result.get('error')}")
            return {
                "success": False,
                "error": f"Orchestration failed: {orchestration_result.get('error')}",
                "workflow_id": str(workflow_id)
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error triggering orchestration for workflow {workflow_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to trigger orchestration: {str(e)}"
        )
