import json
import logging
import uuid
from fastapi import WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)

# Map session_id → WebSocket
sessions: dict[str, WebSocket] = {}


async def webrtc_handler(websocket: WebSocket, session_id: str):
    """
    WebRTC signaling server.
    Handles offer/answer SDP exchange and ICE candidates.
    """
    await websocket.accept()
    sessions[session_id] = websocket
    logger.info(f"WebRTC signaling connected: {session_id[:8]}")

    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            msg_type = message.get("type")

            if msg_type == "offer":
                # Forward offer to server-side WebRTC peer
                # In a real deployment, you'd use aiortc here to handle
                # the actual WebRTC peer connection on the server side.
                # For now we echo back an answer placeholder.
                logger.info(f"Received WebRTC offer from {session_id[:8]}")
                await websocket.send_text(json.dumps({
                    "type": "answer",
                    "sdp": {
                        "type": "answer",
                        "sdp": _generate_placeholder_answer(message.get("sdp", {})),
                    }
                }))

            elif msg_type == "ice_candidate":
                logger.debug(f"ICE candidate from {session_id[:8]}")
                # In production: forward to aiortc peer

    except WebSocketDisconnect:
        logger.info(f"WebRTC signaling disconnected: {session_id[:8]}")
    finally:
        sessions.pop(session_id, None)


def _generate_placeholder_answer(offer_sdp: dict) -> str:
    """
    Placeholder SDP answer.
    Replace with aiortc-generated answer in production.
    """
    return ""
