import os
import logging
from pathlib import Path
from typing import Iterator

logger = logging.getLogger(__name__)


class DocumentLoader:
    """Loads documents from disk for RAG ingestion."""

    SUPPORTED_EXTENSIONS = {".txt", ".md", ".pdf", ".json"}

    def load_directory(self, directory: str) -> Iterator[dict]:
        """Yield documents from a directory."""
        path = Path(directory)
        if not path.exists():
            logger.warning(f"Documents directory not found: {directory}")
            return

        for file_path in path.rglob("*"):
            if file_path.suffix.lower() in self.SUPPORTED_EXTENSIONS:
                doc = self.load_file(str(file_path))
                if doc:
                    yield doc

    def load_file(self, file_path: str) -> dict | None:
        """Load a single file."""
        path = Path(file_path)
        ext = path.suffix.lower()

        try:
            if ext in (".txt", ".md"):
                return self._load_text(path)
            elif ext == ".pdf":
                return self._load_pdf(path)
            elif ext == ".json":
                return self._load_json(path)
        except Exception as e:
            logger.error(f"Failed to load {file_path}: {e}")
        return None

    def load_text(self, text: str, source: str = "inline") -> dict:
        """Load from raw text string."""
        return {
            "content": text.strip(),
            "metadata": {"source": source, "type": "text"},
        }

    def _load_text(self, path: Path) -> dict:
        content = path.read_text(encoding="utf-8", errors="ignore")
        return {
            "content": content.strip(),
            "metadata": {
                "source": path.name,
                "path": str(path),
                "type": path.suffix[1:],
            },
        }

    def _load_pdf(self, path: Path) -> dict:
        try:
            import pypdf
            reader = pypdf.PdfReader(str(path))
            pages = []
            for page in reader.pages:
                text = page.extract_text()
                if text:
                    pages.append(text)
            content = "\n\n".join(pages)
            return {
                "content": content.strip(),
                "metadata": {
                    "source": path.name,
                    "path": str(path),
                    "type": "pdf",
                    "pages": len(reader.pages),
                },
            }
        except ImportError:
            logger.warning("pypdf not installed. Install with: pip install pypdf")
            return None

    def _load_json(self, path: Path) -> dict:
        import json
        data = json.loads(path.read_text())
        # Try to extract text field
        if isinstance(data, dict):
            content = data.get("content") or data.get("text") or json.dumps(data)
        elif isinstance(data, list):
            content = "\n".join(
                item.get("content", str(item)) if isinstance(item, dict) else str(item)
                for item in data
            )
        else:
            content = str(data)
        return {
            "content": content,
            "metadata": {"source": path.name, "type": "json"},
        }


document_loader = DocumentLoader()
