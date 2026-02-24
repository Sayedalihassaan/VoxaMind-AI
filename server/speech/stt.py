import io
import logging
import numpy as np
from typing import Optional
import soundfile as sf

from server.config.settings import settings

logger = logging.getLogger(__name__)


class SpeechToText:
    def __init__(self):
        self._model = None

    def load(self) -> None:
        """Lazy-load Whisper model."""
        try:
            from faster_whisper import WhisperModel
            logger.info(f"Loading Whisper model: {settings.WHISPER_MODEL}")
            self._model = WhisperModel(
                settings.WHISPER_MODEL,
                device=settings.WHISPER_DEVICE,
                compute_type=settings.WHISPER_COMPUTE_TYPE,
            )
            logger.info("Whisper model loaded")
        except ImportError:
            logger.error("faster-whisper not installed. Run: pip install faster-whisper")
            raise

    def _ensure_loaded(self) -> None:
        if self._model is None:
            self.load()

    async def transcribe(
        self,
        audio_bytes: bytes,
        sample_rate: int = 16000,
        language: Optional[str] = None,
    ) -> dict:
        """
        Transcribe audio bytes (PCM int16 mono) to text.
        Returns dict with 'text', 'language', 'segments'.
        """
        self._ensure_loaded()

        try:
            # Convert PCM int16 bytes → float32 numpy array
            audio_array = np.frombuffer(audio_bytes, dtype=np.int16).astype(np.float32)
            audio_array /= 32768.0  # normalize to [-1, 1]

            # Resample to 16kHz if needed (Whisper requires 16kHz)
            if sample_rate != 16000:
                audio_array = self._resample(audio_array, sample_rate, 16000)

            # Transcribe
            segments, info = self._model.transcribe(
                audio_array,
                language=language or settings.WHISPER_LANGUAGE,
                vad_filter=True,
                vad_parameters=dict(min_silence_duration_ms=500),
            )

            text_parts = []
            segment_list = []
            for seg in segments:
                text_parts.append(seg.text.strip())
                segment_list.append({
                    "start": seg.start,
                    "end": seg.end,
                    "text": seg.text.strip(),
                })

            return {
                "text": " ".join(text_parts).strip(),
                "language": info.language,
                "probability": info.language_probability,
                "segments": segment_list,
            }

        except Exception as e:
            logger.error(f"Transcription error: {e}")
            return {"text": "", "language": "en", "probability": 0.0, "segments": []}

    def _resample(self, audio: np.ndarray, orig_sr: int, target_sr: int) -> np.ndarray:
        """Simple linear resampling."""
        if orig_sr == target_sr:
            return audio
        ratio = target_sr / orig_sr
        target_length = int(len(audio) * ratio)
        indices = np.linspace(0, len(audio) - 1, target_length)
        return np.interp(indices, np.arange(len(audio)), audio).astype(np.float32)


# Singleton
stt = SpeechToText()
