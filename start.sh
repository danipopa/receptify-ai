#!/usr/bin/env bash
# start.sh — start all Receptify AI services in the background.
# Run from the project root: bash start.sh
# Stop everything: bash stop.sh
set -euo pipefail

BASE="$(cd "$(dirname "$0")" && pwd)"
VENV="$BASE/.venv"
LOGS="$BASE/logs"
ENV_FILE="$BASE/.env"

if [ ! -f "$ENV_FILE" ]; then
    echo "==> .env not found — copying from .env.example"
    cp "$BASE/.env.example" "$ENV_FILE"
fi

# Load .env
set -a
# shellcheck disable=SC1090
source "$ENV_FILE"
set +a

source "$VENV/bin/activate"
mkdir -p "$LOGS"

start_service() {
    local name="$1"
    local script="$2"
    local log="$LOGS/$name.log"
    echo "==> Starting $name (log: $log)"
    nohup python "$BASE/$script" >> "$log" 2>&1 &
    echo $! > "$LOGS/$name.pid"
}

start_service "rag-service"  "rag-service/main.py"
start_service "stt-service"  "stt-service/main.py"
start_service "tts-service"  "tts-service/main.py"
start_service "fs-bridge"    "fs-bridge/main.py"

echo "==> Waiting for services to be ready..."
sleep 3

start_service "agent"        "agent/main.py"

# Warm up the LLM so the first real call is not slow
echo "==> Warming up LLM (loading model into memory)..."
curl -s http://127.0.0.1:9091/generate \
  -H 'Content-Type: application/json' \
  -d "{\"prompt\":\"hi\"}" > /dev/null && echo "    LLM warm-up done." || echo "    LLM warm-up skipped (service not yet ready)."

echo ""
echo "==> All services started."
echo "    RAG  : http://${HOST_IP:-127.0.0.1}:9091/health"
echo "    STT  : http://${HOST_IP:-127.0.0.1}:9092/health"
echo "    TTS  : http://${HOST_IP:-127.0.0.1}:9093/health"
echo "    Bridge: http://${HOST_IP:-127.0.0.1}:9094/health"
echo "    Agent WS : ws://${HOST_IP:-127.0.0.1}:9090"
echo "    Agent HTTP: http://${HOST_IP:-127.0.0.1}:9095/health"
echo ""
echo "    Logs : $LOGS/"
echo "    Stop : bash stop.sh"
