import logging
import httpx
import json
from typing import AsyncGenerator, Optional

from server.config.settings import settings

logger = logging.getLogger(__name__)


class OllamaClient:
    def __init__(self):
        self.base_url = settings.OLLAMA_BASE_URL
        self.model = settings.OLLAMA_MODEL
        self.timeout = settings.OLLAMA_TIMEOUT

    async def chat(
        self,
        messages: list[dict],
        temperature: float = None,
        max_tokens: int = None,
        stream: bool = False,
    ) -> str | AsyncGenerator[str, None]:
        """
        Send a chat request to Ollama.
        messages: [{"role": "system"|"user"|"assistant", "content": "..."}]
        """
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": stream,
            "options": {
                "temperature": temperature or settings.OLLAMA_TEMPERATURE,
                "num_predict": max_tokens or settings.OLLAMA_MAX_TOKENS,
            },
        }

        if stream:
            return self._stream_chat(payload)
        else:
            return await self._complete_chat(payload)

    async def _complete_chat(self, payload: dict) -> str:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.base_url}/api/chat",
                json=payload,
            )
            response.raise_for_status()
            data = response.json()
            return data["message"]["content"]

    async def _stream_chat(self, payload: dict) -> AsyncGenerator[str, None]:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            async with client.stream("POST", f"{self.base_url}/api/chat", json=payload) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if line:
                        try:
                            data = json.loads(line)
                            if not data.get("done", False):
                                content = data.get("message", {}).get("content", "")
                                if content:
                                    yield content
                        except json.JSONDecodeError:
                            pass

    async def embed(self, text: str) -> list[float]:
        """Get embeddings from Ollama."""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.base_url}/api/embed",
                json={
                    "model": settings.OLLAMA_EMBEDDING_MODEL,
                    "input": text,
                },
            )
            response.raise_for_status()
            data = response.json()
            return data["embeddings"][0]

    async def health_check(self) -> bool:
        """Check if Ollama is running."""
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                response = await client.get(f"{self.base_url}/api/tags")
                return response.status_code == 200
        except Exception:
            return False

    async def list_models(self) -> list[str]:
        """List available models."""
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(f"{self.base_url}/api/tags")
                data = response.json()
                return [m["name"] for m in data.get("models", [])]
        except Exception as e:
            logger.error(f"Could not list models: {e}")
            return []


# Singleton
ollama_client = OllamaClient()
