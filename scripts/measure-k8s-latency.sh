#!/usr/bin/env bash
set -euo pipefail

NAMESPACE="${NAMESPACE:-receptify}"
QUERY_TEXT="${QUERY_TEXT:-What are your working hours?}"
QUERY_TOP_K="${QUERY_TOP_K:-4}"
TTS_TEXT="${TTS_TEXT:-We are open Monday to Friday from 9 to 6.}"
LLM_PROMPT="${LLM_PROMPT:-Answer in one short sentence: Our hours are Monday-Friday 9-6 and Saturday 10-2. Caller asks: what are your hours?}"

KUBECTL="${KUBECTL:-kubectl}"

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
  "$KUBECTL" exec -n "$NAMESPACE" deployment/rag-service -- python3 -c '
import json
import sys
import urllib.request

text = sys.argv[1]
top_k = int(sys.argv[2])
data = json.dumps({"text": text, "top_k": top_k}).encode()
req = urllib.request.Request(
    "http://127.0.0.1:9091/query",
    data=data,
    headers={"Content-Type": "application/json"},
)
print(urllib.request.urlopen(req, timeout=15).read().decode())
' "$QUERY_TEXT" "$QUERY_TOP_K"

time_step "RAG /generate" \
  "$KUBECTL" exec -n "$NAMESPACE" deployment/rag-service -- python3 -c '
import json
import sys
import urllib.request

prompt = sys.argv[1]
data = json.dumps({"prompt": prompt}).encode()
req = urllib.request.Request(
    "http://127.0.0.1:9091/generate",
    data=data,
    headers={"Content-Type": "application/json"},
)
print(urllib.request.urlopen(req, timeout=75).read().decode())
' "$LLM_PROMPT"

time_step "Ollama direct /api/generate" \
  "$KUBECTL" exec -n "$NAMESPACE" deployment/rag-service -- python3 -c '
import json
import sys
import urllib.request

prompt = sys.argv[1]
data = json.dumps({
    "model": "llama3.2:1b",
    "prompt": prompt,
    "stream": False,
    "options": {"num_predict": 32, "temperature": 0.1},
}).encode()
req = urllib.request.Request(
    "http://ollama:11434/api/generate",
    data=data,
    headers={"Content-Type": "application/json"},
)
print(urllib.request.urlopen(req, timeout=75).read().decode())
' "$LLM_PROMPT"

time_step "TTS /synthesize" \
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
echo "Done."
