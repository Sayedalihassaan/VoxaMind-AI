import time
from fastapi import APIRouter
from fastapi.responses import JSONResponse

from server.llm.ollama_client import ollama_client
from server.cache.redis_cache import cache
from server.rag.vector_store import vector_store
from server.config.settings import settings

router = APIRouter()
START_TIME = time.time()


@router.get("/health")
async def health_check():
    ollama_ok = await ollama_client.health_check()
    models = await ollama_client.list_models() if ollama_ok else []

    status = {
        "status": "ok" if ollama_ok else "degraded",
        "uptime_seconds": round(time.time() - START_TIME),
        "version": settings.APP_VERSION,
        "services": {
            "ollama": {
                "ok": ollama_ok,
                "url": settings.OLLAMA_BASE_URL,
                "model": settings.OLLAMA_MODEL,
                "available_models": models,
            },
            "redis": {
                "ok": cache.available,
                "url": settings.REDIS_URL,
            },
            "vector_store": {
                "ok": vector_store.initialized,
                "document_count": vector_store.count,
            },
        },
    }

    code = 200 if ollama_ok else 503
    return JSONResponse(content=status, status_code=code)


@router.get("/health/ready")
async def readiness():
    """Kubernetes/Docker readiness probe."""
    ok = await ollama_client.health_check()
    return JSONResponse(
        content={"ready": ok},
        status_code=200 if ok else 503
    )
