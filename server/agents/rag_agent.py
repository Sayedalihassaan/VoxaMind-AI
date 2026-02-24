import logging
from pathlib import Path

from server.rag.vector_store import vector_store
from server.rag.retriever import retriever
from server.rag.document_loader import document_loader
from server.embeddings.embedding_pipeline import embedding_pipeline
from server.config.settings import settings

logger = logging.getLogger(__name__)


class RAGAgent:
    """Manages document ingestion and retrieval for RAG."""

    async def initialize(self) -> None:
        """Initialize vector store and load documents."""
        vector_store.initialize()

        # Auto-load documents if index is empty
        if vector_store.count == 0:
            await self.ingest_documents_directory(settings.DOCUMENTS_PATH)

    async def ingest_documents_directory(self, directory: str) -> int:
        """Ingest all documents from a directory. Returns count of chunks added."""
        path = Path(directory)
        if not path.exists():
            logger.warning(f"Documents directory does not exist: {directory}")
            return 0

        documents = list(document_loader.load_directory(directory))
        if not documents:
            logger.info("No documents found to ingest")
            return 0

        return await self.ingest_documents(documents)

    async def ingest_documents(self, documents: list[dict]) -> int:
        """Ingest a list of documents. Returns count of chunks added."""
        logger.info(f"Ingesting {len(documents)} documents...")

        chunks = await embedding_pipeline.process_documents(documents)

        if not chunks:
            return 0

        embeddings = [c["embedding"] for c in chunks]
        docs = [{"content": c["content"], "metadata": c["metadata"]} for c in chunks]

        vector_store.add(embeddings, docs)
        logger.info(f"Ingested {len(chunks)} chunks into vector store")
        return len(chunks)

    async def ingest_text(self, text: str, source: str = "inline") -> int:
        """Ingest raw text. Returns count of chunks added."""
        doc = document_loader.load_text(text, source)
        return await self.ingest_documents([doc])

    async def query(self, question: str, top_k: int = None) -> str:
        """Retrieve context for a question."""
        return await retriever.retrieve_formatted(question, top_k)

    @property
    def document_count(self) -> int:
        return vector_store.count


rag_agent = RAGAgent()
