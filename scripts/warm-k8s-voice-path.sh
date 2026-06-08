#!/usr/bin/env bash
set -euo pipefail

NAMESPACE="${NAMESPACE:-receptify}"
KUBECTL="${KUBECTL:-kubectl}"
LLM_MODEL="${LLM_MODEL:-llama3.2:1b}"
TTS_TEXT="${TTS_TEXT:-We are open Monday to Friday from 9 to 6.}"

echo "==> Warming Ollama generation"
"$KUBECTL" exec -n "$NAMESPACE" deployment/rag-service -- python3 -c '
import json
import os
import sys
import urllib.request

model = sys.argv[1]
data = json.dumps({
    "model": model,
    "prompt": "Reply with one word: ready",
    "stream": False,
    "options": {"num_predict": 1, "temperature": 0.1},
}).encode()
req = urllib.request.Request(
    "http://ollama:11434/api/generate",
    data=data,
    headers={"Content-Type": "application/json"},
)
print(urllib.request.urlopen(req, timeout=75).read().decode())
' "$LLM_MODEL"

echo ""
echo "==> Warming RAG /generate"
"$KUBECTL" exec -n "$NAMESPACE" deployment/rag-service -- python3 -c '
import json
import urllib.request

data = json.dumps({"prompt": "Answer in one word: ready"}).encode()
req = urllib.request.Request(
    "http://127.0.0.1:9091/generate",
    data=data,
    headers={"Content-Type": "application/json"},
)
print(urllib.request.urlopen(req, timeout=75).read().decode())
'

echo ""
echo "==> Warming TTS cache"
"$KUBECTL" exec -n "$NAMESPACE" deployment/tts-service -- python3 -c '
import json
import sys
import urllib.request

text = sys.argv[1]
data = json.dumps({"text": text, "sample_rate": 8000}).encode()
req = urllib.request.Request(
    "http://127.0.0.1:9093/synthesize",
    data=data,
    headers={"Content-Type": "application/json"},
)
body = urllib.request.urlopen(req, timeout=45).read()
print(f"wav_bytes={len(body)}")
' "$TTS_TEXT"

echo ""
echo "Warmup complete."
