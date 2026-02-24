import logging
import asyncio
from typing import AsyncGenerator, Callable, Optional

from server.speech.stt import stt
from server.speech.tts import tts
from server.speech.audio_processor import AudioProcessor
from server.llm.ollama_client import ollama_client
from server.llm.prompt_builder import PromptBuilder
from server.agents.rag_agent import rag_agent
from server.agents.memory_agent import memory_agent
from server.config.constants import AgentState

logger = logging.getLogger(__name__)


class VoiceAgent:
    """
    Core orchestrator: audio in → STT → RAG + Memory → LLM → TTS → audio out.
    """

    def __init__(self, session_id: str):
        self.session_id = session_id
        self.state = AgentState.IDLE
        self._audio_buffer = bytearray()

    def append_audio(self, chunk: bytes) -> None:
        """Accumulate incoming audio bytes."""
        self._audio_buffer.extend(chunk)

    def clear_audio_buffer(self) -> None:
        self._audio_buffer = bytearray()

    async def process(
        self,
        on_transcript: Optional[Callable[[str], None]] = None,
        on_text_chunk: Optional[Callable[[str], None]] = None,
        on_audio_chunk: Optional[Callable[[bytes], None]] = None,
    ) -> dict:
        """
        Process buffered audio end-to-end.
        Calls callbacks as results are ready for streaming to client.
        Returns final result dict.
        """
        if not self._audio_buffer:
            return {"error": "No audio data"}

        audio_bytes = bytes(self._audio_buffer)
        self.clear_audio_buffer()

        # ── 1. Speech to Text ──────────────────────────────────────────────
        self.state = AgentState.TRANSCRIBING
        logger.info(f"[{self.session_id[:8]}] Transcribing {len(audio_bytes)} bytes...")

        stt_result = await stt.transcribe(audio_bytes)
        transcript = stt_result.get("text", "").strip()

        if not transcript:
            self.state = AgentState.IDLE
            return {"error": "Could not transcribe audio"}

        logger.info(f"[{self.session_id[:8]}] Transcript: {transcript}")
        if on_transcript:
            on_transcript(transcript)

        # ── 2. Retrieve Context (RAG + Memory) ────────────────────────────
        self.state = AgentState.THINKING

        rag_context, memory_context = await asyncio.gather(
            rag_agent.query(transcript),
            memory_agent.get_context(self.session_id),
        )

        # ── 3. Build Prompt ───────────────────────────────────────────────
        system_prompt = PromptBuilder.build_system_prompt(
            memory_context=memory_context,
            rag_context=rag_context,
        )
        history = await memory_agent.get_history(self.session_id)
        messages = PromptBuilder.build_messages(history, transcript, system_prompt)

        # ── 4. LLM Response (streaming) ───────────────────────────────────
        logger.info(f"[{self.session_id[:8]}] Generating response...")
        response_text = ""
        sentence_buffer = ""

        async for token in await ollama_client.chat(messages, stream=True):
            response_text += token
            sentence_buffer += token

            if on_text_chunk:
                on_text_chunk(token)

            # Stream TTS sentence-by-sentence for low latency
            if on_audio_chunk and self._is_sentence_boundary(sentence_buffer):
                sentence = sentence_buffer.strip()
                sentence_buffer = ""
                if sentence:
                    asyncio.create_task(
                        self._stream_tts(sentence, on_audio_chunk)
                    )

        # Flush remaining sentence buffer
        if sentence_buffer.strip() and on_audio_chunk:
            await self._stream_tts(sentence_buffer.strip(), on_audio_chunk)

        # ── 5. Store to Memory ────────────────────────────────────────────
        await memory_agent.record_exchange(self.session_id, transcript, response_text)

        self.state = AgentState.IDLE
        return {
            "transcript": transcript,
            "response": response_text,
            "rag_context_used": bool(rag_context),
        }

    async def _stream_tts(self, text: str, callback: Callable[[bytes], None]) -> None:
        """Synthesize and stream TTS audio."""
        self.state = AgentState.SPEAKING
        try:
            async for chunk in tts.synthesize_streaming(text):
                if chunk:
                    callback(chunk)
        except Exception as e:
            logger.error(f"TTS error: {e}")

    @staticmethod
    def _is_sentence_boundary(text: str) -> bool:
        """Detect if text ends with a sentence boundary."""
        stripped = text.strip()
        if not stripped:
            return False
        return stripped[-1] in ".!?:;" and len(stripped) > 10
