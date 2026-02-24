import os
import json
import logging
import pickle
import numpy as np
from pathlib import Path
from typing import Optional

from server.config.settings import settings

logger = logging.getLogger(__name__)


class VectorStore:
    """FAISS-backed vector store for document embeddings."""

    def __init__(self, index_path: str = None):
        self.index_path = Path(index_path or settings.FAISS_INDEX_PATH)
        self.index_path.mkdir(parents=True, exist_ok=True)
        self._index = None
        self._documents: list[dict] = []  # parallel list of metadata+content
        self._dim: Optional[int] = None

    def _ensure_faiss(self):
        try:
            import faiss
            return faiss
        except ImportError:
            logger.error("faiss-cpu not installed. Run: pip install faiss-cpu")
            raise

    def initialize(self, dim: int = None) -> None:
        """Initialize or load existing FAISS index."""
        faiss = self._ensure_faiss()
        self._dim = dim or settings.EMBEDDING_DIM

        index_file = self.index_path / "index.faiss"
        docs_file = self.index_path / "documents.pkl"

        if index_file.exists() and docs_file.exists():
            logger.info("Loading existing FAISS index")
            self._index = faiss.read_index(str(index_file))
            with open(docs_file, "rb") as f:
                self._documents = pickle.load(f)
            logger.info(f"Loaded {len(self._documents)} documents")
        else:
            logger.info(f"Creating new FAISS index (dim={self._dim})")
            self._index = faiss.IndexFlatIP(self._dim)  # Inner product (cosine with normalized vectors)

    def add(self, embeddings: list[np.ndarray], documents: list[dict]) -> None:
        """Add embeddings and their associated documents."""
        if self._index is None:
            self.initialize(len(embeddings[0]))

        vectors = np.array(embeddings, dtype=np.float32)
        # Normalize for cosine similarity
        norms = np.linalg.norm(vectors, axis=1, keepdims=True)
        vectors = vectors / (norms + 1e-10)

        self._index.add(vectors)
        self._documents.extend(documents)
        self.save()
        logger.info(f"Added {len(documents)} documents to index (total: {len(self._documents)})")

    def search(self, query_embedding: np.ndarray, top_k: int = None) -> list[dict]:
        """Search for similar documents."""
        if self._index is None or self._index.ntotal == 0:
            return []

        top_k = top_k or settings.RETRIEVAL_TOP_K

        query = np.array([query_embedding], dtype=np.float32)
        norm = np.linalg.norm(query)
        if norm > 0:
            query = query / norm

        distances, indices = self._index.search(query, min(top_k, self._index.ntotal))

        results = []
        for score, idx in zip(distances[0], indices[0]):
            if idx < 0 or idx >= len(self._documents):
                continue
            doc = self._documents[idx].copy()
            doc["score"] = float(score)
            results.append(doc)

        return results

    def save(self) -> None:
        """Persist index and documents to disk."""
        faiss = self._ensure_faiss()
        faiss.write_index(self._index, str(self.index_path / "index.faiss"))
        with open(self.index_path / "documents.pkl", "wb") as f:
            pickle.dump(self._documents, f)

    def clear(self) -> None:
        """Clear the index."""
        faiss = self._ensure_faiss()
        self._index = faiss.IndexFlatIP(self._dim or settings.EMBEDDING_DIM)
        self._documents = []
        self.save()

    @property
    def count(self) -> int:
        return len(self._documents)

    @property
    def initialized(self) -> bool:
        return self._index is not None


# Singleton
vector_store = VectorStore()
