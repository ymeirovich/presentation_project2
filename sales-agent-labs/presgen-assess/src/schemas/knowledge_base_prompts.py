"""
Pydantic schemas for knowledge base prompts API.
Defines request/response models for knowledge base prompt operations.
"""

from pydantic import BaseModel, Field, validator
from typing import Optional
from datetime import datetime
from uuid import UUID


class KnowledgeBasePromptsBase(BaseModel):
    """Base schema for knowledge base prompts."""

    collection_name: str = Field(
        ...,
        description="Unique identifier for the knowledge base collection",
        min_length=1,
        max_length=255,
        example="aws_solutions_architect_v2024"
    )

    certification_name: str = Field(
        ...,
        description="Human-readable certification name",
        min_length=1,
        max_length=255,
        example="AWS Solutions Architect Associate"
    )

    document_ingestion_prompt: Optional[str] = Field(
        None,
        description="Prompt for document ingestion and preprocessing",
        example="Process AWS documentation with focus on architectural patterns and best practices"
    )

    context_retrieval_prompt: Optional[str] = Field(
        None,
        description="Prompt for retrieving relevant context from knowledge base",
        example="Retrieve AWS architectural context that directly relates to the user's question"
    )

    semantic_search_prompt: Optional[str] = Field(
        None,
        description="Prompt for semantic search operations",
        example="Search AWS knowledge base for concepts and patterns relevant to the query"
    )

    content_classification_prompt: Optional[str] = Field(
        None,
        description="Prompt for classifying and organizing content",
        example="Classify AWS content by service category and architectural domain"
    )

    version: str = Field(
        default="v1.0",
        description="Version identifier for prompt schema",
        max_length=50,
        example="v1.0"
    )

    is_active: bool = Field(
        default=True,
        description="Whether this prompt configuration is active"
    )

    @validator('collection_name')
    def validate_collection_name(cls, v):
        """Validate collection name format."""
        if not v or not v.strip():
            raise ValueError('Collection name cannot be empty')

        # Collection names should be URL-safe and filesystem-safe
        allowed_chars = set('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-')
        if not all(c in allowed_chars for c in v):
            raise ValueError('Collection name can only contain letters, numbers, underscores, and hyphens')

        return v.strip()

    @validator('certification_name')
    def validate_certification_name(cls, v):
        """Validate certification name."""
        if not v or not v.strip():
            raise ValueError('Certification name cannot be empty')
        return v.strip()

    class Config:
        """Pydantic configuration."""
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            UUID: str
        }


class KnowledgeBasePromptsCreate(KnowledgeBasePromptsBase):
    """Schema for creating knowledge base prompts."""

    class Config:
        schema_extra = {
            "example": {
                "collection_name": "aws_solutions_architect_v2024",
                "certification_name": "AWS Solutions Architect Associate",
                "document_ingestion_prompt": "Process AWS documentation focusing on architectural patterns, best practices, and service integration points",
                "context_retrieval_prompt": "Retrieve AWS architectural context that directly relates to the question, including relevant services and design patterns",
                "semantic_search_prompt": "Search the AWS knowledge base for concepts, patterns, and solutions that semantically match the user's query",
                "content_classification_prompt": "Classify AWS content by service category (compute, storage, network, security) and architectural domain (availability, scalability, cost optimization)",
                "version": "v1.0",
                "is_active": True
            }
        }


class KnowledgeBasePromptsUpdate(BaseModel):
    """Schema for updating knowledge base prompts."""

    document_ingestion_prompt: Optional[str] = Field(
        None,
        description="Updated prompt for document ingestion"
    )

    context_retrieval_prompt: Optional[str] = Field(
        None,
        description="Updated prompt for context retrieval"
    )

    semantic_search_prompt: Optional[str] = Field(
        None,
        description="Updated prompt for semantic search"
    )

    content_classification_prompt: Optional[str] = Field(
        None,
        description="Updated prompt for content classification"
    )

    version: Optional[str] = Field(
        None,
        description="Updated version identifier",
        max_length=50
    )

    is_active: Optional[bool] = Field(
        None,
        description="Updated active status"
    )

    class Config:
        schema_extra = {
            "example": {
                "document_ingestion_prompt": "Updated ingestion prompt with new requirements",
                "is_active": True
            }
        }


class KnowledgeBasePromptsResponse(KnowledgeBasePromptsBase):
    """Schema for knowledge base prompts API responses."""

    id: UUID = Field(
        ...,
        description="Unique identifier for the knowledge base prompts record"
    )

    created_at: datetime = Field(
        ...,
        description="When the record was created"
    )

    updated_at: datetime = Field(
        ...,
        description="When the record was last updated"
    )

    class Config:
        schema_extra = {
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "collection_name": "aws_solutions_architect_v2024",
                "certification_name": "AWS Solutions Architect Associate",
                "document_ingestion_prompt": "Process AWS documentation focusing on architectural patterns",
                "context_retrieval_prompt": "Retrieve relevant AWS architectural context",
                "semantic_search_prompt": "Search AWS knowledge base semantically",
                "content_classification_prompt": "Classify AWS content by domain",
                "version": "v1.0",
                "is_active": True,
                "created_at": "2024-01-15T10:30:00Z",
                "updated_at": "2024-01-15T10:30:00Z"
            }
        }


class KnowledgeBasePromptsListResponse(BaseModel):
    """Schema for listing knowledge base prompts."""

    prompts: list[KnowledgeBasePromptsResponse] = Field(
        ...,
        description="List of knowledge base prompt configurations"
    )

    total: int = Field(
        ...,
        description="Total number of prompt configurations"
    )

    class Config:
        schema_extra = {
            "example": {
                "prompts": [
                    {
                        "id": "550e8400-e29b-41d4-a716-446655440000",
                        "collection_name": "aws_solutions_architect_v2024",
                        "certification_name": "AWS Solutions Architect Associate",
                        "document_ingestion_prompt": "Process AWS documentation",
                        "version": "v1.0",
                        "is_active": True,
                        "created_at": "2024-01-15T10:30:00Z",
                        "updated_at": "2024-01-15T10:30:00Z"
                    }
                ],
                "total": 1
            }
        }