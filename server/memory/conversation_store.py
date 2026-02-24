import logging
from dataclasses import dataclass, field, asdict
from typing import Optional
import time

from server.cache.redis_cache import cache
from server.config.settings import settings

logger = logging.getLogger(__name__)


@dataclass
class ConversationTurn:
    role: str  # "user" or "assistant"
    content: str
    timestamp: float = field(default_factory=time.time)


@dataclass
class ConversationSession:
    session_id: str
    turns: list[ConversationTurn] = field(default_factory=list)
    summary: str = ""
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)


class ConversationStore:
    """Stores conversation history per session with Redis persistence."""

    def __init__(self):
        # In-memory fallback
        self._sessions: dict[str, ConversationSession] = {}

    async def get_session(self, session_id: str) -> ConversationSession:
        """Get or create a session."""
        # Try Redis first
        data = await cache.get("sessions", session_id)
        if data:
            session = ConversationSession(
                session_id=data["session_id"],
                turns=[ConversationTurn(**t) for t in data["turns"]],
                summary=data.get("summary", ""),
                created_at=data.get("created_at", time.time()),
                updated_at=data.get("updated_at", time.time()),
            )
            self._sessions[session_id] = session
            return session

        # Check in-memory
        if session_id in self._sessions:
            return self._sessions[session_id]

        # Create new session
        session = ConversationSession(session_id=session_id)
        self._sessions[session_id] = session
        return session

    async def add_turn(self, session_id: str, role: str, content: str) -> None:
        """Add a conversation turn."""
        session = await self.get_session(session_id)
        session.turns.append(ConversationTurn(role=role, content=content))
        session.updated_at = time.time()

        # Trim old turns beyond max
        if len(session.turns) > settings.MAX_CONVERSATION_TURNS * 2:
            # Keep summary of old turns, drop them
            session.turns = session.turns[-settings.MAX_CONVERSATION_TURNS * 2:]

        await self._persist(session)

    async def get_history(self, session_id: str) -> list[dict]:
        """Get conversation history as list of {role, content} dicts."""
        session = await self.get_session(session_id)
        return [{"role": t.role, "content": t.content} for t in session.turns]

    async def get_summary(self, session_id: str) -> str:
        """Get conversation summary."""
        session = await self.get_session(session_id)
        return session.summary

    async def set_summary(self, session_id: str, summary: str) -> None:
        """Set conversation summary and optionally trim history."""
        session = await self.get_session(session_id)
        session.summary = summary
        # Keep only the most recent turns after summarizing
        if len(session.turns) > settings.MAX_CONVERSATION_TURNS:
            session.turns = session.turns[-10:]
        await self._persist(session)

    async def clear_session(self, session_id: str) -> None:
        """Clear a session."""
        self._sessions.pop(session_id, None)
        await cache.delete("sessions", session_id)

    async def _persist(self, session: ConversationSession) -> None:
        """Persist session to Redis."""
        data = {
            "session_id": session.session_id,
            "turns": [asdict(t) for t in session.turns],
            "summary": session.summary,
            "created_at": session.created_at,
            "updated_at": session.updated_at,
        }
        await cache.set("sessions", session.session_id, data, ttl=86400)  # 24h TTL


conversation_store = ConversationStore()
