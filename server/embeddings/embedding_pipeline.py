import logging
from typing import Optional
import numpy as np

from server.embeddings.embedding_client import embedding_client
from server.config.settings import settings

logger = logging.getLogger(__name__)


class EmbeddingPipeline:
    """Pipeline for embedding documents in batches with chunking."""

    def __init__(self, chunk_size: int = None, chunk_overlap: int = None):
        self.chunk_size = chunk_size or settings.CHUNK_SIZE
        self.chunk_overlap = chunk_overlap or settings.CHUNK_OVERLAP

    def chunk_text(self, text: str) -> list[str]:
        """Split text into overlapping chunks."""
        words = text.split()
        chunks = []
        i = 0
        while i < len(words):
            chunk_words = words[i:i + self.chunk_size]
            chunks.append(" ".join(chunk_words))
            if i + self.chunk_size >= len(words):
                break
            i += self.chunk_size - self.chunk_overlap
        return chunks

    async def process_document(
        self,
        text: str,
        metadata: dict = None,
    ) -> list[dict]:
        """
        Process a document into embedded chunks.
        Returns list of {"content", "embedding", "metadata"} dicts.
        """
        chunks = self.chunk_text(text)
        results = []

        for i, chunk in enumerate(chunks):
            if not chunk.strip():
                continue
            embedding = await embedding_client.embed(chunk)
            results.append({
                "content": chunk,
                "embedding": embedding,
                "metadata": {
                    **(metadata or {}),
                    "chunk_index": i,
                    "total_chunks": len(chunks),
                },
            })

        logger.info(f"Processed {len(chunks)} chunks from document")
        return results

    async def process_documents(self, documents: list[dict]) -> list[dict]:
        """
        Process multiple documents.
        Each document should have 'content' and optionally 'metadata'.
        """
        all_chunks = []
        for doc in documents:
            chunks = await self.process_document(
                doc["content"],
                metadata=doc.get("metadata", {}),
            )
            all_chunks.extend(chunks)
        return all_chunks


embedding_pipeline = EmbeddingPipeline()
