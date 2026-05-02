#!/usr/bin/env bash
# stop.sh — stop all Receptify AI services started by start.sh
set -euo pipefail

BASE="$(cd "$(dirname "$0")" && pwd)"
LOGS="$BASE/logs"

for svc in rag-service stt-service tts-service fs-bridge agent; do
    pid_file="$LOGS/$svc.pid"
    if [ -f "$pid_file" ]; then
        pid=$(cat "$pid_file")
        if kill -0 "$pid" 2>/dev/null; then
            echo "==> Stopping $svc (PID $pid)"
            kill "$pid"
        else
            echo "==> $svc already stopped"
        fi
        rm -f "$pid_file"
    else
        echo "==> $svc: no PID file found"
    fi
done

echo "==> Done."
