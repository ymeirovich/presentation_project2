"""Knowledge base management API endpoints."""

import logging
from pathlib import Path
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import JSONResponse

from src.knowledge.base import RAGKnowledgeBase
from src.schemas.knowledge import (
    DocumentUploadResponse,
    KnowledgeContextResponse,
    KnowledgeStatsResponse,
    IngestionResult
)
from src.service.dependencies import get_knowledge_base

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/upload", response_model=DocumentUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_documents(
    certification_id: str = Form(..., description="Certification profile ID"),
    content_classification: str = Form(default="exam_guide", description="Content type: exam_guide or transcript"),
    files: List[UploadFile] = File(..., description="Documents to upload"),
    knowledge_base: RAGKnowledgeBase = Depends(get_knowledge_base)
) -> DocumentUploadResponse:
    """Upload and process documents for knowledge base ingestion."""
    try:
        # Validate content classification
        if content_classification not in ["exam_guide", "transcript"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Content classification must be 'exam_guide' or 'transcript'"
            )

        # Validate file uploads
        if not files:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="At least one file must be provided"
            )

        # Process uploaded files
        documents = []
        upload_dir = Path("./uploads") / certification_id
        upload_dir.mkdir(parents=True, exist_ok=True)

        for file in files:
            if not file.filename:
                continue

            # Save uploaded file temporarily
            file_path = upload_dir / file.filename
            with open(file_path, "wb") as buffer:
                content = await file.read()
                buffer.write(content)

            documents.append({
                "file_path": str(file_path),
                "original_filename": file.filename
            })

        # Ingest documents into knowledge base
        result = await knowledge_base.ingest_certification_materials(
            certification_id=certification_id,
            documents=documents,
            content_classification=content_classification
        )

        # Clean up temporary files
        for doc in documents:
            try:
                Path(doc["file_path"]).unlink(missing_ok=True)
            except Exception as e:
                logger.warning(f"⚠️ Failed to clean up temp file {doc['file_path']}: {e}")

        logger.info(f"✅ Processed {len(documents)} documents for certification {certification_id}")
        return DocumentUploadResponse(**result)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to upload documents: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process document upload"
        )


@router.get("/context/{certification_id}", response_model=KnowledgeContextResponse)
async def retrieve_context(
    certification_id: str,
    query: str,
    k: int = 5,
    balance_sources: bool = True,
    knowledge_base: RAGKnowledgeBase = Depends(get_knowledge_base)
) -> KnowledgeContextResponse:
    """Retrieve relevant context for assessment generation."""
    try:
        if k < 1 or k > 20:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Parameter 'k' must be between 1 and 20"
            )

        result = await knowledge_base.retrieve_context_for_assessment(
            query=query,
            certification_id=certification_id,
            k=k,
            balance_sources=balance_sources
        )

        return KnowledgeContextResponse(**result)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to retrieve context: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve context"
        )


@router.get("/stats/{certification_id}", response_model=KnowledgeStatsResponse)
async def get_knowledge_stats(
    certification_id: str,
    knowledge_base: RAGKnowledgeBase = Depends(get_knowledge_base)
) -> KnowledgeStatsResponse:
    """Get knowledge base statistics for a certification."""
    try:
        result = await knowledge_base.get_certification_knowledge_stats(certification_id)
        return KnowledgeStatsResponse(**result)

    except Exception as e:
        logger.error(f"❌ Failed to get knowledge stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve knowledge statistics"
        )


@router.delete("/{certification_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_certification_knowledge(
    certification_id: str,
    knowledge_base: RAGKnowledgeBase = Depends(get_knowledge_base)
):
    """Delete all knowledge base content for a certification."""
    try:
        success = await knowledge_base.delete_certification_knowledge(certification_id)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete certification knowledge"
            )

        logger.info(f"✅ Deleted knowledge for certification: {certification_id}")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to delete certification knowledge: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete certification knowledge"
        )


@router.post("/bulk-ingest/{certification_id}", response_model=IngestionResult)
async def bulk_ingest_certification(
    certification_id: str,
    exam_guides_path: Optional[str] = Form(None, description="Path to exam guides directory"),
    transcripts_path: Optional[str] = Form(None, description="Path to transcripts directory"),
    knowledge_base: RAGKnowledgeBase = Depends(get_knowledge_base)
) -> IngestionResult:
    """Bulk ingest documents for a certification from directory structure."""
    try:
        exam_path = Path(exam_guides_path) if exam_guides_path else None
        transcript_path = Path(transcripts_path) if transcripts_path else None

        if not exam_path and not transcript_path:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="At least one of exam_guides_path or transcripts_path must be provided"
            )

        result = await knowledge_base.bulk_ingest_certification(
            certification_id=certification_id,
            exam_guides_path=exam_path,
            transcripts_path=transcript_path
        )

        return IngestionResult(**result)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to bulk ingest certification: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to bulk ingest certification"
        )


@router.get("/health", response_model=dict)
async def knowledge_health_check(
    knowledge_base: RAGKnowledgeBase = Depends(get_knowledge_base)
) -> dict:
    """Check the health of the knowledge base system."""
    try:
        result = await knowledge_base.health_check()

        if result.get("status") == "unhealthy":
            return JSONResponse(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                content=result
            )

        return result

    except Exception as e:
        logger.error(f"❌ Knowledge base health check failed: {e}")
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"status": "unhealthy", "error": str(e)}
        )