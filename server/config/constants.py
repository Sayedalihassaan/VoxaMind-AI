from enum import Enum


class MessageType(str, Enum):
    AUDIO_CHUNK = "audio_chunk"
    AUDIO_END = "audio_end"
    TRANSCRIPT = "transcript"
    RESPONSE_TEXT = "response_text"
    RESPONSE_AUDIO = "response_audio"
    RESPONSE_AUDIO_END = "response_audio_end"
    ERROR = "error"
    PING = "ping"
    PONG = "pong"
    SESSION_START = "session_start"
    SESSION_END = "session_end"


class AgentState(str, Enum):
    IDLE = "idle"
    LISTENING = "listening"
    TRANSCRIBING = "transcribing"
    THINKING = "thinking"
    SPEAKING = "speaking"
    ERROR = "error"


SYSTEM_PROMPT = """You are a helpful, conversational AI voice assistant. You are friendly, concise, and clear.

Key guidelines:
- Keep responses conversational and relatively brief (2-4 sentences when possible)
- Avoid markdown formatting, bullet points, or special characters that don't translate well to speech
- Speak naturally as if in conversation
- When referencing context from memory or documents, integrate it naturally
- If you don't know something, say so clearly
- Always be helpful and friendly

{memory_context}
{rag_context}
"""

MEMORY_SUMMARY_PROMPT = """Summarize the following conversation history concisely, preserving key facts, preferences, and context that would be useful for future interactions:

{conversation}

Summary:"""

SUPPORTED_AUDIO_FORMATS = {"pcm16", "wav", "webm", "ogg"}
MAX_AUDIO_DURATION_SECONDS = 60
AUDIO_BUFFER_SIZE = 4096
