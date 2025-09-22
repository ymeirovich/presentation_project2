"""FastAPI dependencies for PresGen-Assess."""

import logging
from functools import lru_cache

from src.knowledge.base import RAGKnowledgeBase

logger = logging.getLogger(__name__)


@lru_cache()
def get_knowledge_base() -> RAGKnowledgeBase:
    """Get singleton instance of RAG knowledge base."""
    try:
        return RAGKnowledgeBase()
    except Exception as e:
        logger.error(f"❌ Failed to initialize knowledge base: {e}")
        raise


# Global instance for reuse
_knowledge_base = None


def get_knowledge_base_instance() -> RAGKnowledgeBase:
    """Get cached knowledge base instance."""
    global _knowledge_base
    if _knowledge_base is None:
        _knowledge_base = RAGKnowledgeBase()
    return _knowledge_base