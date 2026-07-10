#!/usr/bin/env bash
# pull_models.sh — pull Ollama models named in config.yaml
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib.sh
source "${SCRIPT_DIR}/lib.sh"

CHAT_MODEL="$(config_get chat_model qwen2.5:7b)"
EMBED_MODEL="$(config_get embed_model nomic-embed-text)"

if ! OLLAMA_BIN="$(find_ollama)"; then
    echo "Ollama not found. Install from https://ollama.com" >&2
    exit 1
fi

ensure_ollama || true

echo "Pulling chat model: ${CHAT_MODEL}"
"${OLLAMA_BIN}" pull "${CHAT_MODEL}"

echo "Pulling embed model: ${EMBED_MODEL}"
"${OLLAMA_BIN}" pull "${EMBED_MODEL}"

echo "Done."