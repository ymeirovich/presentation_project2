"""Certification profile management API endpoints."""

import logging
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.certification import CertificationProfile
from src.schemas.certification import (
    CertificationProfileCreate,
    CertificationProfileResponse,
    CertificationProfileUpdate
)
from src.service.database import get_db

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/", response_model=CertificationProfileResponse, status_code=status.HTTP_201_CREATED)
async def create_certification_profile(
    profile_data: CertificationProfileCreate,
    db: AsyncSession = Depends(get_db)
) -> CertificationProfileResponse:
    """Create a new certification profile."""
    try:
        # Check if profile already exists
        stmt = select(CertificationProfile).where(
            CertificationProfile.name == profile_data.name,
            CertificationProfile.version == profile_data.version
        )
        result = await db.execute(stmt)
        existing_profile = result.scalar_one_or_none()

        if existing_profile:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Certification profile '{profile_data.name} v{profile_data.version}' already exists"
            )

        # Create new profile
        profile = CertificationProfile(**profile_data.model_dump())
        db.add(profile)
        await db.commit()
        await db.refresh(profile)

        logger.info(f"✅ Created certification profile: {profile.name} v{profile.version}")
        return CertificationProfileResponse.model_validate(profile)

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"❌ Failed to create certification profile: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create certification profile"
        )


@router.get("/", response_model=List[CertificationProfileResponse])
async def list_certification_profiles(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db)
) -> List[CertificationProfileResponse]:
    """List all certification profiles with pagination."""
    try:
        stmt = select(CertificationProfile).offset(skip).limit(limit).order_by(CertificationProfile.created_at.desc())
        result = await db.execute(stmt)
        profiles = result.scalars().all()

        return [CertificationProfileResponse.model_validate(profile) for profile in profiles]

    except Exception as e:
        logger.error(f"❌ Failed to list certification profiles: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve certification profiles"
        )


@router.get("/{profile_id}", response_model=CertificationProfileResponse)
async def get_certification_profile(
    profile_id: UUID,
    db: AsyncSession = Depends(get_db)
) -> CertificationProfileResponse:
    """Get a specific certification profile by ID."""
    try:
        stmt = select(CertificationProfile).where(CertificationProfile.id == profile_id)
        result = await db.execute(stmt)
        profile = result.scalar_one_or_none()

        if not profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Certification profile with ID {profile_id} not found"
            )

        return CertificationProfileResponse.model_validate(profile)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to get certification profile {profile_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve certification profile"
        )


@router.put("/{profile_id}", response_model=CertificationProfileResponse)
async def update_certification_profile(
    profile_id: UUID,
    profile_data: CertificationProfileUpdate,
    db: AsyncSession = Depends(get_db)
) -> CertificationProfileResponse:
    """Update an existing certification profile."""
    try:
        # Get existing profile
        stmt = select(CertificationProfile).where(CertificationProfile.id == profile_id)
        result = await db.execute(stmt)
        profile = result.scalar_one_or_none()

        if not profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Certification profile with ID {profile_id} not found"
            )

        # Update profile fields
        update_data = profile_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(profile, field, value)

        await db.commit()
        await db.refresh(profile)

        logger.info(f"✅ Updated certification profile: {profile.name} v{profile.version}")
        return CertificationProfileResponse.model_validate(profile)

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"❌ Failed to update certification profile {profile_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update certification profile"
        )


@router.delete("/{profile_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_certification_profile(
    profile_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Delete a certification profile."""
    try:
        # Get existing profile
        stmt = select(CertificationProfile).where(CertificationProfile.id == profile_id)
        result = await db.execute(stmt)
        profile = result.scalar_one_or_none()

        if not profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Certification profile with ID {profile_id} not found"
            )

        # Delete profile
        await db.delete(profile)
        await db.commit()

        logger.info(f"✅ Deleted certification profile: {profile.name} v{profile.version}")

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"❌ Failed to delete certification profile {profile_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete certification profile"
        )


@router.get("/search/{certification_name}", response_model=List[CertificationProfileResponse])
async def search_certification_profiles(
    certification_name: str,
    db: AsyncSession = Depends(get_db)
) -> List[CertificationProfileResponse]:
    """Search certification profiles by name."""
    try:
        stmt = select(CertificationProfile).where(
            CertificationProfile.name.ilike(f"%{certification_name}%")
        ).order_by(CertificationProfile.created_at.desc())
        result = await db.execute(stmt)
        profiles = result.scalars().all()

        return [CertificationProfileResponse.model_validate(profile) for profile in profiles]

    except Exception as e:
        logger.error(f"❌ Failed to search certification profiles: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to search certification profiles"
        )