from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # App
    APP_NAME: str = "Voice Agent"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # Ollama
    OLLAMA_BASE_URL: str = "http://ollama:11434"
    OLLAMA_MODEL: str = "llama3.2"
    OLLAMA_EMBEDDING_MODEL: str = "nomic-embed-text"
    OLLAMA_TEMPERATURE: float = 0.7
    OLLAMA_MAX_TOKENS: int = 1024
    OLLAMA_TIMEOUT: int = 120

    # STT (Whisper)
    WHISPER_MODEL: str = "base.en"
    WHISPER_DEVICE: str = "cpu"  # "cpu" or "cuda"
    WHISPER_COMPUTE_TYPE: str = "int8"  # "int8", "float16", "float32"
    WHISPER_LANGUAGE: str = "en"

    # TTS (edge-tts)
    TTS_VOICE: str = "en-US-AriaNeural"
    TTS_RATE: str = "+0%"
    TTS_VOLUME: str = "+0%"
    TTS_PITCH: str = "+0Hz"

    # Audio
    AUDIO_SAMPLE_RATE: int = 16000
    AUDIO_CHANNELS: int = 1

    # Redis
    REDIS_URL: str = "redis://redis:6379"
    REDIS_TTL: int = 3600  # 1 hour cache TTL

    # RAG / FAISS
    FAISS_INDEX_PATH: str = "/app/data/faiss_index"
    DOCUMENTS_PATH: str = "/app/data/documents"
    EMBEDDING_DIM: int = 768
    RETRIEVAL_TOP_K: int = 4
    CHUNK_SIZE: int = 512
    CHUNK_OVERLAP: int = 64

    # Memory
    MAX_CONVERSATION_TURNS: int = 20
    MEMORY_SUMMARY_THRESHOLD: int = 15  # summarize after N turns

    # CORS
    CORS_ORIGINS: list[str] = ["*"]

    class Config:
        env_file = ".env"


settings = Settings()
