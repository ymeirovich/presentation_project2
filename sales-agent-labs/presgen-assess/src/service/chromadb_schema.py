"""
ChromaDB Schema and Collection Management for PresGen-Assess

This module provides the schema definitions and collection management
for certification-specific RAG knowledge bases using ChromaDB.
"""

import hashlib
import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional, Literal
from pydantic import BaseModel, Field, validator
from enum import Enum
import chromadb
from chromadb.utils import embedding_functions


class ResourceType(str, Enum):
    """Supported resource types for certification materials"""
    EXAM_GUIDE = "exam_guide"
    TRANSCRIPT = "transcript"
    SUPPLEMENTAL = "supplemental"


class ContentType(str, Enum):
    """Content classification types"""
    CONCEPT = "concept"
    EXAMPLE = "example"
    PROCEDURE = "procedure"
    ASSESSMENT = "assessment"


class DifficultyLevel(str, Enum):
    """Content difficulty levels"""
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    EXPERT = "expert"


class TranscriptQuality(str, Enum):
    """Transcript quality levels"""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class MaterialType(str, Enum):
    """Supplemental material types"""
    WHITEPAPER = "whitepaper"
    BLOG = "blog"
    DOCUMENTATION = "documentation"
    ARTICLE = "article"


class DocumentMetadata(BaseModel):
    """Core metadata schema for all document chunks"""

    # Tenant & Certification Isolation
    user_id: str = Field(..., description="User/tenant identifier")
    cert_id: str = Field(..., description="Certification identifier (e.g., aws-saa-c03)")
    cert_profile_id: str = Field(..., description="UUID of certification profile")
    bundle_version: str = Field(..., description="Bundle version (e.g., v1.0)")

    # Resource Classification
    resource_type: ResourceType = Field(..., description="Type of resource")
    source_file: str = Field(..., description="Original filename")
    source_uri: str = Field(..., description="File path or URL")
    mime_type: str = Field(..., description="MIME type of source file")

    # Content Structure
    section: str = Field("", description="Section title or chapter name")
    page: Optional[int] = Field(None, description="Page number if applicable")
    chunk_index: int = Field(..., description="Sequential chunk number")
    chunk_size: int = Field(..., description="Character count of chunk")

    # Content Classification
    content_type: ContentType = Field(..., description="Content classification")
    domain: str = Field("", description="Certification domain")
    subdomain: str = Field("", description="Specific subdomain or skill area")
    difficulty_level: DifficultyLevel = Field(DifficultyLevel.INTERMEDIATE, description="Content difficulty")

    # Technical Metadata
    embed_model: str = Field("text-embedding-3-small", description="Embedding model used")
    processing_timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    content_hash: str = Field(..., description="SHA-256 hash of content")
    language: str = Field("en", description="Content language")

    # Retrieval Optimization
    keywords: List[str] = Field(default_factory=list, description="Extracted keywords")
    concepts: List[str] = Field(default_factory=list, description="Key concepts covered")
    relevance_score: float = Field(0.5, ge=0.0, le=1.0, description="Content relevance score")

    # Version Control
    file_version: str = Field("1.0", description="Version of source file")
    chunk_version: str = Field("1.0", description="Version of chunk processing")
    schema_version: str = Field("1.0", description="Metadata schema version")

    @validator('content_hash')
    def validate_content_hash(cls, v):
        """Ensure content hash is valid SHA-256"""
        if len(v) != 64 or not all(c in '0123456789abcdef' for c in v.lower()):
            raise ValueError("Content hash must be a valid SHA-256 hex string")
        return v.lower()

    def to_chromadb_metadata(self) -> Dict[str, Any]:
        """Convert to ChromaDB-compatible metadata dict"""
        return {
            # Convert enums to strings
            "resource_type": self.resource_type.value,
            "content_type": self.content_type.value,
            "difficulty_level": self.difficulty_level.value,
            # Include all other fields
            **{k: v for k, v in self.dict().items()
               if k not in ['resource_type', 'content_type', 'difficulty_level'] and v is not None}
        }


class ExamGuideMetadata(DocumentMetadata):
    """Extended metadata for exam guide resources"""

    resource_type: Literal[ResourceType.EXAM_GUIDE] = ResourceType.EXAM_GUIDE
    exam_code: str = Field(..., description="Exam code (e.g., SAA-C03)")
    official_source: bool = Field(True, description="True if from official provider")
    content_authority: str = Field(..., description="Content authority (e.g., AWS, Microsoft)")
    exam_objectives: List[str] = Field(default_factory=list, description="Related exam objectives")
    study_weight: float = Field(0.5, ge=0.0, le=1.0, description="Importance weight")


class TranscriptMetadata(DocumentMetadata):
    """Extended metadata for transcript resources"""

    resource_type: Literal[ResourceType.TRANSCRIPT] = ResourceType.TRANSCRIPT
    course_title: str = Field(..., description="Course or video title")
    instructor: str = Field("", description="Instructor name")
    duration_minutes: Optional[int] = Field(None, description="Content duration in minutes")
    transcript_quality: TranscriptQuality = Field(TranscriptQuality.MEDIUM, description="Transcript quality")
    speaker_context: str = Field("instructor", description="Speaker context")


class SupplementalMetadata(DocumentMetadata):
    """Extended metadata for supplemental resources"""

    resource_type: Literal[ResourceType.SUPPLEMENTAL] = ResourceType.SUPPLEMENTAL
    material_type: MaterialType = Field(..., description="Type of supplemental material")
    author: str = Field("", description="Author or organization")
    publication_date: Optional[str] = Field(None, description="Publication date (ISO format)")
    credibility_score: float = Field(0.5, ge=0.0, le=1.0, description="Source credibility score")


class CollectionMetadata(BaseModel):
    """Metadata for ChromaDB collections"""

    cert_id: str = Field(..., description="Certification identifier")
    cert_name: str = Field(..., description="Full certification name")
    bundle_version: str = Field(..., description="Bundle version")
    embed_model: str = Field("text-embedding-3-small", description="Embedding model")
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    user_id: str = Field(..., description="User identifier")
    tenant_isolation: bool = Field(True, description="Tenant isolation enabled")
    resource_types: List[str] = Field(default_factory=list, description="Available resource types")
    total_documents: int = Field(0, description="Total document count")
    total_chunks: int = Field(0, description="Total chunk count")


class ChromaDBCollectionManager:
    """Manager for ChromaDB collections with strict isolation and versioning"""

    def __init__(self, chroma_client: chromadb.Client, embed_model: str = "text-embedding-3-small"):
        self.client = chroma_client
        self.embed_model = embed_model
        self.embedding_function = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name=embed_model
        )

    @staticmethod
    def generate_collection_name(user_id: str, cert_id: str, bundle_version: str) -> str:
        """Generate collection name with strict naming convention"""
        # Sanitize inputs to ensure valid collection names
        safe_user = "".join(c for c in user_id if c.isalnum() or c in "-_")[:50]
        safe_cert = "".join(c for c in cert_id if c.isalnum() or c in "-_")[:50]
        safe_version = "".join(c for c in bundle_version if c.isalnum() or c in ".-_")[:20]

        return f"assess_{safe_user}_{safe_cert}_{safe_version}"

    def create_collection(
        self,
        user_id: str,
        cert_id: str,
        cert_name: str,
        bundle_version: str
    ) -> chromadb.Collection:
        """Create a new collection for certification resources"""

        collection_name = self.generate_collection_name(user_id, cert_id, bundle_version)

        # Prepare collection metadata
        collection_metadata = CollectionMetadata(
            cert_id=cert_id,
            cert_name=cert_name,
            bundle_version=bundle_version,
            embed_model=self.embed_model,
            user_id=user_id
        )

        # Create collection
        collection = self.client.create_collection(
            name=collection_name,
            metadata=collection_metadata.dict(),
            embedding_function=self.embedding_function
        )

        return collection

    def get_collection(self, user_id: str, cert_id: str, bundle_version: str) -> chromadb.Collection:
        """Get existing collection"""
        collection_name = self.generate_collection_name(user_id, cert_id, bundle_version)
        return self.client.get_collection(
            name=collection_name,
            embedding_function=self.embedding_function
        )

    def delete_collection(self, user_id: str, cert_id: str, bundle_version: str) -> bool:
        """Delete collection and all its data"""
        collection_name = self.generate_collection_name(user_id, cert_id, bundle_version)
        try:
            self.client.delete_collection(collection_name)
            return True
        except Exception:
            return False

    def list_user_collections(self, user_id: str) -> List[Dict[str, Any]]:
        """List all collections for a user"""
        all_collections = self.client.list_collections()
        user_prefix = f"assess_{user_id}_"

        user_collections = []
        for collection in all_collections:
            if collection.name.startswith(user_prefix):
                metadata = collection.metadata or {}
                user_collections.append({
                    "name": collection.name,
                    "cert_id": metadata.get("cert_id"),
                    "cert_name": metadata.get("cert_name"),
                    "bundle_version": metadata.get("bundle_version"),
                    "created_at": metadata.get("created_at"),
                    "total_documents": metadata.get("total_documents", 0),
                    "total_chunks": metadata.get("total_chunks", 0)
                })

        return user_collections

    def add_documents(
        self,
        collection: chromadb.Collection,
        documents: List[str],
        metadatas: List[DocumentMetadata],
        ids: Optional[List[str]] = None
    ) -> None:
        """Add documents to collection with metadata validation"""

        if len(documents) != len(metadatas):
            raise ValueError("Documents and metadata lists must have same length")

        # Generate IDs if not provided
        if ids is None:
            ids = [str(uuid.uuid4()) for _ in documents]

        # Convert metadata to ChromaDB format
        chromadb_metadatas = [meta.to_chromadb_metadata() for meta in metadatas]

        # Add to collection
        collection.add(
            documents=documents,
            metadatas=chromadb_metadatas,
            ids=ids
        )

        # Update collection metadata
        current_meta = collection.metadata or {}
        current_meta["total_documents"] = current_meta.get("total_documents", 0) + len(documents)
        current_meta["total_chunks"] = current_meta.get("total_chunks", 0) + len(documents)

        # Note: ChromaDB doesn't support updating collection metadata after creation
        # This would need to be tracked separately in the application database

    def query_collection(
        self,
        collection: chromadb.Collection,
        query_texts: List[str],
        user_id: str,
        cert_id: str,
        bundle_version: str,
        resource_types: Optional[List[ResourceType]] = None,
        domains: Optional[List[str]] = None,
        difficulty_levels: Optional[List[DifficultyLevel]] = None,
        n_results: int = 10
    ) -> Dict[str, Any]:
        """Query collection with strict filtering"""

        # Build mandatory filters
        where_clause = {
            "user_id": user_id,
            "cert_id": cert_id,
            "bundle_version": bundle_version
        }

        # Add optional filters
        if resource_types:
            where_clause["resource_type"] = {"$in": [rt.value for rt in resource_types]}

        if domains:
            where_clause["domain"] = {"$in": domains}

        if difficulty_levels:
            where_clause["difficulty_level"] = {"$in": [dl.value for dl in difficulty_levels]}

        # Execute query
        results = collection.query(
            query_texts=query_texts,
            where=where_clause,
            n_results=n_results
        )

        return results


def generate_content_hash(content: str) -> str:
    """Generate SHA-256 hash for content"""
    return hashlib.sha256(content.encode('utf-8')).hexdigest()


def create_document_metadata(
    content: str,
    user_id: str,
    cert_id: str,
    cert_profile_id: str,
    bundle_version: str,
    resource_type: ResourceType,
    source_file: str,
    source_uri: str,
    mime_type: str,
    chunk_index: int,
    content_type: ContentType = ContentType.CONCEPT,
    section: str = "",
    page: Optional[int] = None,
    domain: str = "",
    subdomain: str = "",
    difficulty_level: DifficultyLevel = DifficultyLevel.INTERMEDIATE,
    keywords: Optional[List[str]] = None,
    concepts: Optional[List[str]] = None,
    **kwargs
) -> DocumentMetadata:
    """Factory function to create DocumentMetadata with proper validation"""

    return DocumentMetadata(
        user_id=user_id,
        cert_id=cert_id,
        cert_profile_id=cert_profile_id,
        bundle_version=bundle_version,
        resource_type=resource_type,
        source_file=source_file,
        source_uri=source_uri,
        mime_type=mime_type,
        chunk_index=chunk_index,
        chunk_size=len(content),
        content_type=content_type,
        section=section,
        page=page,
        domain=domain,
        subdomain=subdomain,
        difficulty_level=difficulty_level,
        content_hash=generate_content_hash(content),
        keywords=keywords or [],
        concepts=concepts or [],
        **kwargs
    )


# Example usage and testing functions
if __name__ == "__main__":
    # Example of how to use the schema

    # Create ChromaDB client
    client = chromadb.PersistentClient(path="/tmp/chroma_test")
    manager = ChromaDBCollectionManager(client)

    # Create collection
    collection = manager.create_collection(
        user_id="test_user",
        cert_id="aws-saa-c03",
        cert_name="AWS Solutions Architect Associate",
        bundle_version="v1.0"
    )

    # Create sample document metadata
    content = "Amazon EC2 provides resizable compute capacity in the cloud."
    metadata = create_document_metadata(
        content=content,
        user_id="test_user",
        cert_id="aws-saa-c03",
        cert_profile_id=str(uuid.uuid4()),
        bundle_version="v1.0",
        resource_type=ResourceType.EXAM_GUIDE,
        source_file="aws_saa_guide.pdf",
        source_uri="/uploads/aws_saa_guide.pdf",
        mime_type="application/pdf",
        chunk_index=0,
        content_type=ContentType.CONCEPT,
        domain="Design Secure Architectures",
        keywords=["EC2", "compute", "cloud"],
        concepts=["Elastic Compute Cloud", "resizable capacity"]
    )

    # Add document to collection
    manager.add_documents(
        collection=collection,
        documents=[content],
        metadatas=[metadata]
    )

    # Query collection
    results = manager.query_collection(
        collection=collection,
        query_texts=["What is EC2?"],
        user_id="test_user",
        cert_id="aws-saa-c03",
        bundle_version="v1.0",
        resource_types=[ResourceType.EXAM_GUIDE],
        n_results=5
    )

    print(f"Query results: {results}")