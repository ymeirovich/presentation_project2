"""Certification profile data models."""

from datetime import datetime
from typing import Dict, List, Optional
from uuid import UUID, uuid4

from sqlalchemy import Column, String, DateTime, JSON, Text, Integer, Boolean
from sqlalchemy.dialects.postgresql import UUID as PGUUID, ARRAY
from sqlalchemy.sql import func
from pydantic import BaseModel, Field, validator

from src.models.base import Base


class CertificationProfile(Base):
    """Database model for certification profiles."""

    __tablename__ = "certification_profiles"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    name = Column(String(255), nullable=False)
    version = Column(String(100), nullable=False)
    exam_domains = Column(JSON, nullable=False)
    knowledge_base_path = Column(Text, nullable=False)
    assessment_template = Column(JSON)

    # Enhanced fields for ChromaDB integration
    bundle_version = Column(String(50), default="v1.0")
    collection_name = Column(String(255))  # ChromaDB collection name

    # Custom prompts for different workflow processes
    assessment_prompt = Column(Text)  # Controls assessment generation
    presentation_prompt = Column(Text)  # Controls course presentation generation
    gap_analysis_prompt = Column(Text)  # Controls assessment gap analysis

    # File upload tracking
    uploaded_files_metadata = Column(JSON, default=lambda: [])  # Track uploaded files
    resource_binding_enabled = Column(Boolean, default=True)  # Enable cascade delete

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        {"schema": None}  # Default schema
    )


class KnowledgeBaseDocument(Base):
    """Database model for tracking knowledge base documents."""

    __tablename__ = "knowledge_base_documents"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    certification_profile_id = Column(PGUUID(as_uuid=True), nullable=False)
    original_filename = Column(String(500), nullable=False)
    stored_path = Column(Text, nullable=False)
    document_type = Column(String(50), nullable=False)  # PDF, DOCX, TXT
    content_classification = Column(String(50), nullable=False)  # exam_guide, transcript, supplementary
    file_size_bytes = Column(Integer, nullable=False)
    processing_status = Column(String(50), default='pending')
    chunk_count = Column(Integer)
    embedding_model = Column(String(100))  # e.g., "text-embedding-3-small"
    embedding_dimension = Column(Integer)  # e.g., 1536 for OpenAI, 128 for fallback
    processed_at = Column(DateTime(timezone=True))
    checksum = Column(String(64))  # For duplicate detection
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class VectorIngestionAudit(Base):
    """Audit trail for vector database ingestion."""

    __tablename__ = "vector_ingestion_audit"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    document_id = Column(PGUUID(as_uuid=True), nullable=False)
    certification_profile_id = Column(PGUUID(as_uuid=True), nullable=False)
    chunks_processed = Column(Integer, nullable=False)
    embeddings_generated = Column(Integer, nullable=False)
    processing_duration_seconds = Column(Integer)
    vector_collection_name = Column(String(255))
    success = Column(Boolean, default=True)
    error_message = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


# Pydantic models for API validation

class ExamDomain(BaseModel):
    """Exam domain specification."""
    name: str
    weight_percentage: int = Field(ge=0, le=100)
    subdomains: List[str] = Field(default_factory=list)
    skills_measured: List[str] = Field(default_factory=list)


class CertificationProfileCreate(BaseModel):
    """Request model for creating certification profiles."""
    name: str = Field(..., min_length=1, max_length=255)
    version: str = Field(..., min_length=1, max_length=100)
    exam_domains: List[ExamDomain]
    assessment_template: Optional[Dict] = None

    # ChromaDB integration fields
    bundle_version: str = Field(default="v1.0", max_length=50)

    # Custom prompts with defaults
    assessment_prompt: Optional[str] = Field(None, description="Custom prompt for assessment generation")
    presentation_prompt: Optional[str] = Field(None, description="Custom prompt for presentation generation")
    gap_analysis_prompt: Optional[str] = Field(None, description="Custom prompt for gap analysis")

    # File management settings
    resource_binding_enabled: bool = Field(default=True, description="Enable cascade delete for resources")

    @validator('exam_domains')
    def validate_domains_total_weight(cls, v):
        """Ensure domain weights sum to 100%."""
        total_weight = sum(domain.weight_percentage for domain in v)
        if total_weight != 100:
            raise ValueError(f'Domain weights must sum to 100%, got {total_weight}%')
        return v


class CertificationProfileUpdate(BaseModel):
    """Request model for updating certification profiles."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    version: Optional[str] = Field(None, min_length=1, max_length=100)
    exam_domains: Optional[List[ExamDomain]] = None
    assessment_template: Optional[Dict] = None

    # ChromaDB integration fields
    bundle_version: Optional[str] = Field(None, max_length=50)

    # Custom prompts
    assessment_prompt: Optional[str] = Field(None, description="Custom prompt for assessment generation")
    presentation_prompt: Optional[str] = Field(None, description="Custom prompt for presentation generation")
    gap_analysis_prompt: Optional[str] = Field(None, description="Custom prompt for gap analysis")

    # File management settings
    resource_binding_enabled: Optional[bool] = Field(None, description="Enable cascade delete for resources")

    @validator('exam_domains')
    def validate_domains_total_weight(cls, v):
        """Ensure domain weights sum to 100%."""
        if v is not None:
            total_weight = sum(domain.weight_percentage for domain in v)
            if total_weight != 100:
                raise ValueError(f'Domain weights must sum to 100%, got {total_weight}%')
        return v


class CertificationProfileResponse(BaseModel):
    """Response model for certification profiles."""
    id: UUID
    name: str
    version: str
    exam_domains: List[ExamDomain]
    knowledge_base_path: str
    assessment_template: Optional[Dict]

    # ChromaDB integration fields
    bundle_version: str
    collection_name: Optional[str]

    # Custom prompts
    assessment_prompt: Optional[str]
    presentation_prompt: Optional[str]
    gap_analysis_prompt: Optional[str]

    # File management
    uploaded_files_metadata: List[Dict] = Field(default_factory=list)
    resource_binding_enabled: bool

    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class FileReference(BaseModel):
    """Reference to uploaded file for certification profile."""
    file_id: str
    original_filename: str
    resource_type: str  # exam_guide, transcript, supplemental
    file_size: int
    upload_timestamp: str
    processing_status: str
    chunk_count: int = 0


class UploadedFilesMetadata(BaseModel):
    """Metadata structure for uploaded files in certification profile."""
    exam_guides: List[FileReference] = Field(default_factory=list)
    transcripts: List[FileReference] = Field(default_factory=list)
    supplemental: List[FileReference] = Field(default_factory=list)
    total_files: int = 0
    total_chunks: int = 0
    last_updated: str


class DocumentUploadRequest(BaseModel):
    """Request model for document uploads."""
    content_classification: str = Field(..., pattern="^(exam_guide|transcript|supplementary)$")
    description: Optional[str] = Field(None, max_length=500)

    @validator('content_classification')
    def validate_content_classification(cls, v):
        """Validate content classification."""
        valid_types = ['exam_guide', 'transcript', 'supplementary']
        if v not in valid_types:
            raise ValueError(f'Content classification must be one of: {valid_types}')
        return v


class DocumentResponse(BaseModel):
    """Response model for documents."""
    id: UUID
    original_filename: str
    document_type: str
    content_classification: str
    file_size_bytes: int
    processing_status: str
    chunk_count: Optional[int]
    processed_at: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True