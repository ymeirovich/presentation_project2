"""Vector database management with ChromaDB for PresGen-Assess."""

import asyncio
import hashlib
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from uuid import uuid4

import chromadb
from chromadb.config import Settings

from src.common.config import settings
from src.common.embeddings import OpenAIEmbeddingFunctionV1
from src.common.logging_config import get_assessment_logger

# ✅ FIX: Use assessment logger so logs appear in assessments.log and combined log
logger = get_assessment_logger()


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

    async def _get_cert_slug(self, certification_id: str) -> Optional[str]:
        """Get the certification slug/collection_name from UUID."""
        try:
            from src.service.database import AsyncSessionLocal
            from src.models.certification import CertificationProfile
            from sqlalchemy import select, text

            async with AsyncSessionLocal() as session:
                # Remove hyphens from UUID if present for database lookup
                cert_id_normalized = certification_id.replace('-', '')

                # Use text-based query since the ID is stored as a string in SQLite
                stmt = select(CertificationProfile).where(
                    text(f"id = '{cert_id_normalized}'")
                )
                result = await session.execute(stmt)
                cert_profile = result.scalar_one_or_none()

                if cert_profile and cert_profile.collection_name:
                    logger.debug(
                        f"🔍 Resolved cert UUID {certification_id} -> slug '{cert_profile.collection_name}'"
                    )
                    return cert_profile.collection_name

                logger.debug(
                    f"📝 No cert_slug mapping found for certification_id={certification_id} - will use UUID as-is"
                )
                return None

        except Exception as e:
            logger.warning(
                f"⚠️ Failed to lookup cert_slug for {certification_id}: {e}"
            )
            return None

    def _find_cert_collection(self, cert_slug: str):
        """Locate per-certification collection created by ChromaDBCollectionManager."""
        try:
            target_prefix = f"assess__{cert_slug}_"
            logger.info(f"🔍 Looking for collection with prefix: {target_prefix}")

            all_collections = self.client.list_collections()
            logger.info(f"📚 Available collections: {[c.name for c in all_collections]}")

            for collection in all_collections:
                if collection.name.startswith(target_prefix):
                    logger.info(f"✅ Found matching collection: {collection.name}")
                    # CRITICAL: We must attach the correct embedding function for queries
                    # The collection was created with OpenAIEmbeddingFunctionV1, so we
                    # attach the same embedding function type here
                    try:
                        collection_with_embed = self.client.get_collection(
                            name=collection.name,
                            embedding_function=self.embedding_function
                        )
                        logger.info(f"✅ Successfully attached embedding function to {collection.name}")
                        return collection_with_embed
                    except Exception as exc:
                        logger.error(
                            f"❌ Failed to attach embedding function to {collection.name}: {exc}"
                        )
                        # Return collection without embedding function as fallback
                        # This will use default embeddings (384 dim) and may fail queries
                        logger.warning(f"⚠️ Returning collection without embedding function - queries may fail")
                        return collection

            logger.warning(f"⚠️ No collection found with prefix {target_prefix}")
        except Exception as exc:
            logger.warning(f"⚠️ Unable to list collections for cert {cert_slug}: {exc}")
        return None
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
            # ✅ FIX: Look up cert_slug from certification UUID
            cert_slug = await self._get_cert_slug(certification_id)
            if not cert_slug:
                logger.debug(
                    f"📝 No cert_slug mapping for {certification_id}, using certification_id directly"
                )
                cert_slug = certification_id  # Fallback to UUID (this is expected and works correctly)

            # ✅ PHASE 1 FIX: Log RAG retrieval parameters
            logger.info(
                f"🔍 RAG retrieve_context | certification_id={certification_id} | "
                f"cert_slug={cert_slug} | query={query[:100]}... | k={k} | content_types={content_types}"
            )

            results = []

            # Default to both content types if not specified
            if content_types is None:
                content_types = ["exam_guide", "transcript"]

            def _query_with_fallback(collection, n_results: int, collection_name: str, resource_type: Optional[str] = None):
                """Query collection using standardized cert_id metadata key."""
                logger.info(
                    f"🔍 Querying {collection_name} collection | "
                    f"where={{cert_id: {cert_slug}}} | n_results={n_results}"
                )

                # Build where clause with proper AND operator for multiple conditions
                if resource_type:
                    where_clause = {
                        "$and": [
                            {"cert_id": cert_slug},
                            {"resource_type": resource_type}
                        ]
                    }
                else:
                    where_clause = {"cert_id": cert_slug}

                primary_results = collection.query(
                    query_texts=[query],
                    n_results=n_results,
                    where=where_clause
                )
                docs = primary_results.get("documents") or []
                metadatas = primary_results.get("metadatas") or []

                # ✅ PHASE 1 FIX: Log query results
                result_count = len(docs[0]) if docs and docs[0] else 0
                logger.info(
                    f"📊 Query returned {result_count} chunks from {collection_name} | "
                    f"cert_slug={cert_slug}"
                )

                if docs and docs[0]:
                    # Log first result's metadata for verification
                    if metadatas and metadatas[0]:
                        first_meta = metadatas[0][0] if metadatas[0] else {}
                        logger.info(
                            f"📋 First chunk metadata: cert_id={first_meta.get('cert_id')} | "
                            f"doc={first_meta.get('document_name')} | "
                            f"classification={first_meta.get('content_classification')}"
                        )
                    return primary_results

                # Fallback to certification_id (UUID) for dual-stream collections
                logger.warning(
                    f"⚠️ No results with cert_id={cert_slug}, trying certification_id fallback | "
                    f"collection={collection_name} | certification_id={certification_id}"
                )
                # Build legacy where clause with proper AND operator
                if resource_type:
                    legacy_where = {
                        "$and": [
                            {"certification_id": certification_id},
                            {"resource_type": resource_type}
                        ]
                    }
                else:
                    legacy_where = {"certification_id": certification_id}

                legacy_results = collection.query(
                    query_texts=[query],
                    n_results=n_results,
                    where=legacy_where
                )
                legacy_docs = legacy_results.get("documents") or []
                if legacy_docs and legacy_docs[0]:
                    logger.info(
                        f"✅ RAG retrieval using certification_id fallback | "
                        f"certification_id={certification_id} | collection={collection_name}"
                    )
                    return legacy_results

                # No results from either key
                logger.warning(
                    f"⚠️ No chunks found for cert_id={cert_slug} or certification_id={certification_id} in {collection_name}"
                )
                return {"documents": [], "metadatas": []}

            def _format_results(collection_name: str, chroma_results: Dict, source_type: str):
                documents = chroma_results.get("documents") or []
                metadatas = chroma_results.get("metadatas") or []
                distances = chroma_results.get("distances") or []
                ids = chroma_results.get("ids") or []

                if not documents or not documents[0]:
                    return

                # ✅ PHASE 1 FIX: Track validation statistics
                total_chunks = len(documents[0])
                passed_chunks = 0
                failed_chunks = 0
                missing_meta_chunks = 0

                for i, doc in enumerate(documents[0]):
                    metadata = metadatas[0][i] if metadatas and metadatas[0] else {}
                    metadata = metadata or {}
                    # ✅ PHASE 1 FIX: Check certification_id first (primary key)
                    metadata_cert = metadata.get("cert_id") or metadata.get("certification_id") or metadata.get("cert_profile_id")
                    chunk_id = ids[0][i] if ids and ids[0] else None

                    if not metadata_cert:
                        missing_meta_chunks += 1
                        logger.warning(
                            f"⚠️ RAG chunk missing certification metadata | "
                            f"expected={certification_id} | chunk_id={chunk_id} | "
                            f"source_type={source_type} | collection={collection_name}"
                        )
                        continue

                    # ✅ FIX: Accept EITHER UUID or slug match
                    # metadata_cert could be UUID or slug, certification_id is UUID, cert_slug is slug
                    is_match = (metadata_cert == certification_id or metadata_cert == cert_slug)

                    if not is_match:
                        failed_chunks += 1
                        logger.error(
                            f"🚨 CRITICAL: RAG certification mismatch! | "
                            f"expected_uuid={certification_id} | expected_slug={cert_slug} | actual={metadata_cert} | "
                            f"chunk_id={chunk_id} | doc={metadata.get('document_name')} | "
                            f"source_type={source_type} | collection={collection_name}"
                        )
                        continue

                    passed_chunks += 1
                    result = {
                        "content": doc,
                        "source_type": source_type,
                        "metadata": metadata,
                        "distance": distances[0][i] if distances and distances[0] else None,
                        "id": chunk_id,
                    }
                    if include_sources:
                        result["citation"] = self._generate_citation(metadata, source_type)
                    results.append(result)

                # ✅ PHASE 1 FIX: Log validation summary
                logger.info(
                    f"✅ RAG chunk validation | collection={collection_name} | "
                    f"total={total_chunks} | passed={passed_chunks} | "
                    f"failed_mismatch={failed_chunks} | missing_metadata={missing_meta_chunks} | "
                    f"cert_id={certification_id}"
                )

            per_cert_collection = self._find_cert_collection(cert_slug)

            if per_cert_collection:
                logger.info(
                    f"📚 Found per-certification collection '{per_cert_collection.name}' for {cert_slug} (cert_id={certification_id})"
                )
                if "exam_guide" in content_types:
                    exam_results = _query_with_fallback(
                        per_cert_collection,
                        k // 2 if len(content_types) > 1 else k,
                        f"{per_cert_collection.name} (exam_guides)",
                        resource_type="exam_guide"
                    )
                    _format_results(per_cert_collection.name, exam_results, "exam_guide")

                if "transcript" in content_types:
                    transcript_results = _query_with_fallback(
                        per_cert_collection,
                        k // 2 if len(content_types) > 1 else k,
                        f"{per_cert_collection.name} (transcripts)",
                        resource_type="transcript"
                    )
                    _format_results(per_cert_collection.name, transcript_results, "transcript")
            else:
                # Fallback to dual-stream collections
                if "exam_guide" in content_types:
                    exam_results = _query_with_fallback(
                        self.exam_guides_collection,
                        k // 2 if len(content_types) > 1 else k,
                        "exam_guides"
                    )
                    _format_results("exam_guides", exam_results, "exam_guide")

                if "transcript" in content_types:
                    transcript_results = _query_with_fallback(
                        self.transcripts_collection,
                        k // 2 if len(content_types) > 1 else k,
                        "transcripts"
                    )
                    _format_results("transcripts", transcript_results, "transcript")

            # ✅ PHASE 1 FIX: Log final retrieval summary
            if not results:
                logger.warning(
                    f"⚠️ RAG retrieval returned NO chunks after certification filtering | "
                    f"certification_id={certification_id} | query={query[:100]}... | "
                    f"content_types={content_types}"
                )
            else:
                # Group results by source for summary
                exam_guide_count = sum(1 for r in results if r.get("source_type") == "exam_guide")
                transcript_count = sum(1 for r in results if r.get("source_type") == "transcript")
                unique_docs = set(r.get("metadata", {}).get("document_name") for r in results)

                logger.info(
                    f"✅ RAG retrieval complete | certification_id={certification_id} | "
                    f"total_chunks={len(results)} | exam_guides={exam_guide_count} | "
                    f"transcripts={transcript_count} | unique_docs={len(unique_docs)} | "
                    f"docs={list(unique_docs)[:3]}"
                )

            # Sort by relevance (distance) and return top k
            results.sort(key=lambda x: x["distance"] if x["distance"] is not None else float('inf'))
            final_results = results[:k]

            logger.info(
                f"📤 Returning top {len(final_results)} chunks (requested k={k}) | "
                f"certification_id={certification_id}"
            )

            return final_results

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
                where={"cert_id": certification_id}
            )
            if exam_results["ids"]:
                self.exam_guides_collection.delete(ids=exam_results["ids"])

            # Delete from transcripts collection
            transcript_results = self.transcripts_collection.get(
                where={"cert_id": certification_id}
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
                    where={"cert_id": certification_id}
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
