"""Certification profile management API endpoints."""

import logging
from datetime import datetime
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

        # Convert API schema to database schema
        # Transform exam_domains from API format (with topics) to DB format (with subdomains/skills_measured)
        db_exam_domains = []
        for domain in profile_data.exam_domains:
            db_domain = {
                'name': domain.name,
                'weight_percentage': domain.weight_percentage,
                'subdomains': domain.topics[:len(domain.topics)//2] if domain.topics else [],  # Split topics into subdomains
                'skills_measured': domain.topics[len(domain.topics)//2:] if domain.topics else []  # and skills_measured
            }
            db_exam_domains.append(db_domain)

        # Store additional form fields in assessment_template as metadata
        assessment_template = getattr(profile_data, 'assessment_template', None) or {}

        # Add form metadata to assessment_template
        if not isinstance(assessment_template, dict):
            assessment_template = {}

        assessment_template['_metadata'] = {
            'provider': profile_data.provider,
            'description': getattr(profile_data, 'description', None),
            'exam_code': getattr(profile_data, 'exam_code', None),
            'passing_score': getattr(profile_data, 'passing_score', None),
            'exam_duration_minutes': getattr(profile_data, 'exam_duration_minutes', None),
            'question_count': getattr(profile_data, 'question_count', None),
            'prerequisites': getattr(profile_data, 'prerequisites', []),
            'recommended_experience': getattr(profile_data, 'recommended_experience', None),
            'is_active': getattr(profile_data, 'is_active', True)
        }

        # Create profile data for database model (only include fields that exist in DB model)
        db_profile_data = {
            'name': profile_data.name,
            'version': profile_data.version,
            'exam_domains': db_exam_domains,
            'knowledge_base_path': f"knowledge_base/{profile_data.name.lower().replace(' ', '_')}_v{profile_data.version}",
            'assessment_template': assessment_template
        }

        profile = CertificationProfile(**db_profile_data)
        db.add(profile)
        await db.commit()
        await db.refresh(profile)

        logger.info(f"✅ Created certification profile: {profile.name} v{profile.version}")

        # Convert database model back to API schema for response
        response_domains = []
        for domain in profile.exam_domains:
            api_domain = {
                'name': domain['name'],
                'weight_percentage': domain['weight_percentage'],
                'topics': (domain.get('subdomains', []) + domain.get('skills_measured', []))  # Merge back into topics
            }
            response_domains.append(api_domain)

        # Extract metadata from assessment_template
        metadata = {}
        if profile.assessment_template and isinstance(profile.assessment_template, dict):
            metadata = profile.assessment_template.get('_metadata', {})

        response_data = {
            'id': profile.id,
            'name': profile.name,
            'version': profile.version,
            'provider': metadata.get('provider', 'Unknown'),
            'description': metadata.get('description'),
            'exam_code': metadata.get('exam_code'),
            'passing_score': metadata.get('passing_score'),
            'exam_duration_minutes': metadata.get('exam_duration_minutes'),
            'question_count': metadata.get('question_count'),
            'exam_domains': response_domains,
            'prerequisites': metadata.get('prerequisites', []),
            'recommended_experience': metadata.get('recommended_experience'),
            'is_active': metadata.get('is_active', True),
            'created_at': profile.created_at,
            'updated_at': profile.updated_at
        }

        return CertificationProfileResponse(**response_data)

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"❌ Failed to create certification profile: {e}")
        logger.error(f"Error type: {type(e)}")
        logger.error(f"Error args: {e.args}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create certification profile: {str(e)}"
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

        # Convert database models to API schema
        api_profiles = []
        for profile in profiles:
            response_domains = []
            for domain in profile.exam_domains:
                api_domain = {
                    'name': domain['name'],
                    'weight_percentage': domain['weight_percentage'],
                    'topics': (domain.get('subdomains', []) + domain.get('skills_measured', []))
                }
                response_domains.append(api_domain)

            # Extract metadata from assessment_template
            metadata = {}
            if profile.assessment_template and isinstance(profile.assessment_template, dict):
                metadata = profile.assessment_template.get('_metadata', {})

            response_data = {
                'id': profile.id,
                'name': profile.name,
                'version': profile.version,
                'provider': metadata.get('provider', 'Unknown'),
                'description': metadata.get('description'),
                'exam_code': metadata.get('exam_code'),
                'passing_score': metadata.get('passing_score'),
                'exam_duration_minutes': metadata.get('exam_duration_minutes'),
                'question_count': metadata.get('question_count'),
                'exam_domains': response_domains,
                'prerequisites': metadata.get('prerequisites', []),
                'recommended_experience': metadata.get('recommended_experience'),
                'is_active': metadata.get('is_active', True),
                'created_at': profile.created_at,
                'updated_at': profile.updated_at
            }
            api_profiles.append(CertificationProfileResponse(**response_data))

        return api_profiles

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

        # Convert database model to API schema
        response_domains = []
        for domain in profile.exam_domains:
            api_domain = {
                'name': domain['name'],
                'weight_percentage': domain['weight_percentage'],
                'topics': (domain.get('subdomains', []) + domain.get('skills_measured', []))
            }
            response_domains.append(api_domain)

        # Extract metadata from assessment_template
        metadata = {}
        if profile.assessment_template and isinstance(profile.assessment_template, dict):
            metadata = profile.assessment_template.get('_metadata', {})

        response_data = {
            'id': profile.id,
            'name': profile.name,
            'version': profile.version,
            'provider': metadata.get('provider', 'Unknown'),
            'description': metadata.get('description'),
            'exam_code': metadata.get('exam_code'),
            'passing_score': metadata.get('passing_score'),
            'exam_duration_minutes': metadata.get('exam_duration_minutes'),
            'question_count': metadata.get('question_count'),
            'exam_domains': response_domains,
            'prerequisites': metadata.get('prerequisites', []),
            'recommended_experience': metadata.get('recommended_experience'),
            'is_active': metadata.get('is_active', True),
            'created_at': profile.created_at,
            'updated_at': profile.updated_at
        }

        return CertificationProfileResponse(**response_data)

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


@router.post("/{profile_id}/duplicate", response_model=CertificationProfileResponse, status_code=status.HTTP_201_CREATED)
async def duplicate_certification_profile(
    profile_id: UUID,
    new_name: str,
    new_version: str,
    db: AsyncSession = Depends(get_db)
) -> CertificationProfileResponse:
    """Duplicate an existing certification profile with new name/version."""
    try:
        # Get source profile
        stmt = select(CertificationProfile).where(CertificationProfile.id == profile_id)
        result = await db.execute(stmt)
        source_profile = result.scalar_one_or_none()

        if not source_profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Source certification profile with ID {profile_id} not found"
            )

        # Check if new profile already exists
        stmt = select(CertificationProfile).where(
            CertificationProfile.name == new_name,
            CertificationProfile.version == new_version
        )
        result = await db.execute(stmt)
        existing_profile = result.scalar_one_or_none()

        if existing_profile:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Certification profile '{new_name} v{new_version}' already exists"
            )

        # Create duplicate profile
        new_profile = CertificationProfile(
            name=new_name,
            version=new_version,
            exam_domains=source_profile.exam_domains,
            knowledge_base_path=f"knowledge_base/{new_name.lower().replace(' ', '_')}_v{new_version}",
            assessment_template=source_profile.assessment_template
        )

        db.add(new_profile)
        await db.commit()
        await db.refresh(new_profile)

        logger.info(f"✅ Duplicated certification profile: {new_name} v{new_version} from {source_profile.name}")
        return CertificationProfileResponse.model_validate(new_profile)

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"❌ Failed to duplicate certification profile: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to duplicate certification profile"
        )


@router.get("/{profile_id}/statistics", response_model=dict)
async def get_certification_profile_statistics(
    profile_id: UUID,
    db: AsyncSession = Depends(get_db)
) -> dict:
    """Get statistics for a certification profile (assessments, documents, etc.)."""
    try:
        # Get profile
        stmt = select(CertificationProfile).where(CertificationProfile.id == profile_id)
        result = await db.execute(stmt)
        profile = result.scalar_one_or_none()

        if not profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Certification profile with ID {profile_id} not found"
            )

        # TODO: Add actual statistics queries when other models are available
        # For now, return basic profile information

        statistics = {
            "profile_info": {
                "name": profile.name,
                "version": profile.version,
                "created_at": profile.created_at,
                "updated_at": profile.updated_at
            },
            "exam_domains": {
                "total_domains": len(profile.exam_domains),
                "domain_breakdown": [
                    {
                        "domain": domain["name"],
                        "weight": domain["weight_percentage"],
                        "subdomains_count": len(domain.get("subdomains", [])),
                        "skills_count": len(domain.get("skills_measured", []))
                    }
                    for domain in profile.exam_domains
                ]
            },
            "knowledge_base": {
                "path": profile.knowledge_base_path,
                "documents_count": 0,  # TODO: Query actual document count
                "processing_status": "ready"  # TODO: Query actual status
            },
            "assessments": {
                "total_assessments": 0,  # TODO: Query assessment count
                "completed_assessments": 0,  # TODO: Query completed assessments
                "average_score": 0.0  # TODO: Calculate average score
            },
            "gap_analysis": {
                "total_analyses": 0,  # TODO: Query gap analysis count
                "common_gaps": [],  # TODO: Identify common gaps
                "improvement_trends": []  # TODO: Track improvement over time
            }
        }

        return statistics

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to get certification profile statistics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve certification profile statistics"
        )


@router.post("/{profile_id}/validate", response_model=dict)
async def validate_certification_profile(
    profile_id: UUID,
    db: AsyncSession = Depends(get_db)
) -> dict:
    """Validate a certification profile for completeness and correctness."""
    try:
        # Get profile
        stmt = select(CertificationProfile).where(CertificationProfile.id == profile_id)
        result = await db.execute(stmt)
        profile = result.scalar_one_or_none()

        if not profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Certification profile with ID {profile_id} not found"
            )

        validation_results = {
            "profile_id": str(profile_id),
            "validation_timestamp": datetime.now().isoformat(),
            "is_valid": True,
            "warnings": [],
            "errors": [],
            "recommendations": []
        }

        # Validate exam domains
        total_weight = sum(domain["weight_percentage"] for domain in profile.exam_domains)
        if total_weight != 100:
            validation_results["is_valid"] = False
            validation_results["errors"].append(f"Domain weights sum to {total_weight}%, must equal 100%")

        # Check for empty domains
        for domain in profile.exam_domains:
            if not domain.get("name"):
                validation_results["is_valid"] = False
                validation_results["errors"].append("Domain name cannot be empty")

            if domain.get("weight_percentage", 0) <= 0:
                validation_results["is_valid"] = False
                validation_results["errors"].append(f"Domain '{domain.get('name', 'Unknown')}' must have weight > 0%")

            if not domain.get("subdomains"):
                validation_results["warnings"].append(f"Domain '{domain.get('name', 'Unknown')}' has no subdomains defined")

            if not domain.get("skills_measured"):
                validation_results["warnings"].append(f"Domain '{domain.get('name', 'Unknown')}' has no skills measured defined")

        # Validate knowledge base path
        if not profile.knowledge_base_path:
            validation_results["is_valid"] = False
            validation_results["errors"].append("Knowledge base path is required")

        # Add recommendations
        if len(profile.exam_domains) < 3:
            validation_results["recommendations"].append("Consider adding more exam domains for comprehensive coverage")

        if not profile.assessment_template:
            validation_results["recommendations"].append("Adding an assessment template will improve question generation")

        return validation_results

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to validate certification profile: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to validate certification profile"
        )