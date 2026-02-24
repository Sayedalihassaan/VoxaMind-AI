# 🎙 Voice Agent

A fully local, privacy-first voice AI assistant built with:

| Component | Technology |
|-----------|-----------|
| **LLM** | Ollama (llama3.2, mistral, etc.) |
| **STT** | Whisper (faster-whisper) |
| **TTS** | Edge-TTS (Microsoft Azure free tier) |
| **Embeddings** | Ollama nomic-embed-text |
| **Vector DB** | FAISS |
| **Memory** | Redis + in-memory conversation store |
| **Backend** | FastAPI + WebSockets |
| **Frontend** | Vanilla TypeScript |
| **Infra** | Docker Compose + Nginx |

---

## Architecture

```
Browser
  │  WebSocket (PCM audio stream)
  ▼
Nginx
  │  Reverse proxy
  ▼
FastAPI (voice-agent)
  │
  ├── STT  →  faster-whisper  →  transcript text
  │
  ├── RAG  →  FAISS + nomic-embed-text  →  relevant context
  │
  ├── Memory  →  Redis conversation store  →  history context
  │
  ├── LLM  →  Ollama (llama3.2)  →  response text (streaming)
  │
  └── TTS  →  edge-tts  →  audio stream back to browser
```

---

## Prerequisites

| Tool | Version | Install |
|------|---------|---------|
| Docker | 24+ | https://docs.docker.com/get-docker/ |
| Docker Compose | v2 | Included with Docker Desktop |
| Git | any | https://git-scm.com |

> **RAM**: 8GB minimum (16GB recommended for larger models)
> **Disk**: 10GB free (models are large)

---

## 🚀 Quick Start (Docker — Recommended)

### Step 1 — Clone the repository

```bash
git clone <your-repo-url>
cd voice-agent
```

### Step 2 — Create your environment file

```bash
cp .env.example .env
```

Edit `.env` if needed (defaults work out of the box).

### Step 3 — Start all services

```bash
cd infra/docker
docker compose up -d
```

This starts:
- **ollama** — LLM server (pulls `llama3.2` + `nomic-embed-text` automatically)
- **redis** — cache + session memory
- **voice-agent** — FastAPI backend
- **nginx** — reverse proxy on port 80

### Step 4 — Wait for models to download

The first run downloads AI models (~2-4GB). Monitor progress:

```bash
docker compose logs -f ollama-init
# Wait until you see: "=== All models ready ==="
```

Check that all services are healthy:

```bash
docker compose ps
# All should show "healthy" or "Up"
```

### Step 5 — Open the UI

Navigate to **http://localhost** in your browser.

> ⚠️ **HTTPS Required for Microphone**: Chrome/Firefox block microphone access on plain HTTP except for `localhost`. If deploying to a server, set up HTTPS (see [HTTPS section](#https-setup)).

### Step 6 — Talk to your voice agent!

1. Click the **microphone button** 🎤
2. Speak your question
3. Pause for ~1 second — the agent auto-detects silence
4. Listen to the response

---

## 🖥️ Local Development (No Docker)

### Step 1 — Install system dependencies

**macOS:**
```bash
brew install ffmpeg redis
```

**Ubuntu/Debian:**
```bash
sudo apt install ffmpeg redis-server libsndfile1
```

**Windows:**
```powershell
# Install via winget
winget install FFmpeg
# Or use WSL2 (recommended)
```

### Step 2 — Install Ollama

```bash
# macOS / Linux
curl -fsSL https://ollama.ai/install.sh | sh

# Windows
# Download from https://ollama.ai/download
```

### Step 3 — Pull required models

```bash
ollama pull llama3.2
ollama pull nomic-embed-text
```

Verify models are available:
```bash
ollama list
```

### Step 4 — Start Redis

```bash
# macOS
brew services start redis

# Linux
sudo systemctl start redis
# or
redis-server --daemonize yes

# Verify
redis-cli ping  # should return PONG
```

### Step 5 — Set up Python environment

```bash
# Python 3.11 recommended
python3 -m venv .venv
source .venv/bin/activate       # Linux/macOS
# .venv\Scripts\activate       # Windows

pip install -r requirements.txt
```

### Step 6 — Configure environment

```bash
cp .env.example .env
```

Edit `.env` for local dev:
```env
OLLAMA_BASE_URL=http://localhost:11434
REDIS_URL=redis://localhost:6379
DEBUG=true
```

### Step 7 — Run the server

```bash
# From the project root
python -m uvicorn server.main:app --host 0.0.0.0 --port 8000 --reload
```

### Step 8 — Open the UI

Navigate to **http://localhost:8000**

---

## 📚 Adding Documents to the Knowledge Base

The RAG system lets your agent answer questions from your own documents.

### Via the Web UI

1. Open the sidebar (right panel)
2. Paste text into "Ingest Document"
3. Click "Add to Knowledge Base"

### Via the API

```bash
curl -X POST http://localhost:8000/api/ingest \
  -H "Content-Type: application/json" \
  -d '{"text": "Your document content here...", "source": "my-doc"}'
```

### Via the file system

Drop files into `data/documents/` — supported formats:
- `.txt` — plain text
- `.md` — Markdown
- `.pdf` — PDF (text-extractable)
- `.json` — JSON with `content` or `text` field

Documents are **automatically ingested** when the server starts if the FAISS index is empty.

**Force re-index** existing documents:
```bash
# Delete the index and restart
rm -rf data/faiss_index/*
docker compose restart voice-agent  # or restart the server
```

---

## 🔧 Configuration

All settings are in `.env`. Key options:

### Change the LLM model

```env
OLLAMA_MODEL=mistral        # Or phi3.5, qwen2.5:7b, etc.
```

Then pull the model: `ollama pull mistral`

### Change the TTS voice

```env
TTS_VOICE=en-GB-SoniaNeural   # British female
TTS_VOICE=en-US-GuyNeural     # US male
```

List available voices via API: `GET /api/voices`

### Use a larger Whisper model (better accuracy)

```env
WHISPER_MODEL=small.en    # More accurate but slower
WHISPER_MODEL=medium.en   # Best accuracy for English
```

### GPU acceleration

For CUDA GPU support:
```env
WHISPER_DEVICE=cuda
WHISPER_COMPUTE_TYPE=float16
```

Uncomment the GPU section in `docker-compose.yml` for Ollama GPU:
```yaml
deploy:
  resources:
    reservations:
      devices:
        - driver: nvidia
          count: 1
          capabilities: [gpu]
```

---

## 🔒 HTTPS Setup

Chrome blocks microphone on non-localhost HTTP. For remote deployment:

### Option A — Self-signed cert (development)

```bash
mkdir infra/certs
openssl req -x509 -newkey rsa:4096 -keyout infra/certs/key.pem \
  -out infra/certs/cert.pem -days 365 -nodes \
  -subj "/CN=voice-agent"
```

Update `nginx.conf`:
```nginx
listen 443 ssl;
ssl_certificate /etc/nginx/certs/cert.pem;
ssl_certificate_key /etc/nginx/certs/key.pem;
```

### Option B — Let's Encrypt (production)

```bash
certbot certonly --webroot -w /var/www/html -d yourdomain.com
```

---

## 📡 API Reference

| Endpoint | Method | Description |
|----------|--------|-------------|
| `GET /api/health` | GET | Full health check with service status |
| `GET /api/health/ready` | GET | Simple readiness probe |
| `POST /api/ingest` | POST | Add text to knowledge base |
| `GET /api/voices` | GET | List available TTS voices |
| `WS /ws/audio` | WS | Main audio streaming endpoint |
| `WS /ws/webrtc/{id}` | WS | WebRTC signaling (optional) |

### WebSocket Protocol

**Client → Server:**

```jsonc
// Start session
{ "type": "session_start", "data": { "format": "pcm16", "sample_rate": 16000 } }

// Binary audio frames (raw PCM Int16 LE)

// Signal end of speech
{ "type": "audio_end", "timestamp": 1234567890 }

// Keep-alive
{ "type": "ping", "timestamp": 1234567890 }
```

**Server → Client:**

```jsonc
// Session established
{ "type": "session_start", "data": { "session_id": "uuid" } }

// Final transcript
{ "type": "transcript", "data": { "text": "Hello world", "is_final": true } }

// Streaming LLM text tokens
{ "type": "response_text", "data": { "text": "token", "is_final": false } }

// Audio chunk (base64 MP3)
{ "type": "response_audio", "data": { "audio": "base64...", "sample_rate": 24000 } }

// Audio stream complete
{ "type": "response_audio_end" }
```

---

## 🐛 Troubleshooting

### "Could not transcribe audio"
- Check microphone permissions in browser
- Ensure HTTPS or localhost
- Try a louder/clearer voice input

### "Ollama connection failed"
```bash
# Check Ollama is running
curl http://localhost:11434/api/tags

# Pull required model
ollama pull llama3.2
```

### "Redis unavailable" (warning, non-fatal)
The app works without Redis — just without caching and persistent memory.
```bash
redis-cli ping  # Should return PONG
```

### Docker: models stuck downloading
```bash
docker compose logs -f ollama
docker compose logs -f ollama-init
```

### Slow responses
- Switch to a smaller Whisper model: `WHISPER_MODEL=tiny.en`
- Switch to a smaller LLM: `OLLAMA_MODEL=phi3.5`
- Enable GPU if available

### View logs
```bash
# All services
docker compose logs -f

# Just the API
docker compose logs -f voice-agent
```

---

## 📁 Project Structure

```
voice-agent/
├── client/              # TypeScript client library
│   ├── web/
│   │   ├── microphone.ts    # Mic capture + silence detection
│   │   ├── audio-player.ts  # PCM/MP3 playback queue
│   │   ├── webrtc.ts        # WebRTC peer connection
│   │   └── websocket.ts     # Main WS client + state machine
│   └── config.ts
│
├── server/              # Python FastAPI backend
│   ├── main.py              # App entrypoint + lifecycle
│   ├── api/
│   │   ├── websocket_handler.py  # WS audio pipeline
│   │   ├── webrtc_handler.py     # WebRTC signaling
│   │   └── health_check.py       # Health endpoints
│   ├── agents/
│   │   ├── voice_agent.py    # Orchestrates STT→RAG→LLM→TTS
│   │   ├── rag_agent.py      # Document ingestion + retrieval
│   │   └── memory_agent.py   # Conversation memory
│   ├── speech/
│   │   ├── stt.py            # Whisper speech-to-text
│   │   ├── tts.py            # Edge-TTS text-to-speech
│   │   └── audio_processor.py
│   ├── llm/
│   │   ├── ollama_client.py  # Ollama HTTP client
│   │   └── prompt_builder.py
│   ├── embeddings/
│   │   ├── embedding_client.py    # Ollama + fallback embeddings
│   │   └── embedding_pipeline.py  # Document chunking + embedding
│   ├── rag/
│   │   ├── vector_store.py   # FAISS index
│   │   ├── retriever.py      # Semantic search
│   │   └── document_loader.py
│   ├── memory/
│   │   ├── conversation_store.py  # Redis-backed session store
│   │   └── memory_retriever.py    # Auto-summarization
│   ├── cache/
│   │   └── redis_cache.py
│   └── config/
│       ├── settings.py    # Pydantic settings
│       └── constants.py   # Prompts, enums
│
├── static/              # Web UI (served by FastAPI)
│   └── index.html
│
├── data/
│   ├── documents/       # Drop files here for RAG
│   └── faiss_index/     # Auto-generated FAISS index
│
├── infra/
│   ├── docker/
│   │   ├── Dockerfile
│   │   └── docker-compose.yml
│   ├── nginx/nginx.conf
│   └── ollama/ollama-init.sh
│
├── models/
│   ├── model_config.yaml   # Available model reference
│   └── ollama_models.md
│
├── requirements.txt
├── .env.example
└── README.md
```

---

## License

MIT
