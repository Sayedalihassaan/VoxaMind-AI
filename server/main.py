import logging
import uvicorn
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os

from server.config.settings import settings
from server.api.health_check import router as health_router
from server.api.websocket_handler import websocket_handler
from server.api.webrtc_handler import webrtc_handler
from server.cache.redis_cache import cache
from server.speech.stt import stt
from server.agents.rag_agent import rag_agent

logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown lifecycle."""
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")

    # Connect to Redis (non-fatal)
    await cache.connect()

    # Load Whisper model
    try:
        stt.load()
    except Exception as e:
        logger.warning(f"STT model could not be loaded: {e}")

    # Initialize RAG
    try:
        await rag_agent.initialize()
        logger.info(f"RAG initialized with {rag_agent.document_count} chunks")
    except Exception as e:
        logger.warning(f"RAG initialization failed: {e}")

    logger.info("Server ready ✓")
    yield

    # Shutdown
    await cache.disconnect()
    logger.info("Server shutdown complete")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# REST routes
app.include_router(health_router, prefix="/api")


# WebSocket routes
@app.websocket("/ws/audio")
async def ws_audio(websocket: WebSocket):
    await websocket_handler(websocket)


@app.websocket("/ws/webrtc/{session_id}")
async def ws_webrtc(websocket: WebSocket, session_id: str):
    await webrtc_handler(websocket, session_id)


# Ingest API
from fastapi import HTTPException
from pydantic import BaseModel


class IngestRequest(BaseModel):
    text: str
    source: str = "api"


@app.post("/api/ingest")
async def ingest_text(req: IngestRequest):
    """Ingest text into the RAG vector store."""
    count = await rag_agent.ingest_text(req.text, req.source)
    return {"status": "ok", "chunks_added": count}


@app.get("/api/voices")
async def list_voices():
    """List available TTS voices."""
    from server.speech.tts import tts
    voices = await tts.list_voices()
    return {"voices": voices}


# Serve static frontend
static_path = os.path.join(os.path.dirname(__file__), "..", "static")
if os.path.exists(static_path):
    app.mount("/", StaticFiles(directory=static_path, html=True), name="static")


if __name__ == "__main__":
    uvicorn.run(
        "server.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level="debug" if settings.DEBUG else "info",
    )
