"""Test RAG retrieval for ACC certification."""

import asyncio
import logging
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.knowledge.base import RAGKnowledgeBase

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_rag_retrieval():
    """Test RAG retrieval with ACC certification."""

    # Initialize knowledge base
    kb = RAGKnowledgeBase()

    # ACC certification ID
    cert_id = "36b36141-0f79-449f-a6bf-b2ec59fddcd1"

    # Test queries
    test_queries = [
        "What are the ICF Core Competencies?",
        "Tell me about coaching ethics",
        "What is required for ACC certification?"
    ]

    logger.info("=" * 60)
    logger.info("Testing RAG Retrieval for ACC Certification")
    logger.info("=" * 60)

    for query in test_queries:
        logger.info(f"\n🔍 Query: {query}")
        logger.info("-" * 60)

        try:
            result = await kb.retrieve_context_for_assessment(
                query=query,
                certification_id=cert_id,
                k=5,
                balance_sources=True
            )

            logger.info(f"✅ Total results: {result['total_results']}")
            logger.info(f"   Exam guides: {result['sources']['exam_guides']['count']}")
            logger.info(f"   Transcripts: {result['sources']['transcripts']['count']}")

            if result.get('error'):
                logger.error(f"❌ Error: {result['error']}")
            elif result['total_results'] > 0:
                # Show first result
                all_sources = (result['sources']['exam_guides']['results'] +
                             result['sources']['transcripts']['results'])
                if all_sources:
                    first = all_sources[0]
                    logger.info(f"\n   First result preview:")
                    logger.info(f"   Source: {first.get('source_file', 'Unknown')}")
                    logger.info(f"   Type: {first.get('source_type', 'Unknown')}")
                    content_preview = first.get('content', '')[:150]
                    logger.info(f"   Content: {content_preview}...")
            else:
                logger.warning("⚠️  No results found!")

        except Exception as e:
            logger.error(f"❌ Exception during retrieval: {e}", exc_info=True)

    logger.info("\n" + "=" * 60)
    logger.info("RAG Retrieval Test Complete")
    logger.info("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_rag_retrieval())
