"""Async workflow management API endpoints."""

import logging
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.workflow import WorkflowExecution
from src.schemas.workflow import (
    WorkflowCreate,
    WorkflowResponse,
    WorkflowResumeRequest,
    WorkflowStatusUpdate
)
from src.service.database import get_db

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/", response_model=WorkflowResponse, status_code=status.HTTP_201_CREATED)
async def create_workflow(
    workflow_data: WorkflowCreate,
    db: AsyncSession = Depends(get_db)
) -> WorkflowResponse:
    """Create a new async workflow."""
    try:
        workflow = WorkflowExecution(**workflow_data.model_dump())
        db.add(workflow)
        await db.commit()
        await db.refresh(workflow)

        logger.info(f"✅ Created workflow: {workflow.id}")
        return WorkflowResponse.model_validate(workflow)

    except Exception as e:
        await db.rollback()
        logger.error(f"❌ Failed to create workflow: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create workflow"
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
        stmt = select(WorkflowExecution).where(WorkflowExecution.id == workflow_id)
        result = await db.execute(stmt)
        workflow = result.scalar_one_or_none()

        if not workflow:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Workflow with ID {workflow_id} not found"
            )

        return WorkflowResponse.model_validate(workflow)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to get workflow {workflow_id}: {e}")
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