import json
import hashlib
import logging
from typing import Optional, Any
import redis.asyncio as aioredis

from server.config.settings import settings

logger = logging.getLogger(__name__)


class RedisCache:
    def __init__(self):
        self._client: Optional[aioredis.Redis] = None

    async def connect(self) -> None:
        try:
            self._client = aioredis.from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=False,
            )
            await self._client.ping()
            logger.info("Redis connected successfully")
        except Exception as e:
            logger.warning(f"Redis unavailable: {e}. Running without cache.")
            self._client = None

    async def disconnect(self) -> None:
        if self._client:
            await self._client.aclose()

    def _key(self, namespace: str, key: str) -> str:
        return f"voice-agent:{namespace}:{key}"

    async def get(self, namespace: str, key: str) -> Optional[Any]:
        if not self._client:
            return None
        try:
            data = await self._client.get(self._key(namespace, key))
            if data:
                return json.loads(data)
        except Exception as e:
            logger.error(f"Cache get error: {e}")
        return None

    async def set(self, namespace: str, key: str, value: Any, ttl: int = None) -> bool:
        if not self._client:
            return False
        try:
            ttl = ttl or settings.REDIS_TTL
            serialized = json.dumps(value)
            await self._client.setex(self._key(namespace, key), ttl, serialized)
            return True
        except Exception as e:
            logger.error(f"Cache set error: {e}")
            return False

    async def delete(self, namespace: str, key: str) -> bool:
        if not self._client:
            return False
        try:
            await self._client.delete(self._key(namespace, key))
            return True
        except Exception as e:
            logger.error(f"Cache delete error: {e}")
            return False

    async def get_bytes(self, namespace: str, key: str) -> Optional[bytes]:
        if not self._client:
            return None
        try:
            return await self._client.get(self._key(namespace, key))
        except Exception as e:
            logger.error(f"Cache get_bytes error: {e}")
        return None

    async def set_bytes(self, namespace: str, key: str, value: bytes, ttl: int = None) -> bool:
        if not self._client:
            return False
        try:
            ttl = ttl or settings.REDIS_TTL
            await self._client.setex(self._key(namespace, key), ttl, value)
            return True
        except Exception as e:
            logger.error(f"Cache set_bytes error: {e}")
            return False

    @staticmethod
    def hash_key(text: str) -> str:
        return hashlib.sha256(text.encode()).hexdigest()[:16]

    @property
    def available(self) -> bool:
        return self._client is not None


# Singleton
cache = RedisCache()
