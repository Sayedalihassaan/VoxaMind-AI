#!/bin/bash
# Pull required Ollama models at container startup
# This script runs inside the Ollama container

set -e

MODELS=(
  "llama3.2"
  "nomic-embed-text"
)

echo "=== Ollama Model Initialization ==="

for model in "${MODELS[@]}"; do
  echo "Checking model: $model"
  if ollama list | grep -q "$model"; then
    echo "  ✓ $model already present"
  else
    echo "  ⬇  Pulling $model..."
    ollama pull "$model"
    echo "  ✓ $model pulled"
  fi
done

echo "=== All models ready ==="
