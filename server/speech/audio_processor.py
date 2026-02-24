import io
import struct
import numpy as np
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class AudioProcessor:
    """Utility class for audio format conversions and processing."""

    @staticmethod
    def pcm16_to_float32(data: bytes) -> np.ndarray:
        """Convert raw PCM int16 bytes to float32 numpy array."""
        arr = np.frombuffer(data, dtype=np.int16).astype(np.float32)
        arr /= 32768.0
        return arr

    @staticmethod
    def float32_to_pcm16(data: np.ndarray) -> bytes:
        """Convert float32 numpy array to PCM int16 bytes."""
        clipped = np.clip(data, -1.0, 1.0)
        int16 = (clipped * 32767).astype(np.int16)
        return int16.tobytes()

    @staticmethod
    def pcm16_to_wav(pcm_data: bytes, sample_rate: int = 16000, channels: int = 1) -> bytes:
        """Wrap raw PCM16 in a WAV container."""
        buf = io.BytesIO()
        bits_per_sample = 16
        byte_rate = sample_rate * channels * bits_per_sample // 8
        block_align = channels * bits_per_sample // 8
        data_size = len(pcm_data)

        buf.write(b"RIFF")
        buf.write(struct.pack("<I", 36 + data_size))
        buf.write(b"WAVE")
        buf.write(b"fmt ")
        buf.write(struct.pack("<I", 16))
        buf.write(struct.pack("<H", 1))  # PCM
        buf.write(struct.pack("<H", channels))
        buf.write(struct.pack("<I", sample_rate))
        buf.write(struct.pack("<I", byte_rate))
        buf.write(struct.pack("<H", block_align))
        buf.write(struct.pack("<H", bits_per_sample))
        buf.write(b"data")
        buf.write(struct.pack("<I", data_size))
        buf.write(pcm_data)

        return buf.getvalue()

    @staticmethod
    def resample(audio: np.ndarray, orig_sr: int, target_sr: int) -> np.ndarray:
        """Linear resampling."""
        if orig_sr == target_sr:
            return audio
        ratio = target_sr / orig_sr
        target_len = int(len(audio) * ratio)
        indices = np.linspace(0, len(audio) - 1, target_len)
        return np.interp(indices, np.arange(len(audio)), audio).astype(np.float32)

    @staticmethod
    def normalize(audio: np.ndarray, target_db: float = -20.0) -> np.ndarray:
        """Normalize audio to target dBFS."""
        rms = np.sqrt(np.mean(audio ** 2))
        if rms < 1e-10:
            return audio
        target_rms = 10 ** (target_db / 20.0)
        return audio * (target_rms / rms)

    @staticmethod
    def is_silent(audio: np.ndarray, threshold: float = 0.01) -> bool:
        """Check if audio chunk is silent."""
        rms = np.sqrt(np.mean(audio ** 2))
        return rms < threshold

    @staticmethod
    def split_chunks(data: bytes, chunk_size: int = 32000) -> list[bytes]:
        """Split audio bytes into chunks."""
        return [data[i:i + chunk_size] for i in range(0, len(data), chunk_size)]
