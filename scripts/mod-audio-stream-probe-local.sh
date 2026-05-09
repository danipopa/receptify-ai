#!/usr/bin/env bash
set -euo pipefail

BASE="$(cd "$(dirname "$0")/.." && pwd)"
VENV="${VENV:-$BASE/.venv}"
LOGS="${LOGS:-$BASE/logs}"
ENV_FILE="${ENV_FILE:-$BASE/.env}"
TEXT="${MOD_AUDIO_STREAM_PROBE_TEXT:-This is a mod audio stream playback test.}"

if [ ! -f "$ENV_FILE" ]; then
  echo "Missing env file: $ENV_FILE" >&2
  exit 1
fi

if [ ! -f "$VENV/bin/activate" ]; then
  echo "Missing virtualenv: $VENV" >&2
  exit 1
fi

mkdir -p "$LOGS"

if [ -f "$LOGS/agent.pid" ] && kill -0 "$(cat "$LOGS/agent.pid")" 2>/dev/null; then
  echo "Stopping existing agent pid $(cat "$LOGS/agent.pid")"
  kill "$(cat "$LOGS/agent.pid")"
  sleep 1
fi

set -a
# shellcheck disable=SC1090
source "$ENV_FILE"
set +a

export AUDIO_PLAYBACK_MODE=mod_audio_stream
export MOD_AUDIO_STREAM_PROBE_TEXT="$TEXT"

# shellcheck disable=SC1091
source "$VENV/bin/activate"

echo "Starting local agent with mod_audio_stream probe enabled"
echo "Probe text: $MOD_AUDIO_STREAM_PROBE_TEXT"
nohup python "$BASE/agent/main.py" >> "$LOGS/agent.log" 2>&1 &
echo $! > "$LOGS/agent.pid"

echo ""
echo "Agent restarted. Make a test call now."
echo "Watch logs with:"
echo "  tail -f $LOGS/agent.log"
echo ""
echo "To go back to normal:"
echo "  bash stop.sh && bash start.sh"
