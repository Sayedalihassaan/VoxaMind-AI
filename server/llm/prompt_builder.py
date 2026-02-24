from server.config.constants import SYSTEM_PROMPT, MEMORY_SUMMARY_PROMPT


class PromptBuilder:
    """Builds structured prompt messages for the LLM."""

    @staticmethod
    def build_system_prompt(
        memory_context: str = "",
        rag_context: str = "",
    ) -> str:
        """Build the system prompt with optional memory and RAG context."""
        memory_section = ""
        if memory_context:
            memory_section = f"\n## Conversation Memory\n{memory_context}\n"

        rag_section = ""
        if rag_context:
            rag_section = f"\n## Relevant Knowledge\n{rag_context}\n"

        return SYSTEM_PROMPT.format(
            memory_context=memory_section,
            rag_context=rag_section,
        ).strip()

    @staticmethod
    def build_messages(
        conversation_history: list[dict],
        user_message: str,
        system_prompt: str,
    ) -> list[dict]:
        """Build the messages list for the LLM API."""
        messages = [{"role": "system", "content": system_prompt}]

        # Add conversation history (trim to last N turns)
        for turn in conversation_history[-20:]:
            messages.append(turn)

        # Add current user message
        messages.append({"role": "user", "content": user_message})

        return messages

    @staticmethod
    def build_memory_summary_prompt(conversation: str) -> list[dict]:
        """Build prompt for summarizing conversation history."""
        return [
            {
                "role": "user",
                "content": MEMORY_SUMMARY_PROMPT.format(conversation=conversation),
            }
        ]

    @staticmethod
    def format_rag_context(documents: list[dict]) -> str:
        """Format retrieved documents into context string."""
        if not documents:
            return ""

        parts = []
        for i, doc in enumerate(documents, 1):
            source = doc.get("source", f"Document {i}")
            content = doc.get("content", "")
            score = doc.get("score", 0)
            parts.append(f"[{source}] (relevance: {score:.2f})\n{content}")

        return "\n\n".join(parts)
