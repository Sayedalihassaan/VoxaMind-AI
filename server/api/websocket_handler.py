import json
import base64
import asyncio
import logging
import uuid
from fastapi import WebSocket, WebSocketDisconnect

from server.agents.voice_agent import VoiceAgent
from server.config.constants import MessageType

logger = logging.getLogger(__name__)


class ConnectionManager:
    def __init__(self):
        self._active: dict[str, WebSocket] = {}

    def add(self, session_id: str, ws: WebSocket):
        self._active[session_id] = ws

    def remove(self, session_id: str):
        self._active.pop(session_id, None)

    @property
    def count(self):
        return len(self._active)


manager = ConnectionManager()


async def websocket_handler(websocket: WebSocket):
    session_id = str(uuid.uuid4())
    await websocket.accept()
    manager.add(session_id, websocket)

    agent = VoiceAgent(session_id)

    # Send session info
    await send_json(websocket, {
        "type": MessageType.SESSION_START,
        "data": {"session_id": session_id},
    })

    logger.info(f"WebSocket connected: {session_id[:8]} (total: {manager.count})")

    try:
        while True:
            message = await websocket.receive()

            # Binary audio data
            if "bytes" in message and message["bytes"]:
                agent.append_audio(message["bytes"])

            # JSON control messages
            elif "text" in message and message["text"]:
                await handle_text_message(websocket, agent, message["text"])

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected: {session_id[:8]}")
    except Exception as e:
        logger.error(f"WebSocket error [{session_id[:8]}]: {e}")
        try:
            await send_json(websocket, {
                "type": MessageType.ERROR,
                "data": {"message": str(e)},
            })
        except Exception:
            pass
    finally:
        manager.remove(session_id)


async def handle_text_message(websocket: WebSocket, agent: VoiceAgent, raw: str):
    try:
        message = json.loads(raw)
    except json.JSONDecodeError:
        return

    msg_type = message.get("type")

    if msg_type == MessageType.PING:
        await send_json(websocket, {"type": MessageType.PONG, "timestamp": message.get("timestamp")})

    elif msg_type == MessageType.AUDIO_END:
        # Process accumulated audio
        await process_audio(websocket, agent)

    elif msg_type == MessageType.SESSION_END:
        await websocket.close()


async def process_audio(websocket: WebSocket, agent: VoiceAgent):
    """Process audio buffer and stream response back."""

    async def on_transcript(text: str):
        await send_json(websocket, {
            "type": MessageType.TRANSCRIPT,
            "data": {"text": text, "is_final": True},
        })

    text_buffer = []

    async def on_text_chunk(token: str):
        text_buffer.append(token)
        await send_json(websocket, {
            "type": MessageType.RESPONSE_TEXT,
            "data": {"text": token, "is_final": False},
        })

    audio_queue: asyncio.Queue[bytes | None] = asyncio.Queue()

    async def on_audio_chunk(chunk: bytes):
        await audio_queue.put(chunk)

    # Run agent processing in background
    process_task = asyncio.create_task(
        agent.process(
            on_transcript=lambda t: asyncio.create_task(_safe_send_transcript(websocket, t)),
            on_text_chunk=lambda t: asyncio.create_task(_safe_send_text(websocket, t)),
            on_audio_chunk=lambda c: asyncio.create_task(audio_queue.put(c)),
        )
    )

    # Stream audio chunks to client as they arrive
    while True:
        try:
            chunk = await asyncio.wait_for(audio_queue.get(), timeout=0.1)
            if chunk is None:
                break
            # Send as base64 JSON (could also send binary with websocket.send_bytes)
            encoded = base64.b64encode(chunk).decode("utf-8")
            await send_json(websocket, {
                "type": MessageType.RESPONSE_AUDIO,
                "data": {"audio": encoded, "sample_rate": 24000},
            })
        except asyncio.TimeoutError:
            if process_task.done():
                break

    await process_task

    # Signal audio stream end
    await send_json(websocket, {"type": MessageType.RESPONSE_AUDIO_END})

    # Final text
    if text_buffer:
        await send_json(websocket, {
            "type": MessageType.RESPONSE_TEXT,
            "data": {"text": "", "is_final": True},
        })


async def _safe_send_transcript(websocket: WebSocket, text: str):
    try:
        await send_json(websocket, {
            "type": MessageType.TRANSCRIPT,
            "data": {"text": text, "is_final": True},
        })
    except Exception:
        pass


async def _safe_send_text(websocket: WebSocket, token: str):
    try:
        await send_json(websocket, {
            "type": MessageType.RESPONSE_TEXT,
            "data": {"text": token, "is_final": False},
        })
    except Exception:
        pass


async def send_json(websocket: WebSocket, data: dict):
    await websocket.send_text(json.dumps(data))
