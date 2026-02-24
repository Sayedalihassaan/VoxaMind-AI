import logging
from typing import Optional

from server.rag.vector_store import vector_store
from server.embeddings.embedding_client import embedding_client
from server.config.settings import settings

logger = logging.getLogger(__name__)


class Retriever:
    """Retrieves relevant documents for a query using FAISS similarity search."""

    def __init__(self, top_k: int = None):
        self.top_k = top_k or settings.RETRIEVAL_TOP_K

    async def retrieve(self, query: str, top_k: int = None) -> list[dict]:
        """
        Retrieve relevant documents for a query.
        Returns list of {"content", "source", "score"} dicts.
        """
        if not vector_store.initialized or vector_store.count == 0:
            logger.debug("Vector store is empty or not initialized")
            return []

        try:
            query_embedding = await embedding_client.embed(query)
            results = vector_store.search(query_embedding, top_k or self.top_k)

            # Filter low-relevance results
            filtered = [r for r in results if r.get("score", 0) > 0.3]

            return [
                {
                    "content": r.get("content", ""),
                    "source": r.get("metadata", {}).get("source", "unknown"),
                    "score": r.get("score", 0),
                }
                for r in filtered
            ]
        except Exception as e:
            logger.error(f"Retrieval error: {e}")
            return []

    async def retrieve_formatted(self, query: str, top_k: int = None) -> str:
        """Retrieve and format results as a context string."""
        docs = await self.retrieve(query, top_k)
        if not docs:
            return ""

        parts = []
        for doc in docs:
            parts.append(f"[{doc['source']}]\n{doc['content']}")

        return "\n\n---\n\n".join(parts)


# Singleton
retriever = Retriever()
