import logging
from server.memory.conversation_store import conversation_store
from server.llm.ollama_client import ollama_client
from server.llm.prompt_builder import PromptBuilder
from server.config.settings import settings

logger = logging.getLogger(__name__)


class MemoryRetriever:
    """Manages conversation memory and generates summaries when needed."""

    async def get_context(self, session_id: str) -> str:
        """
        Get memory context for the current session.
        Returns summary of past conversation if available.
        """
        summary = await conversation_store.get_summary(session_id)
        history = await conversation_store.get_history(session_id)

        context_parts = []

        if summary:
            context_parts.append(f"Previous conversation summary:\n{summary}")

        if history:
            # Format recent turns for context
            recent_turns = history[-6:]  # last 3 exchanges
            formatted = []
            for turn in recent_turns:
                role_label = "User" if turn["role"] == "user" else "Assistant"
                formatted.append(f"{role_label}: {turn['content']}")
            if formatted:
                context_parts.append("Recent exchanges:\n" + "\n".join(formatted))

        return "\n\n".join(context_parts)

    async def maybe_summarize(self, session_id: str) -> None:
        """Summarize conversation history if it's getting long."""
        history = await conversation_store.get_history(session_id)

        if len(history) < settings.MEMORY_SUMMARY_THRESHOLD:
            return

        logger.info(f"Summarizing conversation for session {session_id[:8]}...")

        conversation_text = "\n".join(
            f"{t['role'].capitalize()}: {t['content']}"
            for t in history
        )

        messages = PromptBuilder.build_memory_summary_prompt(conversation_text)

        try:
            summary = await ollama_client.chat(messages, temperature=0.3)
            await conversation_store.set_summary(session_id, summary)
            logger.info("Conversation summarized and history trimmed")
        except Exception as e:
            logger.error(f"Failed to summarize conversation: {e}")


memory_retriever = MemoryRetriever()
