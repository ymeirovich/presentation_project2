"""Pydantic schemas for knowledge base operations."""

from datetime import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class DocumentInfo(BaseModel):
    """Document information schema."""
    filename: str = Field(..., description="Document filename")
    chunk_count: Optional[int] = Field(None, description="Number of chunks created")
    file_info: Optional[Dict] = Field(None, description="Additional file metadata")
    error: Optional[str] = Field(None, description="Error message if processing failed")


class IngestionResult(BaseModel):
    """Result of document ingestion process."""
    certification_id: str = Field(..., description="Certification profile ID")
    content_classification: Optional[str] = Field(None, description="Content classification type")
    processed_documents: List[DocumentInfo] = Field(default_factory=list, description="Successfully processed documents")
    failed_documents: List[DocumentInfo] = Field(default_factory=list, description="Failed document processing")
    total_chunks: int = Field(default=0, description="Total number of chunks created")
    success: bool = Field(..., description="Overall success status")
    error: Optional[str] = Field(None, description="Error message if ingestion failed")
    exam_guides_result: Optional[Dict] = Field(None, description="Exam guides processing result")
    transcripts_result: Optional[Dict] = Field(None, description="Transcripts processing result")


class DocumentUploadResponse(IngestionResult):
    """Response schema for document upload endpoint."""
    pass


class ContextSource(BaseModel):
    """Source information for retrieved context."""
    content: str = Field(..., description="Retrieved content")
    source_type: str = Field(..., description="Type of source (exam_guide, transcript)")
    metadata: Dict = Field(..., description="Source metadata")
    distance: float = Field(..., description="Semantic distance/relevance score")
    citation: Optional[str] = Field(None, description="Source citation")


class SourceGroup(BaseModel):
    """Grouped sources by type."""
    count: int = Field(..., description="Number of sources in this group")
    results: List[ContextSource] = Field(..., description="Source results")


class KnowledgeContextResponse(BaseModel):
    """Response schema for context retrieval."""
    query: str = Field(..., description="Original query")
    certification_id: str = Field(..., description="Certification profile ID")
    total_results: int = Field(..., description="Total number of results")
    sources: Dict[str, SourceGroup] = Field(..., description="Sources grouped by type")
    combined_context: str = Field(..., description="Formatted context for LLM consumption")
    citations: List[str] = Field(..., description="List of source citations")
    error: Optional[str] = Field(None, description="Error message if retrieval failed")


class CollectionStats(BaseModel):
    """Statistics for a document collection."""
    count: int = Field(..., description="Number of documents in collection")
    metadata: Optional[Dict] = Field(None, description="Collection metadata")


class KnowledgeStatsResponse(BaseModel):
    """Response schema for knowledge base statistics."""
    certification_id: str = Field(..., description="Certification profile ID")
    stats: Optional[Dict] = Field(None, description="Knowledge base statistics")
    knowledge_base_path: Optional[str] = Field(None, description="Path to knowledge base")
    error: Optional[str] = Field(None, description="Error message if stats retrieval failed")


class SimilarContent(BaseModel):
    """Schema for similar content search results."""
    content: str = Field(..., description="Similar content text")
    collection: str = Field(..., description="Source collection name")
    similarity: float = Field(..., description="Similarity score (0-1)")
    metadata: Dict = Field(..., description="Content metadata")


class KnowledgeHealthResponse(BaseModel):
    """Response schema for knowledge base health check."""
    status: str = Field(..., description="Overall health status")
    components: Dict = Field(..., description="Health status of individual components")
    timestamp: str = Field(..., description="Health check timestamp")
    error: Optional[str] = Field(None, description="Error message if health check failed")


class BulkIngestRequest(BaseModel):
    """Request schema for bulk document ingestion."""
    certification_id: str = Field(..., description="Certification profile ID")
    exam_guides_path: Optional[str] = Field(None, description="Path to exam guides directory")
    transcripts_path: Optional[str] = Field(None, description="Path to transcripts directory")

    class Config:
        json_schema_extra = {
            "example": {
                "certification_id": "aws-solutions-architect-associate",
                "exam_guides_path": "/data/certifications/aws-saa/guides",
                "transcripts_path": "/data/certifications/aws-saa/transcripts"
            }
        }