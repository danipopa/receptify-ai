#!/usr/bin/env bash
# setup.sh — install all Python dependencies, download Piper voice model,
#             and pull required Ollama models.
# Run once from the project root: bash setup.sh
set -euo pipefail

BASE="$(cd "$(dirname "$0")" && pwd)"
VENV="$BASE/.venv"

PIPER_MODEL_BASE="https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium"
PIPER_ONNX="$BASE/piper/en_US-lessac-medium.onnx"
PIPER_JSON="$BASE/piper/en_US-lessac-medium.onnx.json"

# ---------------------------------------------------------------------------
# 1. Virtual environment
# ---------------------------------------------------------------------------
if [ ! -d "$VENV" ]; then
    echo "==> Creating virtualenv at $VENV"
    python3 -m venv "$VENV"
fi
source "$VENV/bin/activate"
pip install --upgrade pip --quiet

# ---------------------------------------------------------------------------
# 2. Python dependencies (all services share one venv)
# ---------------------------------------------------------------------------
echo "==> Installing Python dependencies..."
for svc in rag-service stt-service tts-service agent; do
    req="$BASE/$svc/requirements.txt"
    if [ -f "$req" ]; then
        echo "    $svc/requirements.txt"
        pip install --quiet -r "$req"
    fi
done

# ---------------------------------------------------------------------------
# 3. Piper voice model
# ---------------------------------------------------------------------------
mkdir -p "$BASE/piper" "$BASE/recordings" "$BASE/context"

if [ ! -f "$BASE/context/ai-ivr-context.txt" ]; then
    echo "==> context/ai-ivr-context.txt not found — using the sample from the repo."
fi

if [ ! -f "$PIPER_ONNX" ]; then
    echo "==> Downloading Piper ONNX model..."
    wget -q --show-progress -O "$PIPER_ONNX" "$PIPER_MODEL_BASE/en_US-lessac-medium.onnx"
else
    echo "==> Piper ONNX model already present, skipping."
fi

if [ ! -f "$PIPER_JSON" ]; then
    echo "==> Downloading Piper model config..."
    wget -q --show-progress -O "$PIPER_JSON" "$PIPER_MODEL_BASE/en_US-lessac-medium.onnx.json"
else
    echo "==> Piper model config already present, skipping."
fi

# ---------------------------------------------------------------------------
# 4. Ollama models
# ---------------------------------------------------------------------------
if command -v ollama &>/dev/null; then
    # Ensure ollama is running before pulling
    if ! curl -sf http://127.0.0.1:11434/ &>/dev/null; then
        echo "==> Ollama not running — starting it in the background..."
        ollama serve &>/dev/null &
        OLLAMA_PID=$!
        echo "    PID $OLLAMA_PID — waiting for it to be ready..."
        for i in $(seq 1 15); do
            curl -sf http://127.0.0.1:11434/ &>/dev/null && break
            sleep 1
        done
    fi

    echo "==> Pulling Ollama models (this may take a while on first run)..."
    ollama pull nomic-embed-text
    ollama pull llama3.2:1b
    ollama pull llama3.2:3b
else
    echo "==> WARNING: ollama not found in PATH. Install it and run:"
    echo "      ollama pull nomic-embed-text"
    echo "      ollama pull llama3.2:1b"
fi

# ---------------------------------------------------------------------------
# 5. Summary
# ---------------------------------------------------------------------------
echo ""
echo "==> Setup complete."
echo "    Activate venv : source $VENV/bin/activate"
echo "    Piper binary  : $VENV/bin/piper"
echo "    Piper model   : $PIPER_ONNX"
echo ""
echo "    Start services (each in its own terminal):"
echo "      python rag-service/main.py"
echo "      python stt-service/main.py"
echo "      PIPER_BIN=$VENV/bin/piper PIPER_MODEL=$PIPER_ONNX python tts-service/main.py"
echo "      python fs-bridge/main.py"
echo "      python agent/main.py"
