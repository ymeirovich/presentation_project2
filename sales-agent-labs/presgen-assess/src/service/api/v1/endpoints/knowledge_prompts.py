"""
API endpoints for knowledge base prompt management.
Handles CRUD operations for collection-level prompts.
"""

from fastapi import APIRouter, HTTPException, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
from sqlalchemy.exc import IntegrityError
from typing import List
from uuid import UUID

from src.models.knowledge_base_prompts import KnowledgeBasePrompts
from src.schemas.knowledge_base_prompts import (
    KnowledgeBasePromptsCreate,
    KnowledgeBasePromptsUpdate,
    KnowledgeBasePromptsResponse,
    KnowledgeBasePromptsListResponse
)
from src.service.database import get_db
from src.common.enhanced_logging import (
    KB_PROMPTS_API_LOGGER,
    set_correlation_id,
    track_data_transformation,
    log_data_flow
)

router = APIRouter()


@router.post(
    "/",
    response_model=KnowledgeBasePromptsResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create knowledge base prompts",
    description="Create a new knowledge base prompt configuration for a collection"
)
@track_data_transformation(
    logger=KB_PROMPTS_API_LOGGER,
    step="api_create",
    component="knowledge_prompts_api"
)
async def create_knowledge_base_prompts(
    prompts_data: KnowledgeBasePromptsCreate,
    db: AsyncSession = Depends(get_db)
) -> KnowledgeBasePromptsResponse:
    """Create new knowledge base prompts."""
    correlation_id = set_correlation_id()

    log_data_flow(
        logger=KB_PROMPTS_API_LOGGER,
        step="api_create_start",
        component="knowledge_prompts_api",
        message=f"Creating knowledge base prompts for collection: {prompts_data.collection_name}",
        data_before=prompts_data.dict()
    )

    try:
        # Create new knowledge base prompts record
        kb_prompts = KnowledgeBasePrompts(
            collection_name=prompts_data.collection_name,
            certification_name=prompts_data.certification_name,
            document_ingestion_prompt=prompts_data.document_ingestion_prompt,
            context_retrieval_prompt=prompts_data.context_retrieval_prompt,
            semantic_search_prompt=prompts_data.semantic_search_prompt,
            content_classification_prompt=prompts_data.content_classification_prompt,
            version=prompts_data.version,
            is_active=prompts_data.is_active
        )

        db.add(kb_prompts)
        await db.commit()
        await db.refresh(kb_prompts)

        response_data = KnowledgeBasePromptsResponse.from_orm(kb_prompts)

        log_data_flow(
            logger=KB_PROMPTS_API_LOGGER,
            step="api_create_success",
            component="knowledge_prompts_api",
            message=f"Successfully created knowledge base prompts: {kb_prompts.id}",
            data_after=response_data.dict(),
            success=True
        )

        return response_data

    except IntegrityError as e:
        await db.rollback()
        error_msg = f"Knowledge base prompts already exist for collection: {prompts_data.collection_name}"

        log_data_flow(
            logger=KB_PROMPTS_API_LOGGER,
            step="api_create_conflict",
            component="knowledge_prompts_api",
            message=error_msg,
            error=str(e),
            success=False
        )

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=error_msg
        )

    except Exception as e:
        await db.rollback()
        error_msg = f"Failed to create knowledge base prompts: {str(e)}"

        log_data_flow(
            logger=KB_PROMPTS_API_LOGGER,
            step="api_create_error",
            component="knowledge_prompts_api",
            message=error_msg,
            error=str(e),
            success=False
        )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error while creating knowledge base prompts"
        )


@router.get(
    "/{collection_name}",
    response_model=KnowledgeBasePromptsResponse,
    summary="Get knowledge base prompts",
    description="Retrieve knowledge base prompts for a specific collection"
)
@track_data_transformation(
    logger=KB_PROMPTS_API_LOGGER,
    step="api_get",
    component="knowledge_prompts_api"
)
async def get_knowledge_base_prompts(
    collection_name: str,
    db: AsyncSession = Depends(get_db)
) -> KnowledgeBasePromptsResponse:
    """Get knowledge base prompts by collection name."""
    correlation_id = set_correlation_id()

    log_data_flow(
        logger=KB_PROMPTS_API_LOGGER,
        step="api_get_start",
        component="knowledge_prompts_api",
        message=f"Retrieving knowledge base prompts for collection: {collection_name}",
        data_before={"collection_name": collection_name}
    )

    try:
        # Query for knowledge base prompts
        stmt = select(KnowledgeBasePrompts).where(
            KnowledgeBasePrompts.collection_name == collection_name
        )
        result = await db.execute(stmt)
        kb_prompts = result.scalar_one_or_none()

        if not kb_prompts:
            error_msg = f"Knowledge base prompts not found for collection: {collection_name}"

            log_data_flow(
                logger=KB_PROMPTS_API_LOGGER,
                step="api_get_not_found",
                component="knowledge_prompts_api",
                message=error_msg,
                success=False
            )

            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=error_msg
            )

        response_data = KnowledgeBasePromptsResponse.from_orm(kb_prompts)

        log_data_flow(
            logger=KB_PROMPTS_API_LOGGER,
            step="api_get_success",
            component="knowledge_prompts_api",
            message=f"Successfully retrieved knowledge base prompts: {kb_prompts.id}",
            data_after=response_data.dict(),
            success=True
        )

        return response_data

    except HTTPException:
        raise
    except Exception as e:
        error_msg = f"Failed to retrieve knowledge base prompts: {str(e)}"

        log_data_flow(
            logger=KB_PROMPTS_API_LOGGER,
            step="api_get_error",
            component="knowledge_prompts_api",
            message=error_msg,
            error=str(e),
            success=False
        )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error while retrieving knowledge base prompts"
        )


@router.put(
    "/{collection_name}",
    response_model=KnowledgeBasePromptsResponse,
    summary="Update knowledge base prompts",
    description="Update knowledge base prompts for a specific collection"
)
@track_data_transformation(
    logger=KB_PROMPTS_API_LOGGER,
    step="api_update",
    component="knowledge_prompts_api"
)
async def update_knowledge_base_prompts(
    collection_name: str,
    prompts_data: KnowledgeBasePromptsUpdate,
    db: AsyncSession = Depends(get_db)
) -> KnowledgeBasePromptsResponse:
    """Update knowledge base prompts."""
    correlation_id = set_correlation_id()

    log_data_flow(
        logger=KB_PROMPTS_API_LOGGER,
        step="api_update_start",
        component="knowledge_prompts_api",
        message=f"Updating knowledge base prompts for collection: {collection_name}",
        data_before=prompts_data.dict(exclude_unset=True)
    )

    try:
        # Check if prompts exist
        stmt = select(KnowledgeBasePrompts).where(
            KnowledgeBasePrompts.collection_name == collection_name
        )
        result = await db.execute(stmt)
        kb_prompts = result.scalar_one_or_none()

        if not kb_prompts:
            error_msg = f"Knowledge base prompts not found for collection: {collection_name}"

            log_data_flow(
                logger=KB_PROMPTS_API_LOGGER,
                step="api_update_not_found",
                component="knowledge_prompts_api",
                message=error_msg,
                success=False
            )

            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=error_msg
            )

        # Update only provided fields
        update_data = prompts_data.dict(exclude_unset=True)
        if update_data:
            stmt = update(KnowledgeBasePrompts).where(
                KnowledgeBasePrompts.collection_name == collection_name
            ).values(**update_data)
            await db.execute(stmt)
            await db.commit()

            # Refresh the record
            await db.refresh(kb_prompts)

        response_data = KnowledgeBasePromptsResponse.from_orm(kb_prompts)

        log_data_flow(
            logger=KB_PROMPTS_API_LOGGER,
            step="api_update_success",
            component="knowledge_prompts_api",
            message=f"Successfully updated knowledge base prompts: {kb_prompts.id}",
            data_after=response_data.dict(),
            success=True
        )

        return response_data

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        error_msg = f"Failed to update knowledge base prompts: {str(e)}"

        log_data_flow(
            logger=KB_PROMPTS_API_LOGGER,
            step="api_update_error",
            component="knowledge_prompts_api",
            message=error_msg,
            error=str(e),
            success=False
        )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error while updating knowledge base prompts"
        )


@router.get(
    "/",
    response_model=KnowledgeBasePromptsListResponse,
    summary="List knowledge base prompts",
    description="List all knowledge base prompt configurations"
)
@track_data_transformation(
    logger=KB_PROMPTS_API_LOGGER,
    step="api_list",
    component="knowledge_prompts_api"
)
async def list_knowledge_base_prompts(
    is_active: bool = None,
    db: AsyncSession = Depends(get_db)
) -> KnowledgeBasePromptsListResponse:
    """List all knowledge base prompts."""
    correlation_id = set_correlation_id()

    log_data_flow(
        logger=KB_PROMPTS_API_LOGGER,
        step="api_list_start",
        component="knowledge_prompts_api",
        message="Listing knowledge base prompts",
        data_before={"is_active": is_active}
    )

    try:
        # Build query
        stmt = select(KnowledgeBasePrompts)
        if is_active is not None:
            stmt = stmt.where(KnowledgeBasePrompts.is_active == is_active)

        # Execute query
        result = await db.execute(stmt)
        kb_prompts_list = result.scalars().all()

        # Convert to response format
        prompts_responses = [
            KnowledgeBasePromptsResponse.from_orm(kb_prompts)
            for kb_prompts in kb_prompts_list
        ]

        response_data = KnowledgeBasePromptsListResponse(
            prompts=prompts_responses,
            total=len(prompts_responses)
        )

        log_data_flow(
            logger=KB_PROMPTS_API_LOGGER,
            step="api_list_success",
            component="knowledge_prompts_api",
            message=f"Successfully listed {len(prompts_responses)} knowledge base prompt configurations",
            data_after={"total": len(prompts_responses)},
            success=True
        )

        return response_data

    except Exception as e:
        error_msg = f"Failed to list knowledge base prompts: {str(e)}"

        log_data_flow(
            logger=KB_PROMPTS_API_LOGGER,
            step="api_list_error",
            component="knowledge_prompts_api",
            message=error_msg,
            error=str(e),
            success=False
        )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error while listing knowledge base prompts"
        )


@router.delete(
    "/{collection_name}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete knowledge base prompts",
    description="Delete knowledge base prompts for a specific collection"
)
@track_data_transformation(
    logger=KB_PROMPTS_API_LOGGER,
    step="api_delete",
    component="knowledge_prompts_api"
)
async def delete_knowledge_base_prompts(
    collection_name: str,
    db: AsyncSession = Depends(get_db)
):
    """Delete knowledge base prompts."""
    correlation_id = set_correlation_id()

    log_data_flow(
        logger=KB_PROMPTS_API_LOGGER,
        step="api_delete_start",
        component="knowledge_prompts_api",
        message=f"Deleting knowledge base prompts for collection: {collection_name}",
        data_before={"collection_name": collection_name}
    )

    try:
        # Check if prompts exist
        stmt = select(KnowledgeBasePrompts).where(
            KnowledgeBasePrompts.collection_name == collection_name
        )
        result = await db.execute(stmt)
        kb_prompts = result.scalar_one_or_none()

        if not kb_prompts:
            error_msg = f"Knowledge base prompts not found for collection: {collection_name}"

            log_data_flow(
                logger=KB_PROMPTS_API_LOGGER,
                step="api_delete_not_found",
                component="knowledge_prompts_api",
                message=error_msg,
                success=False
            )

            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=error_msg
            )

        # Delete the record
        stmt = delete(KnowledgeBasePrompts).where(
            KnowledgeBasePrompts.collection_name == collection_name
        )
        await db.execute(stmt)
        await db.commit()

        log_data_flow(
            logger=KB_PROMPTS_API_LOGGER,
            step="api_delete_success",
            component="knowledge_prompts_api",
            message=f"Successfully deleted knowledge base prompts for collection: {collection_name}",
            success=True
        )

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        error_msg = f"Failed to delete knowledge base prompts: {str(e)}"

        log_data_flow(
            logger=KB_PROMPTS_API_LOGGER,
            step="api_delete_error",
            component="knowledge_prompts_api",
            message=error_msg,
            error=str(e),
            success=False
        )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error while deleting knowledge base prompts"
        )