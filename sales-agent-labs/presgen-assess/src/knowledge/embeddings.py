"""Vector database management with ChromaDB for PresGen-Assess."""

import asyncio
import hashlib
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from uuid import uuid4

import chromadb
from chromadb.config import Settings
from chromadb.utils import embedding_functions
from openai import OpenAI

from src.common.config import settings

logger = logging.getLogger(__name__)


class OpenAIEmbeddingFunctionV1:
    """Custom OpenAI embedding function compatible with OpenAI v1.0+ API."""

    def __init__(self, api_key: str, model_name: str = "text-embedding-3-small"):
        """Initialize with OpenAI client."""
        self.client = OpenAI(api_key=api_key)
        self.model_name = model_name

    def __call__(self, input_texts: List[str]) -> List[List[float]]:
        """Generate embeddings for input texts."""
        try:
            response = self.client.embeddings.create(
                input=input_texts,
                model=self.model_name
            )
            return [data.embedding for data in response.data]
        except Exception as e:
            logger.error(f"❌ OpenAI embedding failed: {e}")
            raise


class VectorDatabaseManager:
    """Manages ChromaDB vector database operations with dual-stream support."""

    def __init__(self):
        """Initialize ChromaDB client and collections."""
        self.chroma_path = Path(settings.chroma_db_path)
        self.chroma_path.mkdir(parents=True, exist_ok=True)

        # Initialize ChromaDB client with new configuration format
        self.client = chromadb.PersistentClient(
            path=str(self.chroma_path)
        )

        # Set up OpenAI embedding function (compatible with OpenAI v1.0+)
        self.embedding_function = OpenAIEmbeddingFunctionV1(
            api_key=settings.openai_api_key,
            model_name="text-embedding-3-small"
        )

        # Collections for dual-stream architecture
        self.exam_guides_collection = None
        self.transcripts_collection = None
        self._initialize_collections()

    def _initialize_collections(self):
        """Initialize the dual-stream collections."""
        try:
            # Collection for official exam guides
            self.exam_guides_collection = self.client.get_or_create_collection(
                name="certification_exam_guides",
                embedding_function=self.embedding_function,
                metadata={"content_type": "exam_guide", "description": "Official certification exam guides"}
            )

            # Collection for course transcripts
            self.transcripts_collection = self.client.get_or_create_collection(
                name="certification_transcripts",
                embedding_function=self.embedding_function,
                metadata={"content_type": "transcript", "description": "Curated course transcripts"}
            )

            logger.info("✅ ChromaDB collections initialized successfully")

        except Exception as e:
            logger.error(f"❌ Failed to initialize ChromaDB collections: {e}")
            raise

    async def store_document_chunks(
        self,
        chunks: List[str],
        metadata: List[Dict],
        content_classification: str = "exam_guide"
    ) -> bool:
        """Store processed document chunks with metadata and source attribution."""
        try:
            # Choose collection based on content classification
            if content_classification == "exam_guide":
                collection = self.exam_guides_collection
            elif content_classification == "transcript":
                collection = self.transcripts_collection
            else:
                logger.warning(f"Unknown content classification: {content_classification}, defaulting to exam_guide")
                collection = self.exam_guides_collection

            # Generate unique IDs for chunks
            chunk_ids = [f"{content_classification}_{uuid4()}" for _ in chunks]

            # Filter out None values from metadata (ChromaDB doesn't support None values)
            clean_metadata = []
            for meta in metadata:
                clean_meta = {k: v for k, v in meta.items() if v is not None}
                clean_metadata.append(clean_meta)

            # Add chunks to the appropriate collection
            collection.add(
                documents=chunks,
                metadatas=clean_metadata,
                ids=chunk_ids
            )

            logger.info(
                f"✅ Stored {len(chunks)} chunks in {content_classification} collection"
            )
            return True

        except Exception as e:
            logger.error(f"❌ Failed to store chunks: {e}")
            return False

    async def retrieve_context(
        self,
        query: str,
        certification_id: str,
        k: int = 5,
        content_types: Optional[List[str]] = None,
        include_sources: bool = True
    ) -> List[Dict]:
        """Retrieve relevant context with source attribution for RAG."""
        try:
            results = []

            # Default to both content types if not specified
            if content_types is None:
                content_types = ["exam_guide", "transcript"]

            # Search in exam guides collection
            if "exam_guide" in content_types:
                exam_results = self.exam_guides_collection.query(
                    query_texts=[query],
                    n_results=k // 2 if len(content_types) > 1 else k,
                    where={"certification_id": certification_id}
                )

                # Format exam guide results
                for i, doc in enumerate(exam_results["documents"][0]):
                    result = {
                        "content": doc,
                        "source_type": "exam_guide",
                        "metadata": exam_results["metadatas"][0][i],
                        "distance": exam_results["distances"][0][i],
                        "id": exam_results["ids"][0][i]
                    }
                    if include_sources:
                        result["citation"] = self._generate_citation(
                            exam_results["metadatas"][0][i], "exam_guide"
                        )
                    results.append(result)

            # Search in transcripts collection
            if "transcript" in content_types:
                transcript_results = self.transcripts_collection.query(
                    query_texts=[query],
                    n_results=k // 2 if len(content_types) > 1 else k,
                    where={"certification_id": certification_id}
                )

                # Format transcript results
                for i, doc in enumerate(transcript_results["documents"][0]):
                    result = {
                        "content": doc,
                        "source_type": "transcript",
                        "metadata": transcript_results["metadatas"][0][i],
                        "distance": transcript_results["distances"][0][i],
                        "id": transcript_results["ids"][0][i]
                    }
                    if include_sources:
                        result["citation"] = self._generate_citation(
                            transcript_results["metadatas"][0][i], "transcript"
                        )
                    results.append(result)

            # Sort by relevance (distance) and return top k
            results.sort(key=lambda x: x["distance"])
            return results[:k]

        except Exception as e:
            logger.error(f"❌ Failed to retrieve context: {e}")
            return []

    def _generate_citation(self, metadata: Dict, source_type: str) -> str:
        """Generate a proper citation for source attribution."""
        document_name = metadata.get("document_name", "Unknown Document")
        chunk_index = metadata.get("chunk_index", 0)
        page_number = metadata.get("source_page", "Unknown")

        if source_type == "exam_guide":
            return f"Exam Guide: {document_name} (Section {chunk_index}, Page {page_number})"
        elif source_type == "transcript":
            return f"Course Transcript: {document_name} (Segment {chunk_index})"
        else:
            return f"Source: {document_name} (Chunk {chunk_index})"

    async def get_collection_stats(self) -> Dict:
        """Get statistics about the vector collections."""
        try:
            exam_count = self.exam_guides_collection.count()
            transcript_count = self.transcripts_collection.count()

            return {
                "exam_guides_count": exam_count,
                "transcripts_count": transcript_count,
                "total_chunks": exam_count + transcript_count,
                "collections": {
                    "exam_guides": {
                        "count": exam_count,
                        "metadata": self.exam_guides_collection.metadata
                    },
                    "transcripts": {
                        "count": transcript_count,
                        "metadata": self.transcripts_collection.metadata
                    }
                }
            }

        except Exception as e:
            logger.error(f"❌ Failed to get collection stats: {e}")
            return {}

    async def delete_documents_by_certification(self, certification_id: str) -> bool:
        """Delete all documents for a specific certification."""
        try:
            # Delete from exam guides collection
            exam_results = self.exam_guides_collection.get(
                where={"certification_id": certification_id}
            )
            if exam_results["ids"]:
                self.exam_guides_collection.delete(ids=exam_results["ids"])

            # Delete from transcripts collection
            transcript_results = self.transcripts_collection.get(
                where={"certification_id": certification_id}
            )
            if transcript_results["ids"]:
                self.transcripts_collection.delete(ids=transcript_results["ids"])

            logger.info(f"✅ Deleted documents for certification: {certification_id}")
            return True

        except Exception as e:
            logger.error(f"❌ Failed to delete documents: {e}")
            return False

    async def search_similar_chunks(
        self,
        content: str,
        certification_id: str,
        threshold: float = 0.8
    ) -> List[Dict]:
        """Search for similar chunks to avoid duplicates."""
        try:
            # Search in both collections
            all_results = []

            for collection, collection_name in [
                (self.exam_guides_collection, "exam_guides"),
                (self.transcripts_collection, "transcripts")
            ]:
                results = collection.query(
                    query_texts=[content],
                    n_results=5,
                    where={"certification_id": certification_id}
                )

                for i, doc in enumerate(results["documents"][0]):
                    if results["distances"][0][i] < (1 - threshold):  # ChromaDB uses cosine distance
                        all_results.append({
                            "content": doc,
                            "collection": collection_name,
                            "similarity": 1 - results["distances"][0][i],
                            "metadata": results["metadatas"][0][i]
                        })

            return all_results

        except Exception as e:
            logger.error(f"❌ Failed to search similar chunks: {e}")
            return []

    def generate_content_hash(self, content: str) -> str:
        """Generate a hash for content deduplication."""
        return hashlib.sha256(content.encode()).hexdigest()

    async def health_check(self) -> Dict:
        """Check the health of the vector database."""
        try:
            # Test basic operations
            test_query = "test query"

            # Check if collections are accessible
            exam_accessible = self.exam_guides_collection.count() >= 0
            transcript_accessible = self.transcripts_collection.count() >= 0

            # Test embedding function
            try:
                test_embedding = await asyncio.get_event_loop().run_in_executor(
                    None, lambda: self.embedding_function([test_query])
                )
                embedding_working = len(test_embedding) > 0
            except Exception:
                embedding_working = False

            return {
                "status": "healthy" if all([exam_accessible, transcript_accessible, embedding_working]) else "unhealthy",
                "exam_guides_collection": exam_accessible,
                "transcripts_collection": transcript_accessible,
                "embedding_function": embedding_working,
                "chroma_path": str(self.chroma_path),
                "stats": await self.get_collection_stats()
            }

        except Exception as e:
            logger.error(f"❌ Vector database health check failed: {e}")
            return {
                "status": "unhealthy",
                "error": str(e)
            }