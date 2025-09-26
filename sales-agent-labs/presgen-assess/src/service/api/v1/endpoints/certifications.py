"""Certification profile management API endpoints."""

import logging
import json
from datetime import datetime
from typing import List, Dict, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.certification import CertificationProfile
from src.schemas.certification import (
    CertificationProfileCreate,
    CertificationProfileResponse,
    CertificationProfileUpdate
)
from src.service.database import get_db

# Import enhanced logging
from src.common.logging_config import get_certification_logger, get_database_logger

logger = get_certification_logger()
db_logger = get_database_logger()

def log_request_details(endpoint: str, method: str, profile_id: str = None, data: Any = None):
    """Log detailed request information for debugging."""
    log_data = {
        "endpoint": endpoint,
        "method": method,
        "profile_id": profile_id,
        "timestamp": datetime.now().isoformat()
    }
    if data:
        # Safely serialize data for logging
        try:
            if hasattr(data, 'model_dump'):
                log_data["request_data"] = data.model_dump()
            elif hasattr(data, 'dict'):
                log_data["request_data"] = data.dict()
            else:
                log_data["request_data"] = str(data)
        except Exception as e:
            log_data["request_data"] = f"<serialization_error: {str(e)}>"

    logger.info(f"📥 REQUEST: {json.dumps(log_data, indent=2)}")

def log_response_details(endpoint: str, profile_id: str = None, response_data: Any = None, status_code: int = 200):
    """Log detailed response information for debugging."""
    log_data = {
        "endpoint": endpoint,
        "profile_id": profile_id,
        "status_code": status_code,
        "timestamp": datetime.now().isoformat()
    }
    if response_data:
        try:
            if hasattr(response_data, 'model_dump'):
                # For detailed response logging, include key fields but limit size
                data_dict = response_data.model_dump()
                log_data["response_summary"] = {
                    "id": str(data_dict.get("id")) if data_dict.get("id") else None,
                    "name": data_dict.get("name"),
                    "version": data_dict.get("version"),
                    "fields_count": len(data_dict.keys()),
                    "has_prompts": {
                        "assessment_prompt": bool(data_dict.get("assessment_prompt")),
                        "presentation_prompt": bool(data_dict.get("presentation_prompt")),
                        "gap_analysis_prompt": bool(data_dict.get("gap_analysis_prompt"))
                    }
                }
            elif hasattr(response_data, 'dict'):
                data_dict = response_data.dict()
                log_data["response_summary"] = {
                    "fields_count": len(data_dict.keys()),
                    "data_type": type(response_data).__name__
                }
            elif isinstance(response_data, list):
                log_data["response_summary"] = {
                    "list_length": len(response_data),
                    "first_item_type": type(response_data[0]).__name__ if response_data else "empty"
                }
            else:
                log_data["response_summary"] = str(response_data)[:200]
        except Exception as e:
            log_data["response_data"] = f"<serialization_error: {str(e)}>"

    logger.info(f"📤 RESPONSE: {json.dumps(log_data, indent=2)}")

def log_database_operation(operation: str, table: str, profile_id: str = None, data: Dict = None):
    """Log database operations for debugging."""
    log_data = {
        "operation": operation,
        "table": table,
        "profile_id": profile_id,
        "timestamp": datetime.now().isoformat()
    }
    if data:
        log_data["data_summary"] = {
            "name": data.get("name"),
            "version": data.get("version"),
            "fields_present": list(data.keys()) if isinstance(data, dict) else "non_dict_data",
            # Add prompt-related field logging
            "prompt_fields": {
                "assessment_prompt": data.get("assessment_prompt", "NOT_SET")[:100] + "..." if data.get("assessment_prompt") and len(str(data.get("assessment_prompt"))) > 100 else data.get("assessment_prompt", "NOT_SET"),
                "presentation_prompt": data.get("presentation_prompt", "NOT_SET")[:100] + "..." if data.get("presentation_prompt") and len(str(data.get("presentation_prompt"))) > 100 else data.get("presentation_prompt", "NOT_SET"),
                "gap_analysis_prompt": data.get("gap_analysis_prompt", "NOT_SET")[:100] + "..." if data.get("gap_analysis_prompt") and len(str(data.get("gap_analysis_prompt"))) > 100 else data.get("gap_analysis_prompt", "NOT_SET")
            }
        }

    db_logger.info(f"💾 DATABASE: {json.dumps(log_data, indent=2)}")

def log_data_transformation(step: str, input_data: Any = None, output_data: Any = None, profile_id: str = None):
    """Log data transformation steps for debugging."""
    log_data = {
        "transformation_step": step,
        "profile_id": profile_id,
        "timestamp": datetime.now().isoformat()
    }

    try:
        if input_data:
            log_data["input_summary"] = {
                "type": type(input_data).__name__,
                "keys": list(input_data.keys()) if isinstance(input_data, dict) else "non_dict",
                "length": len(input_data) if hasattr(input_data, '__len__') else "no_length"
            }

        if output_data:
            log_data["output_summary"] = {
                "type": type(output_data).__name__,
                "keys": list(output_data.keys()) if isinstance(output_data, dict) else "non_dict",
                "length": len(output_data) if hasattr(output_data, '__len__') else "no_length"
            }
    except Exception as e:
        log_data["transformation_error"] = str(e)

    logger.info(f"🔄 TRANSFORM: {json.dumps(log_data, indent=2)}")

def log_prompt_values(step: str, profile_id: str, prompts: Dict[str, Any], source: str = "unknown"):
    """Log detailed prompt values for debugging persistent prompt issues."""
    log_data = {
        "step": step,
        "profile_id": profile_id,
        "source": source,
        "timestamp": datetime.now().isoformat(),
        "prompt_details": {
            "assessment_prompt": {
                "has_value": bool(prompts.get("assessment_prompt")),
                "length": len(str(prompts.get("assessment_prompt", ""))) if prompts.get("assessment_prompt") else 0,
                "preview": str(prompts.get("assessment_prompt", ""))[:200] + "..." if prompts.get("assessment_prompt") and len(str(prompts.get("assessment_prompt"))) > 200 else str(prompts.get("assessment_prompt", "")),
                "type": type(prompts.get("assessment_prompt")).__name__
            },
            "presentation_prompt": {
                "has_value": bool(prompts.get("presentation_prompt")),
                "length": len(str(prompts.get("presentation_prompt", ""))) if prompts.get("presentation_prompt") else 0,
                "preview": str(prompts.get("presentation_prompt", ""))[:200] + "..." if prompts.get("presentation_prompt") and len(str(prompts.get("presentation_prompt"))) > 200 else str(prompts.get("presentation_prompt", "")),
                "type": type(prompts.get("presentation_prompt")).__name__
            },
            "gap_analysis_prompt": {
                "has_value": bool(prompts.get("gap_analysis_prompt")),
                "length": len(str(prompts.get("gap_analysis_prompt", ""))) if prompts.get("gap_analysis_prompt") else 0,
                "preview": str(prompts.get("gap_analysis_prompt", ""))[:200] + "..." if prompts.get("gap_analysis_prompt") and len(str(prompts.get("gap_analysis_prompt"))) > 200 else str(prompts.get("gap_analysis_prompt", "")),
                "type": type(prompts.get("gap_analysis_prompt")).__name__
            }
        }
    }

    logger.info(f"🎯 PROMPTS: {json.dumps(log_data, indent=2)}")

router = APIRouter()


@router.post("/", response_model=CertificationProfileResponse, status_code=status.HTTP_201_CREATED)
async def create_certification_profile(
    profile_data: CertificationProfileCreate,
    db: AsyncSession = Depends(get_db)
) -> CertificationProfileResponse:
    """Create a new certification profile."""

    # Log incoming request
    log_request_details("CREATE /", "POST", data=profile_data)
    logger.info(f"🆕 Creating new certification profile: {profile_data.name} v{profile_data.version}")

    try:
        # Check if profile already exists
        log_database_operation("SELECT", "certification_profiles", data={"name": profile_data.name, "version": profile_data.version})
        stmt = select(CertificationProfile).where(
            CertificationProfile.name == profile_data.name,
            CertificationProfile.version == profile_data.version
        )
        result = await db.execute(stmt)
        existing_profile = result.scalar_one_or_none()

        if existing_profile:
            logger.warning(f"❌ Profile creation failed - already exists: {profile_data.name} v{profile_data.version}")
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Certification profile '{profile_data.name} v{profile_data.version}' already exists"
            )

        logger.info(f"✅ Profile uniqueness check passed - proceeding with creation")

        # Convert API schema to database schema
        # Transform exam_domains from API format (with topics) to DB format (with subdomains/skills_measured)
        log_data_transformation("API_to_DB_exam_domains", input_data=profile_data.exam_domains)

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
            'updated_at': profile.updated_at,
            # Include prompt fields from database columns
            'assessment_prompt': profile.assessment_prompt,
            'presentation_prompt': profile.presentation_prompt,
            'gap_analysis_prompt': profile.gap_analysis_prompt,
            'resource_binding_enabled': profile.resource_binding_enabled
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
    # Log incoming request
    log_request_details("LIST /", "GET", data={"skip": skip, "limit": limit})
    logger.info(f"📋 Listing certification profiles: skip={skip}, limit={limit}")

    try:
        # Log database operation
        log_database_operation("SELECT", "certification_profiles", data={"skip": skip, "limit": limit})

        stmt = select(CertificationProfile).offset(skip).limit(limit).order_by(CertificationProfile.created_at.desc())
        result = await db.execute(stmt)
        profiles = result.scalars().all()

        logger.info(f"📋 Retrieved {len(profiles)} certification profiles")

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
                'updated_at': profile.updated_at,
                # Include prompt fields from database columns
                'assessment_prompt': profile.assessment_prompt,
                'presentation_prompt': profile.presentation_prompt,
                'gap_analysis_prompt': profile.gap_analysis_prompt,
                'resource_binding_enabled': profile.resource_binding_enabled
            }
            api_profiles.append(CertificationProfileResponse(**response_data))

        # Log successful response
        log_response_details("LIST /", response_data=api_profiles, status_code=200)
        logger.info(f"✅ Successfully returned {len(api_profiles)} certification profiles")

        return api_profiles

    except Exception as e:
        logger.error(f"❌ Failed to list certification profiles: {e}")
        logger.error(f"Error type: {type(e)}")
        logger.error(f"Error args: {e.args}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
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
    # Log incoming request
    log_request_details("GET /{profile_id}", "GET", profile_id=str(profile_id))
    logger.info(f"🔍 Getting certification profile: {profile_id}")

    try:
        # Log database operation
        log_database_operation("SELECT", "certification_profiles", profile_id=str(profile_id))

        stmt = select(CertificationProfile).where(CertificationProfile.id == profile_id)
        result = await db.execute(stmt)
        profile = result.scalar_one_or_none()

        if not profile:
            logger.warning(f"❌ Profile not found: {profile_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Certification profile with ID {profile_id} not found"
            )

        logger.info(f"✅ Found certification profile: {profile.name} v{profile.version}")

        # Log raw database values for prompt fields
        db_prompts = {
            "assessment_prompt": profile.assessment_prompt,
            "presentation_prompt": profile.presentation_prompt,
            "gap_analysis_prompt": profile.gap_analysis_prompt
        }
        log_prompt_values("GET_from_database", str(profile_id), db_prompts, "database_columns")

        # Also log any prompts from assessment_template
        template_prompts = {}
        if profile.assessment_template and isinstance(profile.assessment_template, dict):
            chromadb_prompts = profile.assessment_template.get('_chromadb_prompts', {})
            template_prompts = {
                "assessment_prompt": chromadb_prompts.get('assessment_prompt'),
                "presentation_prompt": chromadb_prompts.get('presentation_prompt'),
                "gap_analysis_prompt": chromadb_prompts.get('gap_analysis_prompt')
            }
            log_prompt_values("GET_from_template", str(profile_id), template_prompts, "assessment_template._chromadb_prompts")

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
            'updated_at': profile.updated_at,
            # ADD MISSING PROMPT FIELDS FROM DATABASE
            'assessment_prompt': profile.assessment_prompt,
            'presentation_prompt': profile.presentation_prompt,
            'gap_analysis_prompt': profile.gap_analysis_prompt,
            'resource_binding_enabled': profile.resource_binding_enabled
        }

        # Log what prompts are being included in API response
        final_prompts = {
            "assessment_prompt": response_data.get("assessment_prompt"),
            "presentation_prompt": response_data.get("presentation_prompt"),
            "gap_analysis_prompt": response_data.get("gap_analysis_prompt")
        }
        log_prompt_values("GET_response_to_ui", str(profile_id), final_prompts, "api_response")

        response = CertificationProfileResponse(**response_data)

        # Log successful response
        log_response_details("GET /{profile_id}", profile_id=str(profile_id), response_data=response, status_code=200)
        logger.info(f"✅ Successfully returned certification profile: {profile.name} v{profile.version}")

        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to get certification profile {profile_id}: {e}")
        logger.error(f"Error type: {type(e)}")
        logger.error(f"Error args: {e.args}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
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
    # Log incoming request
    log_request_details("PUT /{profile_id}", "PUT", profile_id=str(profile_id), data=profile_data)
    logger.info(f"✏️ Updating certification profile: {profile_id}")

    try:
        # Get existing profile
        log_database_operation("SELECT", "certification_profiles", profile_id=str(profile_id))

        stmt = select(CertificationProfile).where(CertificationProfile.id == profile_id)
        result = await db.execute(stmt)
        profile = result.scalar_one_or_none()

        if not profile:
            logger.warning(f"❌ Profile not found for update: {profile_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Certification profile with ID {profile_id} not found"
            )

        logger.info(f"✅ Found profile for update: {profile.name} v{profile.version}")

        # Log data transformation
        update_data = profile_data.model_dump(exclude_unset=True)

        # Capture which fields survived Pydantic validation to highlight drops
        validated_fields = set(update_data.keys())
        expected_prompt_fields = {"assessment_prompt", "presentation_prompt", "gap_analysis_prompt"}
        missing_expected = sorted(expected_prompt_fields - validated_fields)
        if missing_expected:
            logger.warning(
                "⚠️ Prompt fields missing from validated payload (likely dropped before persistence): %s",
                missing_expected
            )

        log_data_transformation("UPDATE_data_preparation", input_data=update_data, profile_id=str(profile_id))

        # Update profile fields
        logger.info(f"📝 Updating {len(update_data)} fields: {list(update_data.keys())}")
        for field, value in update_data.items():
            old_value = getattr(profile, field, None)
            setattr(profile, field, value)
            logger.debug(f"🔄 Field '{field}': {old_value} -> {value}")

        # Log database operation
        log_database_operation("UPDATE", "certification_profiles", profile_id=str(profile_id), data=update_data)

        await db.commit()
        await db.refresh(profile)

        logger.info(f"✅ Updated certification profile: {profile.name} v{profile.version}")

        # Convert database model back to API schema for response (same as CREATE endpoint)
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

        # Extract prompt values from both database columns and assessment_template
        prompts = profile.assessment_template.get('_chromadb_prompts', {}) if profile.assessment_template else {}

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
            'updated_at': profile.updated_at,
            # ADD MISSING PROMPT FIELDS FROM DATABASE COLUMNS
            'assessment_prompt': profile.assessment_prompt,
            'presentation_prompt': profile.presentation_prompt,
            'gap_analysis_prompt': profile.gap_analysis_prompt,
            'resource_binding_enabled': profile.resource_binding_enabled
        }

        # Log prompt values being returned to UI
        log_prompt_values(
            step="update_response_construction",
            profile_id=str(profile.id),
            prompts={
                'assessment_prompt': profile.assessment_prompt,
                'presentation_prompt': profile.presentation_prompt,
                'gap_analysis_prompt': profile.gap_analysis_prompt
            },
            source="database_columns"
        )

        response = CertificationProfileResponse(**response_data)

        # Log successful response
        log_response_details("PUT /{profile_id}", profile_id=str(profile_id), response_data=response, status_code=200)
        logger.info(f"✅ Successfully returned updated profile: {profile.name} v{profile.version}")

        return response

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"❌ Failed to update certification profile {profile_id}: {e}")
        logger.error(f"Error type: {type(e)}")
        logger.error(f"Error args: {e.args}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
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
    # Log incoming request
    log_request_details("DELETE /{profile_id}", "DELETE", profile_id=str(profile_id))
    logger.info(f"🗑️ Deleting certification profile: {profile_id}")

    try:
        # Get existing profile
        log_database_operation("SELECT", "certification_profiles", profile_id=str(profile_id))

        stmt = select(CertificationProfile).where(CertificationProfile.id == profile_id)
        result = await db.execute(stmt)
        profile = result.scalar_one_or_none()

        if not profile:
            logger.warning(f"❌ Profile not found for deletion: {profile_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Certification profile with ID {profile_id} not found"
            )

        logger.info(f"✅ Found profile for deletion: {profile.name} v{profile.version}")

        # Store profile info for logging before deletion
        profile_name = profile.name
        profile_version = profile.version

        # Delete profile
        log_database_operation("DELETE", "certification_profiles", profile_id=str(profile_id), data={"name": profile_name, "version": profile_version})

        await db.delete(profile)
        await db.commit()

        logger.info(f"✅ Deleted certification profile: {profile_name} v{profile_version}")

        # Log successful response
        log_response_details("DELETE /{profile_id}", profile_id=str(profile_id), status_code=204)
        logger.info(f"✅ Successfully deleted profile: {profile_name} v{profile_version}")

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"❌ Failed to delete certification profile {profile_id}: {e}")
        logger.error(f"Error type: {type(e)}")
        logger.error(f"Error args: {e.args}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
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
    # Log incoming request
    log_request_details("SEARCH /search/{certification_name}", "GET", data={"search_term": certification_name})
    logger.info(f"🔍 Searching certification profiles for: '{certification_name}'")

    try:
        # Log database operation
        log_database_operation("SELECT", "certification_profiles", data={"search_term": certification_name, "pattern": f"%{certification_name}%"})

        stmt = select(CertificationProfile).where(
            CertificationProfile.name.ilike(f"%{certification_name}%")
        ).order_by(CertificationProfile.created_at.desc())
        result = await db.execute(stmt)
        profiles = result.scalars().all()

        logger.info(f"🔍 Found {len(profiles)} profiles matching '{certification_name}'")

        response_profiles = [CertificationProfileResponse.model_validate(profile) for profile in profiles]

        # Log successful response
        log_response_details("SEARCH /search/{certification_name}", response_data=response_profiles, status_code=200)
        logger.info(f"✅ Successfully returned {len(response_profiles)} search results")

        return response_profiles

    except Exception as e:
        logger.error(f"❌ Failed to search certification profiles for '{certification_name}': {e}")
        logger.error(f"Error type: {type(e)}")
        logger.error(f"Error args: {e.args}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
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
    # Log incoming request
    log_request_details("POST /{profile_id}/duplicate", "POST", profile_id=str(profile_id), data={"new_name": new_name, "new_version": new_version})
    logger.info(f"📋 Duplicating certification profile {profile_id} as '{new_name} v{new_version}'")

    try:
        # Get source profile
        log_database_operation("SELECT", "certification_profiles", profile_id=str(profile_id))

        stmt = select(CertificationProfile).where(CertificationProfile.id == profile_id)
        result = await db.execute(stmt)
        source_profile = result.scalar_one_or_none()

        if not source_profile:
            logger.warning(f"❌ Source profile not found for duplication: {profile_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Source certification profile with ID {profile_id} not found"
            )

        logger.info(f"✅ Found source profile: {source_profile.name} v{source_profile.version}")

        # Check if new profile already exists
        log_database_operation("SELECT", "certification_profiles", data={"name": new_name, "version": new_version})

        stmt = select(CertificationProfile).where(
            CertificationProfile.name == new_name,
            CertificationProfile.version == new_version
        )
        result = await db.execute(stmt)
        existing_profile = result.scalar_one_or_none()

        if existing_profile:
            logger.warning(f"❌ Target profile already exists: {new_name} v{new_version}")
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Certification profile '{new_name} v{new_version}' already exists"
            )

        logger.info(f"✅ Target profile name available: {new_name} v{new_version}")

        # Create duplicate profile
        log_data_transformation("DUPLICATE_profile_creation", input_data={"source_id": str(profile_id), "target_name": new_name, "target_version": new_version})

        new_profile = CertificationProfile(
            name=new_name,
            version=new_version,
            exam_domains=source_profile.exam_domains,
            knowledge_base_path=f"knowledge_base/{new_name.lower().replace(' ', '_')}_v{new_version}",
            assessment_template=source_profile.assessment_template
        )

        # Log database operation
        log_database_operation("INSERT", "certification_profiles", data={"name": new_name, "version": new_version, "source_id": str(profile_id)})

        db.add(new_profile)
        await db.commit()
        await db.refresh(new_profile)

        logger.info(f"✅ Duplicated certification profile: {new_name} v{new_version} from {source_profile.name}")

        response = CertificationProfileResponse.model_validate(new_profile)

        # Log successful response
        log_response_details("POST /{profile_id}/duplicate", profile_id=str(new_profile.id), response_data=response, status_code=201)
        logger.info(f"✅ Successfully returned duplicated profile: {new_name} v{new_version}")

        return response

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"❌ Failed to duplicate certification profile {profile_id} as '{new_name} v{new_version}': {e}")
        logger.error(f"Error type: {type(e)}")
        logger.error(f"Error args: {e.args}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
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
    # Log incoming request
    log_request_details("GET /{profile_id}/statistics", "GET", profile_id=str(profile_id))
    logger.info(f"📊 Getting statistics for certification profile: {profile_id}")

    try:
        # Get profile
        log_database_operation("SELECT", "certification_profiles", profile_id=str(profile_id))

        stmt = select(CertificationProfile).where(CertificationProfile.id == profile_id)
        result = await db.execute(stmt)
        profile = result.scalar_one_or_none()

        if not profile:
            logger.warning(f"❌ Profile not found for statistics: {profile_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Certification profile with ID {profile_id} not found"
            )

        logger.info(f"✅ Found profile for statistics: {profile.name} v{profile.version}")

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

        # Log successful response
        log_response_details("GET /{profile_id}/statistics", profile_id=str(profile_id), response_data=statistics, status_code=200)
        logger.info(f"✅ Successfully returned statistics for: {profile.name} v{profile.version}")

        return statistics

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to get certification profile statistics {profile_id}: {e}")
        logger.error(f"Error type: {type(e)}")
        logger.error(f"Error args: {e.args}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
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
    # Log incoming request
    log_request_details("POST /{profile_id}/validate", "POST", profile_id=str(profile_id))
    logger.info(f"✅ Validating certification profile: {profile_id}")

    try:
        # Get profile
        log_database_operation("SELECT", "certification_profiles", profile_id=str(profile_id))

        stmt = select(CertificationProfile).where(CertificationProfile.id == profile_id)
        result = await db.execute(stmt)
        profile = result.scalar_one_or_none()

        if not profile:
            logger.warning(f"❌ Profile not found for validation: {profile_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Certification profile with ID {profile_id} not found"
            )

        logger.info(f"✅ Found profile for validation: {profile.name} v{profile.version}")

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

        # Log validation summary
        logger.info(f"🔍 Validation complete for {profile.name}: valid={validation_results['is_valid']}, errors={len(validation_results['errors'])}, warnings={len(validation_results['warnings'])}")

        # Log successful response
        log_response_details("POST /{profile_id}/validate", profile_id=str(profile_id), response_data=validation_results, status_code=200)
        logger.info(f"✅ Successfully returned validation results for: {profile.name} v{profile.version}")

        return validation_results

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to validate certification profile {profile_id}: {e}")
        logger.error(f"Error type: {type(e)}")
        logger.error(f"Error args: {e.args}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to validate certification profile"
        )
