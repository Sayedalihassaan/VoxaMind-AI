import logging
import numpy as np
from typing import Optional

from server.config.settings import settings
from server.cache.redis_cache import cache

logger = logging.getLogger(__name__)


class EmbeddingClient:
    """
    Generates embeddings using Ollama's nomic-embed-text model.
    Falls back to sentence-transformers if Ollama is unavailable.
    """

    def __init__(self):
        self._fallback_model = None

    async def embed(self, text: str) -> np.ndarray:
        """Get embedding for a single text."""
        # Check cache
        cache_key = cache.hash_key(text)
        cached = await cache.get("embeddings", cache_key)
        if cached:
            return np.array(cached, dtype=np.float32)

        vector = await self._embed_with_ollama(text)

        if vector is None:
            vector = self._embed_with_sentence_transformers(text)

        # Normalize
        norm = np.linalg.norm(vector)
        if norm > 0:
            vector = vector / norm

        # Cache embedding for 7 days
        await cache.set("embeddings", cache_key, vector.tolist(), ttl=604800)

        return vector

    async def embed_batch(self, texts: list[str]) -> list[np.ndarray]:
        """Embed a list of texts."""
        results = []
        for text in texts:
            emb = await self.embed(text)
            results.append(emb)
        return results

    async def _embed_with_ollama(self, text: str) -> Optional[np.ndarray]:
        try:
            from server.llm.ollama_client import ollama_client
            vector = await ollama_client.embed(text)
            return np.array(vector, dtype=np.float32)
        except Exception as e:
            logger.warning(f"Ollama embedding failed: {e}. Falling back to sentence-transformers.")
            return None

    def _embed_with_sentence_transformers(self, text: str) -> np.ndarray:
        if self._fallback_model is None:
            try:
                from sentence_transformers import SentenceTransformer
                self._fallback_model = SentenceTransformer("all-MiniLM-L6-v2")
                logger.info("Loaded sentence-transformers fallback model")
            except ImportError:
                logger.error("sentence-transformers not installed. Run: pip install sentence-transformers")
                # Return random vector as last resort
                return np.random.randn(settings.EMBEDDING_DIM).astype(np.float32)

        vector = self._fallback_model.encode(text, normalize_embeddings=True)
        return vector.astype(np.float32)


# Singleton
embedding_client = EmbeddingClient()
