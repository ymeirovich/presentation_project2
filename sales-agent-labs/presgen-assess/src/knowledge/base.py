"""Base knowledge management service integrating document processing and vector storage."""

import asyncio
import logging
from pathlib import Path
from typing import Dict, List, Optional
from uuid import UUID

from src.knowledge.documents import DocumentProcessor
from src.knowledge.embeddings import VectorDatabaseManager
from src.common.config import settings

logger = logging.getLogger(__name__)


class RAGKnowledgeBase:
    """Central RAG knowledge base implementation with dual-stream architecture."""

    def __init__(self):
        """Initialize the RAG knowledge base with document processor and vector database."""
        self.document_processor = DocumentProcessor()
        self.vector_manager = VectorDatabaseManager()
        self.knowledge_base_path = Path(settings.chroma_db_path).parent
        self.knowledge_base_path.mkdir(parents=True, exist_ok=True)

    async def ingest_certification_materials(
        self,
        certification_id: str,
        documents: List[Dict],
        content_classification: str = "exam_guide"
    ) -> Dict:
        """Process and ingest certification materials with full pipeline."""
        try:
            ingestion_results = {
                "certification_id": certification_id,
                "content_classification": content_classification,
                "processed_documents": [],
                "failed_documents": [],
                "total_chunks": 0,
                "success": True
            }

            logger.info(
                f"🚀 Starting ingestion for certification {certification_id} "
                f"({len(documents)} documents, type: {content_classification})"
            )

            for doc_info in documents:
                file_path = Path(doc_info["file_path"])
                original_filename = doc_info.get("original_filename", file_path.name)

                try:
                    # Validate file before processing
                    is_valid, error_msg = self.document_processor.validate_file(file_path)
                    if not is_valid:
                        ingestion_results["failed_documents"].append({
                            "filename": original_filename,
                            "error": error_msg
                        })
                        continue

                    # Process document into chunks
                    processing_result = await self.document_processor.process_certification_document(
                        file_path=file_path,
                        certification_id=certification_id,
                        content_classification=content_classification,
                        original_filename=original_filename
                    )

                    if not processing_result["success"]:
                        ingestion_results["failed_documents"].append({
                            "filename": original_filename,
                            "error": processing_result["error"]
                        })
                        continue

                    # Store chunks in vector database
                    chunks = processing_result["chunks"]
                    metadata = processing_result["metadata"]

                    storage_success = await self.vector_manager.store_document_chunks(
                        chunks=chunks,
                        metadata=metadata,
                        content_classification=content_classification
                    )

                    if storage_success:
                        ingestion_results["processed_documents"].append({
                            "filename": original_filename,
                            "chunk_count": len(chunks),
                            "file_info": processing_result["file_info"]
                        })
                        ingestion_results["total_chunks"] += len(chunks)
                    else:
                        ingestion_results["failed_documents"].append({
                            "filename": original_filename,
                            "error": "Failed to store chunks in vector database"
                        })

                except Exception as e:
                    logger.error(f"❌ Failed to process document {original_filename}: {e}")
                    ingestion_results["failed_documents"].append({
                        "filename": original_filename,
                        "error": str(e)
                    })

            # Update success status
            if ingestion_results["failed_documents"] and not ingestion_results["processed_documents"]:
                ingestion_results["success"] = False

            logger.info(
                f"✅ Ingestion complete for {certification_id}: "
                f"{len(ingestion_results['processed_documents'])} succeeded, "
                f"{len(ingestion_results['failed_documents'])} failed, "
                f"{ingestion_results['total_chunks']} total chunks"
            )

            return ingestion_results

        except Exception as e:
            logger.error(f"❌ Ingestion pipeline failed: {e}")
            return {
                "certification_id": certification_id,
                "success": False,
                "error": str(e)
            }

    async def retrieve_context_for_assessment(
        self,
        query: str,
        certification_id: str,
        k: int = 5,
        balance_sources: bool = True
    ) -> Dict:
        """Retrieve context for assessment generation with balanced source types."""
        try:
            if balance_sources:
                # Get context from both exam guides and transcripts
                context_results = await self.vector_manager.retrieve_context(
                    query=query,
                    certification_id=certification_id,
                    k=k,
                    content_types=["exam_guide", "transcript"],
                    include_sources=True
                )
            else:
                # Get context from all available sources
                context_results = await self.vector_manager.retrieve_context(
                    query=query,
                    certification_id=certification_id,
                    k=k,
                    include_sources=True
                )

            # Organize results by source type
            exam_guide_sources = [r for r in context_results if r["source_type"] == "exam_guide"]
            transcript_sources = [r for r in context_results if r["source_type"] == "transcript"]

            return {
                "query": query,
                "certification_id": certification_id,
                "total_results": len(context_results),
                "sources": {
                    "exam_guides": {
                        "count": len(exam_guide_sources),
                        "results": exam_guide_sources
                    },
                    "transcripts": {
                        "count": len(transcript_sources),
                        "results": transcript_sources
                    }
                },
                "combined_context": self._format_combined_context(context_results),
                "citations": [r.get("citation") for r in context_results if r.get("citation")]
            }

        except Exception as e:
            logger.error(f"❌ Context retrieval failed: {e}")
            return {
                "query": query,
                "certification_id": certification_id,
                "error": str(e),
                "total_results": 0
            }

    def _format_combined_context(self, context_results: List[Dict]) -> str:
        """Format retrieved context into a coherent string for LLM consumption."""
        if not context_results:
            return ""

        formatted_sections = []

        # Group by source type for better organization
        exam_guides = [r for r in context_results if r["source_type"] == "exam_guide"]
        transcripts = [r for r in context_results if r["source_type"] == "transcript"]

        # Add exam guide content
        if exam_guides:
            formatted_sections.append("=== OFFICIAL EXAM GUIDE CONTENT ===")
            for i, result in enumerate(exam_guides[:3], 1):  # Limit to top 3
                formatted_sections.append(f"\n[Source {i}: {result.get('citation', 'Unknown')}]")
                formatted_sections.append(result["content"])

        # Add transcript content
        if transcripts:
            formatted_sections.append("\n\n=== COURSE TRANSCRIPT CONTENT ===")
            for i, result in enumerate(transcripts[:3], 1):  # Limit to top 3
                formatted_sections.append(f"\n[Source {i}: {result.get('citation', 'Unknown')}]")
                formatted_sections.append(result["content"])

        return "\n".join(formatted_sections)

    async def search_similar_content(
        self,
        content: str,
        certification_id: str,
        threshold: float = 0.8
    ) -> List[Dict]:
        """Search for similar content to avoid duplicates during ingestion."""
        try:
            return await self.vector_manager.search_similar_chunks(
                content=content,
                certification_id=certification_id,
                threshold=threshold
            )
        except Exception as e:
            logger.error(f"❌ Similar content search failed: {e}")
            return []

    async def get_certification_knowledge_stats(self, certification_id: str) -> Dict:
        """Get statistics about knowledge base content for a certification."""
        try:
            # Get overall stats
            overall_stats = await self.vector_manager.get_collection_stats()

            # TODO: Add certification-specific filtering when ChromaDB supports it better
            # For now, return overall stats with certification context
            return {
                "certification_id": certification_id,
                "stats": overall_stats,
                "knowledge_base_path": str(self.knowledge_base_path)
            }

        except Exception as e:
            logger.error(f"❌ Failed to get knowledge stats: {e}")
            return {
                "certification_id": certification_id,
                "error": str(e)
            }

    async def delete_certification_knowledge(self, certification_id: str) -> bool:
        """Delete all knowledge base content for a certification."""
        try:
            success = await self.vector_manager.delete_documents_by_certification(certification_id)
            if success:
                logger.info(f"✅ Deleted knowledge base content for certification: {certification_id}")
            return success

        except Exception as e:
            logger.error(f"❌ Failed to delete certification knowledge: {e}")
            return False

    async def health_check(self) -> Dict:
        """Comprehensive health check of the knowledge base system."""
        try:
            # Check vector database health
            vector_health = await self.vector_manager.health_check()

            # Check document processor
            processor_health = {
                "status": "healthy",
                "supported_types": list(self.document_processor.supported_types.keys()),
                "chunk_config": {
                    "chunk_size": self.document_processor.text_splitter._chunk_size,
                    "chunk_overlap": self.document_processor.text_splitter._chunk_overlap
                }
            }

            # Check file system
            fs_health = {
                "status": "healthy" if self.knowledge_base_path.exists() else "unhealthy",
                "knowledge_base_path": str(self.knowledge_base_path),
                "writable": self.knowledge_base_path.is_dir() and
                          (self.knowledge_base_path / "test_write").parent.exists()
            }

            overall_status = "healthy" if all([
                vector_health.get("status") == "healthy",
                processor_health.get("status") == "healthy",
                fs_health.get("status") == "healthy"
            ]) else "unhealthy"

            return {
                "status": overall_status,
                "components": {
                    "vector_database": vector_health,
                    "document_processor": processor_health,
                    "file_system": fs_health
                },
                "timestamp": self.document_processor._get_current_timestamp()
            }

        except Exception as e:
            logger.error(f"❌ Knowledge base health check failed: {e}")
            return {
                "status": "unhealthy",
                "error": str(e)
            }

    async def bulk_ingest_certification(
        self,
        certification_id: str,
        exam_guides_path: Optional[Path] = None,
        transcripts_path: Optional[Path] = None
    ) -> Dict:
        """Bulk ingest all documents for a certification from directory structure."""
        try:
            results = {
                "certification_id": certification_id,
                "exam_guides_result": None,
                "transcripts_result": None,
                "total_chunks": 0,
                "success": True
            }

            # Process exam guides
            if exam_guides_path and exam_guides_path.exists():
                exam_docs = [
                    {"file_path": str(f), "original_filename": f.name}
                    for f in exam_guides_path.rglob("*")
                    if f.is_file() and not f.name.startswith(".")
                ]

                if exam_docs:
                    results["exam_guides_result"] = await self.ingest_certification_materials(
                        certification_id=certification_id,
                        documents=exam_docs,
                        content_classification="exam_guide"
                    )
                    results["total_chunks"] += results["exam_guides_result"].get("total_chunks", 0)

            # Process transcripts
            if transcripts_path and transcripts_path.exists():
                transcript_docs = [
                    {"file_path": str(f), "original_filename": f.name}
                    for f in transcripts_path.rglob("*")
                    if f.is_file() and not f.name.startswith(".")
                ]

                if transcript_docs:
                    results["transcripts_result"] = await self.ingest_certification_materials(
                        certification_id=certification_id,
                        documents=transcript_docs,
                        content_classification="transcript"
                    )
                    results["total_chunks"] += results["transcripts_result"].get("total_chunks", 0)

            # Update overall success
            results["success"] = all([
                results["exam_guides_result"] is None or results["exam_guides_result"].get("success", True),
                results["transcripts_result"] is None or results["transcripts_result"].get("success", True)
            ])

            logger.info(
                f"✅ Bulk ingestion complete for {certification_id}: {results['total_chunks']} total chunks"
            )

            return results

        except Exception as e:
            logger.error(f"❌ Bulk ingestion failed: {e}")
            return {
                "certification_id": certification_id,
                "success": False,
                "error": str(e)
            }