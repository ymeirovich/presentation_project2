"""Reprocess failed ACC knowledge base documents."""

import asyncio
import logging
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.knowledge.base import RAGKnowledgeBase
from src.service.database import AsyncSessionLocal

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def reprocess_failed_documents():
    """Reprocess the two failed ACC documents."""

    # Initialize knowledge base
    kb = RAGKnowledgeBase()

    # Define the ACC certification ID
    cert_id = "36b36141-0f79-449f-a6bf-b2ec59fddcd1"

    # Documents to reprocess
    documents = [
        {
            "file_path": "uploads/transcripts/a86ffe08-db49-4583-98d1-bd98450b6018.txt",
            "original_filename": "ACC ICF Preparation transcript.txt",
            "classification": "transcript",
            "doc_id": "a86ffe08-db49-4583-98d1-bd98450b6018"
        },
        {
            "file_path": "uploads/exam_guides/a2670d30-5ebf-4779-a70a-d661157c8981.txt",
            "original_filename": "ACC Exam Preparation Study Guide.txt",
            "classification": "exam_guide",
            "doc_id": "a2670d30-5ebf-4779-a70a-d661157c8981"
        }
    ]

    logger.info("=" * 60)
    logger.info("Starting reprocessing of failed ACC documents")
    logger.info("=" * 60)

    for doc in documents:
        file_path = Path(doc["file_path"])

        if not file_path.exists():
            logger.error(f"❌ File not found: {file_path}")
            continue

        logger.info(f"\n📄 Processing: {doc['original_filename']}")
        logger.info(f"   Path: {file_path}")
        logger.info(f"   Type: {doc['classification']}")

        try:
            # Process the document through the knowledge base
            result = await kb.ingest_certification_materials(
                certification_id=cert_id,
                documents=[{
                    "file_path": str(file_path),
                    "original_filename": doc["original_filename"]
                }],
                content_classification=doc["classification"]
            )

            if result["success"]:
                logger.info(f"✅ Successfully processed {doc['original_filename']}")
                logger.info(f"   Total chunks: {result['total_chunks']}")
                logger.info(f"   Processed documents: {len(result['processed_documents'])}")
            else:
                logger.error(f"❌ Failed to process {doc['original_filename']}")
                logger.error(f"   Errors: {result.get('failed_documents', [])}")

        except Exception as e:
            logger.error(f"❌ Exception processing {doc['original_filename']}: {e}", exc_info=True)

    logger.info("\n" + "=" * 60)
    logger.info("Reprocessing complete")
    logger.info("=" * 60)

    # Verify the results
    logger.info("\n📊 Verifying results in database...")

    async with AsyncSessionLocal() as db:
        from src.models.knowledge_base import KnowledgeBaseDocument
        from sqlalchemy import select

        stmt = select(KnowledgeBaseDocument).where(
            KnowledgeBaseDocument.certification_profile_id == cert_id,
            KnowledgeBaseDocument.original_filename.like('%ACC%')
        )
        result = await db.execute(stmt)
        docs = result.scalars().all()

        for doc in docs:
            logger.info(f"   {doc.original_filename}: {doc.processing_status} (chunks: {doc.chunk_count})")


if __name__ == "__main__":
    asyncio.run(reprocess_failed_documents())
