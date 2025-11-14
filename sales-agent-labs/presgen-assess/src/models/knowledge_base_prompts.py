"""
Database model for knowledge base prompts.
Stores collection-level prompts for knowledge base operations.
"""

from sqlalchemy import Column, String, Text, Boolean, DateTime, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.types import TypeDecorator, CHAR
import uuid

from src.models.base import Base


class GUID(TypeDecorator):
    """Platform-independent GUID type."""

    impl = CHAR
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == 'postgresql':
            return dialect.type_descriptor(PGUUID(as_uuid=True))
        return dialect.type_descriptor(CHAR(36))

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        if isinstance(value, uuid.UUID):
            return str(value)
        return str(uuid.UUID(value))

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        if isinstance(value, uuid.UUID):
            return value
        return uuid.UUID(value)


class KnowledgeBasePrompts(Base):
    """
    Knowledge base prompts model for collection-level prompt storage.

    This table stores prompts that control how knowledge retrieval and ingestion
    works for a certification's knowledge base. These prompts are shared across
    all users of that certification's knowledge base.

    Separation from certification profile prompts ensures that:
    - Knowledge base operations are consistent across users
    - Profile-specific prompts don't interfere with knowledge base behavior
    - Changes to knowledge base prompts affect all users consistently
    - Changes to profile prompts don't break knowledge base functionality
    """

    __tablename__ = "knowledge_base_prompts"

    # Primary key
    id = Column(GUID(), primary_key=True, default=uuid.uuid4)

    # Unique identifier for the knowledge base collection
    collection_name = Column(String(255), nullable=False, unique=True, index=True)

    # Human-readable certification name for reference
    certification_name = Column(String(255), nullable=False)

    # Knowledge base operation prompts
    document_ingestion_prompt = Column(
        Text,
        nullable=True,
        comment="Prompt for document ingestion and preprocessing"
    )

    context_retrieval_prompt = Column(
        Text,
        nullable=True,
        comment="Prompt for retrieving relevant context from knowledge base"
    )

    semantic_search_prompt = Column(
        Text,
        nullable=True,
        comment="Prompt for semantic search operations"
    )

    content_classification_prompt = Column(
        Text,
        nullable=True,
        comment="Prompt for classifying and organizing content"
    )

    # Metadata fields
    version = Column(String(50), nullable=False, default="v1.0")
    is_active = Column(Boolean, nullable=False, default=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<KnowledgeBasePrompts(collection_name='{self.collection_name}', certification_name='{self.certification_name}')>"

    def to_dict(self):
        """Convert model to dictionary for API responses."""
        return {
            "id": str(self.id),
            "collection_name": self.collection_name,
            "certification_name": self.certification_name,
            "document_ingestion_prompt": self.document_ingestion_prompt,
            "context_retrieval_prompt": self.context_retrieval_prompt,
            "semantic_search_prompt": self.semantic_search_prompt,
            "content_classification_prompt": self.content_classification_prompt,
            "version": self.version,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }
