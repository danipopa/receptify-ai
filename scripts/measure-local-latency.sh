#!/usr/bin/env bash
set -euo pipefail

QUERY_TEXT="${QUERY_TEXT:-What are your working hours?}"
QUERY_TOP_K="${QUERY_TOP_K:-4}"
TTS_TEXT="${TTS_TEXT:-We are open Monday to Friday from 9 to 6.}"
LLM_PROMPT="${LLM_PROMPT:-Answer in one short sentence: Our hours are Monday-Friday 9-6 and Saturday 10-2. Caller asks: what are your hours?}"

RAG_URL="${RAG_URL:-http://127.0.0.1:9091}"
TTS_URL="${TTS_URL:-http://127.0.0.1:9093}"
OLLAMA_HOST="${OLLAMA_HOST:-127.0.0.1:11434}"
LLM_MODEL="${LLM_MODEL:-llama3.2:1b}"

export RAG_URL
export TTS_URL
export OLLAMA_HOST
export LLM_MODEL

PYTHON="${PYTHON:-python3}"

time_step() {
  local name="$1"
  shift

  echo ""
  echo "==> ${name}"
  local start end elapsed
  start="$(date +%s%3N)"
  "$@"
  end="$(date +%s%3N)"
  elapsed="$((end - start))"
  echo "-- ${name}: ${elapsed} ms"
}

time_step "RAG /query" \
  "$PYTHON" -c '
import json
import os
import sys
import urllib.request

text = sys.argv[1]
top_k = int(sys.argv[2])
rag_url = os.environ["RAG_URL"].rstrip("/")
data = json.dumps({"text": text, "top_k": top_k}).encode()
req = urllib.request.Request(
    f"{rag_url}/query",
    data=data,
    headers={"Content-Type": "application/json"},
)
print(urllib.request.urlopen(req, timeout=15).read().decode())
' "$QUERY_TEXT" "$QUERY_TOP_K"

time_step "RAG /generate" \
  "$PYTHON" -c '
import json
import os
import sys
import urllib.request

prompt = sys.argv[1]
rag_url = os.environ["RAG_URL"].rstrip("/")
data = json.dumps({"prompt": prompt}).encode()
req = urllib.request.Request(
    f"{rag_url}/generate",
    data=data,
    headers={"Content-Type": "application/json"},
)
print(urllib.request.urlopen(req, timeout=75).read().decode())
' "$LLM_PROMPT"

time_step "Ollama direct /api/generate" \
  "$PYTHON" -c '
import json
import os
import sys
import urllib.request

prompt = sys.argv[1]
ollama_host = os.environ["OLLAMA_HOST"]
model = os.environ["LLM_MODEL"]
data = json.dumps({
    "model": model,
    "prompt": prompt,
    "stream": False,
    "options": {"num_predict": 32, "temperature": 0.1},
}).encode()
req = urllib.request.Request(
    f"http://{ollama_host}/api/generate",
    data=data,
    headers={"Content-Type": "application/json"},
)
print(urllib.request.urlopen(req, timeout=75).read().decode())
' "$LLM_PROMPT"

time_step "TTS /synthesize" \
  "$PYTHON" -c '
import json
import os
import sys
import urllib.request

text = sys.argv[1]
tts_url = os.environ["TTS_URL"].rstrip("/")
data = json.dumps({"text": text, "sample_rate": 8000}).encode()
req = urllib.request.Request(
    f"{tts_url}/synthesize",
    data=data,
    headers={"Content-Type": "application/json"},
)
body = urllib.request.urlopen(req, timeout=45).read()
print(f"wav_bytes={len(body)}")
' "$TTS_TEXT"

echo ""
echo "Done."
