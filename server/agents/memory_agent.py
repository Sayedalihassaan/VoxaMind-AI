import logging
from server.memory.conversation_store import conversation_store
from server.memory.memory_retriever import memory_retriever

logger = logging.getLogger(__name__)


class MemoryAgent:
    """Manages per-session conversational memory."""

    async def get_context(self, session_id: str) -> str:
        """Get memory context for a session."""
        return await memory_retriever.get_context(session_id)

    async def record_exchange(
        self, session_id: str, user_message: str, assistant_response: str
    ) -> None:
        """Record a user/assistant exchange to memory."""
        await conversation_store.add_turn(session_id, "user", user_message)
        await conversation_store.add_turn(session_id, "assistant", assistant_response)

        # Check if we need to summarize
        await memory_retriever.maybe_summarize(session_id)

    async def get_history(self, session_id: str) -> list[dict]:
        """Get conversation history for a session."""
        return await conversation_store.get_history(session_id)

    async def clear(self, session_id: str) -> None:
        """Clear session memory."""
        await conversation_store.clear_session(session_id)


memory_agent = MemoryAgent()
