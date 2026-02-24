import io
import logging
import asyncio
import struct
from typing import AsyncGenerator, Optional

from server.config.settings import settings
from server.cache.redis_cache import cache

logger = logging.getLogger(__name__)


class TextToSpeech:
    """Text-to-Speech using edge-tts (free, no API key needed)."""

    def __init__(self):
        self._voice = settings.TTS_VOICE

    async def synthesize(self, text: str) -> bytes:
        """
        Synthesize text to PCM audio bytes.
        Returns raw MP3 bytes (24kHz).
        Uses Redis cache to avoid re-synthesizing identical phrases.
        """
        if not text.strip():
            return b""

        # Check cache
        cache_key = cache.hash_key(f"{self._voice}:{text}")
        cached = await cache.get_bytes("tts", cache_key)
        if cached:
            logger.debug("TTS cache hit")
            return cached

        try:
            import edge_tts

            communicate = edge_tts.Communicate(
                text=text,
                voice=self._voice,
                rate=settings.TTS_RATE,
                volume=settings.TTS_VOLUME,
                pitch=settings.TTS_PITCH,
            )

            audio_buffer = io.BytesIO()
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    audio_buffer.write(chunk["data"])

            audio_bytes = audio_buffer.getvalue()

            # Cache for 24 hours (TTS is expensive)
            await cache.set_bytes("tts", cache_key, audio_bytes, ttl=86400)

            return audio_bytes

        except ImportError:
            logger.error("edge-tts not installed. Run: pip install edge-tts")
            raise
        except Exception as e:
            logger.error(f"TTS error: {e}")
            return b""

    async def synthesize_streaming(self, text: str) -> AsyncGenerator[bytes, None]:
        """Stream audio chunks as they are generated."""
        try:
            import edge_tts

            communicate = edge_tts.Communicate(
                text=text,
                voice=self._voice,
                rate=settings.TTS_RATE,
                volume=settings.TTS_VOLUME,
                pitch=settings.TTS_PITCH,
            )

            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    yield chunk["data"]

        except Exception as e:
            logger.error(f"TTS streaming error: {e}")
            return

    def set_voice(self, voice: str) -> None:
        self._voice = voice

    @staticmethod
    async def list_voices() -> list[dict]:
        try:
            import edge_tts
            voices = await edge_tts.list_voices()
            return [
                {
                    "name": v["ShortName"],
                    "locale": v["Locale"],
                    "gender": v["Gender"],
                }
                for v in voices
                if v["Locale"].startswith("en-")
            ]
        except Exception as e:
            logger.error(f"Could not list voices: {e}")
            return []


# Singleton
tts = TextToSpeech()
