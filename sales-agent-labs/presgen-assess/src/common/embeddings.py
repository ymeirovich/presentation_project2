"""Shared OpenAI embedding function for ChromaDB.

This module provides a single, unified implementation of the OpenAI embedding
function to be used by both file upload (chromadb_schema.py) and RAG retrieval
(embeddings.py) systems. Having a single implementation prevents segfaults that
occur when ChromaDB tries to use collections created with one embedding function
instance and queried with a different instance (even if they're the same class).
"""

import logging
import math
from typing import List

from openai import OpenAI

logger = logging.getLogger(__name__)


class OpenAIEmbeddingFunctionV1:
    """Custom OpenAI embedding function compatible with OpenAI v1.0+ API.

    This is the canonical implementation used throughout the presgen-assess system.
    Both ChromaDBCollectionManager and VectorDatabaseManager should import this
    class from this module to ensure compatibility.
    """

    def __init__(self, api_key: str, model_name: str = "text-embedding-3-small"):
        """Initialize with OpenAI client.

        Args:
            api_key: OpenAI API key
            model_name: OpenAI embedding model name (default: text-embedding-3-small)
        """
        self.model_name = model_name
        self.client = None

        if api_key:
            try:
                self.client = OpenAI(api_key=api_key)
                logger.info(f"✅ OpenAI embedding function initialized: {model_name}")
            except Exception as exc:
                logger.warning(
                    f"⚠️ OpenAI client initialization failed ({exc}). "
                    "Will fall back to simple embeddings."
                )
        else:
            logger.warning("⚠️ No OpenAI API key provided. Using fallback embeddings.")

    def __call__(self, input_texts: List[str]) -> List[List[float]]:
        """Generate embeddings for input texts.

        Args:
            input_texts: List of text strings to embed

        Returns:
            List of embedding vectors (each is a list of floats)
        """
        if self.client is None:
            logger.warning("⚠️ No OpenAI client available, using simple embeddings")
            return [self._simple_embedding(text) for text in input_texts]

        try:
            response = self.client.embeddings.create(
                input=input_texts,
                model=self.model_name
            )
            return [data.embedding for data in response.data]
        except Exception as e:
            logger.warning(
                f"⚠️ OpenAI embedding failed ({e}). "
                "Falling back to simple embedding function."
            )
            return [self._simple_embedding(text) for text in input_texts]

    @staticmethod
    def _simple_embedding(text: str, dim: int = 128) -> List[float]:
        """Generate a deterministic hash-based embedding as a fallback.

        This is used when OpenAI API is not available. Note that this produces
        128-dimensional vectors, which is incompatible with collections created
        using OpenAI embeddings (1536 dimensions for text-embedding-3-small).

        Args:
            text: Input text to embed
            dim: Embedding dimension (default: 128)

        Returns:
            Normalized embedding vector
        """
        vector = [0.0] * dim
        if not text:
            return vector

        encoded = text.encode("utf-8", errors="ignore")
        for idx, byte in enumerate(encoded):
            vector[idx % dim] += (byte / 255.0)

        # Normalize
        norm = math.sqrt(sum(v * v for v in vector)) or 1.0
        return [v / norm for v in vector]
