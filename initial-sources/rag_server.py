"""
RAG microservice — HTTP API wrapping Ollama embeddings + cosine retrieval.

Endpoints:
  GET  /health         — liveness probe
  POST /query          — {"text": "...", "top_k": 3}  → {"context": "..."}
  POST /rebuild        — reload FAQ file and rebuild embeddings
"""

import json
import os
import threading
import urllib.request
from http.server import BaseHTTPRequestHandler, HTTPServer

import numpy as np

# ---------------------------------------------------------------------------
# Config (override via env vars)
# ---------------------------------------------------------------------------

FAQ_FILE       = os.getenv("FAQ_FILE",       "/opt/ai-ivr-context.txt")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "nomic-embed-text")
OLLAMA_HOST    = os.getenv("OLLAMA_HOST",    "127.0.0.1:11434")
RAG_CHUNK_WORDS = int(os.getenv("RAG_CHUNK_WORDS", "60"))
RAG_TOP_K       = int(os.getenv("RAG_TOP_K",       "3"))
HOST            = os.getenv("RAG_HOST",  "0.0.0.0")
PORT            = int(os.getenv("RAG_PORT",  "9091"))

os.environ.setdefault("HOME", "/root")
os.environ["OLLAMA_HOST"] = OLLAMA_HOST

# ---------------------------------------------------------------------------
# RAG store
# ---------------------------------------------------------------------------

class RagStore:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._chunks: list[str] = []
        self._embeddings: np.ndarray | None = None

    # ------------------------------------------------------------------ helpers

    def _embed(self, text: str) -> np.ndarray | None:
        try:
            payload = json.dumps({"model": EMBEDDING_MODEL, "prompt": text}).encode()
            req = urllib.request.Request(
                f"http://{OLLAMA_HOST}/api/embeddings",
                data=payload,
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read())
                return np.array(data["embedding"], dtype=np.float32)
        except Exception as e:
            print(f"[rag] embed error: {e}")
            return None

    def _load_text(self) -> str:
        if os.path.exists(FAQ_FILE):
            with open(FAQ_FILE, "r", encoding="utf-8") as f:
                return f.read()
        return "Working hours are Monday to Friday, 9 AM to 5 PM."

    # ------------------------------------------------------------------ public

    def build(self) -> int:
        """(Re)build chunk embeddings from FAQ_FILE. Returns number of chunks."""
        text = self._load_text()
        words = text.split()
        chunks = [
            " ".join(words[i : i + RAG_CHUNK_WORDS])
            for i in range(0, len(words), RAG_CHUNK_WORDS)
            if words[i : i + RAG_CHUNK_WORDS]
        ]

        if not chunks:
            print("[rag] no chunks to embed — empty FAQ file?")
            with self._lock:
                self._chunks = []
                self._embeddings = None
            return 0

        print(f"[rag] embedding {len(chunks)} chunks with {EMBEDDING_MODEL} …")
        raw: list[np.ndarray] = []
        for chunk in chunks:
            emb = self._embed(chunk)
            raw.append(emb if emb is not None else np.zeros(1, dtype=np.float32))

        matrix: np.ndarray | None = None
        shapes = {e.shape for e in raw}
        if len(shapes) == 1:
            matrix = np.stack(raw)

        with self._lock:
            self._chunks = chunks
            self._embeddings = matrix

        print(f"[rag] store ready: {len(chunks)} chunks")
        return len(chunks)

    def query(self, text: str, top_k: int = RAG_TOP_K) -> str:
        with self._lock:
            chunks = list(self._chunks)
            embeddings = self._embeddings

        if not chunks:
            return self._load_text()

        if embeddings is None:
            return "\n\n".join(chunks[:top_k])

        q_emb = self._embed(text)
        if q_emb is None or q_emb.shape != embeddings[0].shape:
            return "\n\n".join(chunks[:top_k])

        norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
        norms = np.where(norms == 0, 1e-9, norms)
        normed = embeddings / norms
        q_norm = q_emb / (np.linalg.norm(q_emb) or 1e-9)
        scores = normed @ q_norm
        top_idx = np.argsort(scores)[::-1][:top_k]
        return "\n\n".join(chunks[i] for i in top_idx)


store = RagStore()

# ---------------------------------------------------------------------------
# HTTP handler
# ---------------------------------------------------------------------------

class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):  # quieter access log
        print(f"[rag] {self.address_string()} {fmt % args}")

    def _send_json(self, status: int, obj: dict):
        body = json.dumps(obj).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_json(self) -> dict:
        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length) if length else b"{}"
        return json.loads(raw)

    def do_GET(self):
        if self.path == "/health":
            self._send_json(200, {"status": "ok", "chunks": len(store._chunks)})
        else:
            self._send_json(404, {"error": "not found"})

    def do_POST(self):
        if self.path == "/query":
            try:
                body = self._read_json()
                text   = str(body.get("text", "")).strip()
                top_k  = int(body.get("top_k", RAG_TOP_K))

                if not text:
                    self._send_json(400, {"error": "text is required"})
                    return

                context = store.query(text, top_k=top_k)
                self._send_json(200, {"context": context})

            except Exception as e:
                self._send_json(500, {"error": str(e)})

        elif self.path == "/rebuild":
            try:
                n = store.build()
                self._send_json(200, {"status": "rebuilt", "chunks": n})
            except Exception as e:
                self._send_json(500, {"error": str(e)})

        else:
            self._send_json(404, {"error": "not found"})


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    store.build()

    server = HTTPServer((HOST, PORT), Handler)
    print(f"[rag] RAG server listening on http://{HOST}:{PORT}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("[rag] shutting down")
