# Ollama Models Reference

## Pull Commands

```bash
# LLM
ollama pull llama3.2       # 2B - recommended default (fast, 4GB RAM)
ollama pull llama3.2:3b    # 3B - better reasoning
ollama pull mistral        # 7B - strong instruction following
ollama pull phi3.5         # 3.8B - Microsoft efficient model

# Embedding
ollama pull nomic-embed-text  # 768-dim - default
ollama pull mxbai-embed-large # 1024-dim - higher quality
```

## Switch Model Without Restart

Update your `.env` file and restart the voice-agent container:
```bash
OLLAMA_MODEL=mistral
docker compose restart voice-agent
```
