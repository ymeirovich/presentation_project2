"""Assessment generation and management API endpoints."""

import logging
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.assessment import Assessment
from src.schemas.assessment import (
    AssessmentCreate,
    AssessmentResponse,
    AssessmentUpdate
)
from src.service.database import get_db

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/", response_model=AssessmentResponse, status_code=status.HTTP_201_CREATED)
async def create_assessment(
    assessment_data: AssessmentCreate,
    db: AsyncSession = Depends(get_db)
) -> AssessmentResponse:
    """Create a new assessment."""
    try:
        assessment = Assessment(**assessment_data.model_dump())
        db.add(assessment)
        await db.commit()
        await db.refresh(assessment)

        logger.info(f"✅ Created assessment: {assessment.id}")
        return AssessmentResponse.model_validate(assessment)

    except Exception as e:
        await db.rollback()
        logger.error(f"❌ Failed to create assessment: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create assessment"
        )


@router.get("/", response_model=List[AssessmentResponse])
async def list_assessments(
    certification_id: Optional[UUID] = None,
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db)
) -> List[AssessmentResponse]:
    """List assessments with optional filtering."""
    try:
        stmt = select(Assessment).offset(skip).limit(limit).order_by(Assessment.created_at.desc())

        if certification_id:
            stmt = stmt.where(Assessment.certification_profile_id == certification_id)

        result = await db.execute(stmt)
        assessments = result.scalars().all()

        return [AssessmentResponse.model_validate(assessment) for assessment in assessments]

    except Exception as e:
        logger.error(f"❌ Failed to list assessments: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve assessments"
        )


@router.get("/{assessment_id}", response_model=AssessmentResponse)
async def get_assessment(
    assessment_id: UUID,
    db: AsyncSession = Depends(get_db)
) -> AssessmentResponse:
    """Get a specific assessment by ID."""
    try:
        stmt = select(Assessment).where(Assessment.id == assessment_id)
        result = await db.execute(stmt)
        assessment = result.scalar_one_or_none()

        if not assessment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Assessment with ID {assessment_id} not found"
            )

        return AssessmentResponse.model_validate(assessment)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to get assessment {assessment_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve assessment"
        )


@router.put("/{assessment_id}", response_model=AssessmentResponse)
async def update_assessment(
    assessment_id: UUID,
    assessment_data: AssessmentUpdate,
    db: AsyncSession = Depends(get_db)
) -> AssessmentResponse:
    """Update an existing assessment."""
    try:
        stmt = select(Assessment).where(Assessment.id == assessment_id)
        result = await db.execute(stmt)
        assessment = result.scalar_one_or_none()

        if not assessment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Assessment with ID {assessment_id} not found"
            )

        # Update assessment fields
        update_data = assessment_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(assessment, field, value)

        await db.commit()
        await db.refresh(assessment)

        logger.info(f"✅ Updated assessment: {assessment.id}")
        return AssessmentResponse.model_validate(assessment)

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"❌ Failed to update assessment {assessment_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update assessment"
        )


@router.delete("/{assessment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_assessment(
    assessment_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Delete an assessment."""
    try:
        stmt = select(Assessment).where(Assessment.id == assessment_id)
        result = await db.execute(stmt)
        assessment = result.scalar_one_or_none()

        if not assessment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Assessment with ID {assessment_id} not found"
            )

        await db.delete(assessment)
        await db.commit()

        logger.info(f"✅ Deleted assessment: {assessment_id}")

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"❌ Failed to delete assessment {assessment_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete assessment"
        )