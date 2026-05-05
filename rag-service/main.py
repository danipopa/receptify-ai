"""
rag-service — Retrieval-Augmented Generation microservice.

Chunks the FAQ file, embeds chunks via Ollama embeddings API,
does cosine-similarity search at query time, and proxies LLM generation.

Endpoints:
  GET  /health
  GET  /ready
  POST /query      {"text": "...", "top_k": 3}   → {"context": "..."}
  POST /generate   {"prompt": "..."}              → {"reply": "..."}
  POST /rebuild                                   → 202 {"status": "building"} (non-blocking)

Environment variables:
  FAQ_FILE          /opt/ai-ivr-context.txt
  EMBEDDING_MODEL   nomic-embed-text
  LLM_MODEL         llama3.2:1b
  OLLAMA_HOST       127.0.0.1:11434
  RAG_CHUNK_WORDS   60
  RAG_TOP_K         3
  OLLAMA_TIMEOUT    20
  HOST              0.0.0.0
  PORT              9091
  LOG_LEVEL         INFO
"""

import datetime
import json
import logging
import os
import re
import threading
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import numpy as np

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

FAQ_DIR         = os.getenv("FAQ_DIR",        "/faq")
FAQ_FILE        = os.getenv("FAQ_FILE",        os.path.join(FAQ_DIR, "default.txt"))
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "nomic-embed-text")
LLM_MODEL       = os.getenv("LLM_MODEL",       "llama3.2:3b")
OLLAMA_HOST     = os.getenv("OLLAMA_HOST",     "127.0.0.1:11434")
RAG_CHUNK_WORDS = int(os.getenv("RAG_CHUNK_WORDS", "30"))
RAG_TOP_K       = int(os.getenv("RAG_TOP_K",       "4"))
OLLAMA_TIMEOUT  = int(os.getenv("OLLAMA_TIMEOUT",  "20"))
HOST            = os.getenv("HOST",  "0.0.0.0")
PORT            = int(os.getenv("PORT", "9091"))
LOG_LEVEL       = os.getenv("LOG_LEVEL", "INFO").upper()

os.environ.setdefault("HOME", "/root")
os.environ["OLLAMA_HOST"] = OLLAMA_HOST

ANSI_RE = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")
CTRL_RE = re.compile(r"[\x00-\x1f\x7f-\x9f]")
SPIN_RE = re.compile(r"[⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏]")

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

class JsonFormatter(logging.Formatter):
    def format(self, record):
        return json.dumps({
            "ts":      datetime.datetime.utcnow().isoformat() + "Z",
            "level":   record.levelname,
            "msg":     record.getMessage(),
            "service": "rag",
        })

_h = logging.StreamHandler()
_h.setFormatter(JsonFormatter())
logging.root.setLevel(LOG_LEVEL)
logging.root.handlers = [_h]
log = logging.getLogger("rag")

# ---------------------------------------------------------------------------
# RAG store
# ---------------------------------------------------------------------------

class RagStore:
    EMPTY    = "empty"
    BUILDING = "building"
    READY    = "ready"

    def __init__(self, faq_file: str = FAQ_FILE) -> None:
        self.faq_file      = faq_file
        self._lock         = threading.RLock()
        self._build_lock   = threading.Lock()   # only one build at a time
        self._chunks: list[str]             = []
        self._embeddings: np.ndarray | None = None
        self._state: str                    = self.EMPTY

    @property
    def state(self) -> str:
        with self._lock:
            return self._state

    # ---- helpers -----------------------------------------------------------

    def _ollama_post(self, path: str, payload: dict, timeout: int = 10) -> dict:
        data = json.dumps(payload).encode()
        req  = urllib.request.Request(
            f"http://{OLLAMA_HOST}{path}",
            data=data,
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read())

    def _embed(self, text: str, warn: bool = True) -> np.ndarray | None:
        try:
            r = self._ollama_post("/api/embeddings", {"model": EMBEDDING_MODEL, "prompt": text})
            return np.array(r["embedding"], dtype=np.float32)
        except Exception as e:
            if warn:
                log.warning("embed error: %s", e)
            return None

    def _load_text(self) -> str:
        if os.path.exists(self.faq_file):
            with open(self.faq_file, "r", encoding="utf-8") as f:
                return f.read()
        return "Working hours are Monday to Friday, 9 AM to 5 PM."

    # ---- public ------------------------------------------------------------

    def build(self) -> int:
        """(Re)build synchronously. Returns chunk count."""
        with self._lock:
            self._state = self.BUILDING

        try:
            text  = self._load_text()
            words = text.split()
            chunks = [
                " ".join(words[i : i + RAG_CHUNK_WORDS])
                for i in range(0, len(words), RAG_CHUNK_WORDS)
                if words[i : i + RAG_CHUNK_WORDS]
            ]
            if not chunks:
                log.warning("No chunks to embed — empty FAQ?")
                with self._lock:
                    self._chunks     = []
                    self._embeddings = None
                    self._state      = self.EMPTY
                return 0

            log.info("Embedding %d chunks with %s", len(chunks), EMBEDDING_MODEL)
            embed_failed = False
            raw = []
            for c in chunks:
                emb = self._embed(c)
                if emb is None and not embed_failed:
                    embed_failed = True
                    log.warning("Embedding model unavailable — running without vector search (full-context fallback)")
                raw.append(emb if emb is not None else np.zeros(1, dtype=np.float32))

            matrix = None
            if len({e.shape for e in raw}) == 1:
                matrix = np.stack(raw)

            with self._lock:
                self._chunks     = chunks
                self._embeddings = matrix
                self._state      = self.READY

            log.info("RAG store ready: %d chunks", len(chunks))
            return len(chunks)

        except Exception:
            with self._lock:
                self._state = self.EMPTY
            raise

    def build_in_background(self) -> bool:
        """Start a background build. Returns False if one is already running."""
        if not self._build_lock.acquire(blocking=False):
            return False

        def _run() -> None:
            try:
                self.build()
            except Exception as exc:
                log.exception("Background build failed: %s", exc)
            finally:
                self._build_lock.release()

        threading.Thread(target=_run, daemon=True, name="rag-build").start()
        return True

    def query(self, text: str, top_k: int = RAG_TOP_K) -> str:
        with self._lock:
            chunks     = list(self._chunks)
            embeddings = self._embeddings

        if not chunks:
            return self._load_text()

        if embeddings is None:
            # No embeddings available — return all chunks so LLM has full context
            log.warning("Embeddings unavailable, returning all %d chunks", len(chunks))
            return "\n\n".join(chunks)

        q = self._embed(text, warn=False)
        if q is None or q.shape != embeddings[0].shape:
            # Silent fallback — embedding model unavailable, full context already logged at build time
            return "\n\n".join(chunks)

        norms  = np.linalg.norm(embeddings, axis=1, keepdims=True)
        norms  = np.where(norms == 0, 1e-9, norms)
        scores = (embeddings / norms) @ (q / (np.linalg.norm(q) or 1e-9))
        top    = np.argsort(scores)[::-1][:top_k]
        return "\n\n".join(chunks[i] for i in top)

    def generate(self, prompt: str) -> str:
        try:
            r = self._ollama_post(
                "/api/generate",
                {"model": LLM_MODEL, "prompt": prompt, "stream": False},
                timeout=OLLAMA_TIMEOUT,
            )
            raw = r.get("response", "")
            raw = ANSI_RE.sub("", raw)
            raw = CTRL_RE.sub("", raw)
            raw = SPIN_RE.sub("", raw)
            raw = re.sub(r"\s+", " ", raw).strip()
            return raw or "Sorry, I do not have that information."
        except Exception as e:
            log.warning("generate error: %s", e)
            return "Sorry, I do not have that information."


store = RagStore()

# Per-tenant store registry: tenant_id (int) → RagStore
_tenant_stores: dict[int, RagStore] = {}
_tenant_stores_lock = threading.Lock()


def get_tenant_store(tenant_id: int) -> RagStore:
    """Return (and lazily build) the store for a given tenant."""
    with _tenant_stores_lock:
        if tenant_id not in _tenant_stores:
            faq = os.path.join(FAQ_DIR, f"{tenant_id}.txt")
            ts = RagStore(faq_file=faq)
            _tenant_stores[tenant_id] = ts
            ts.build_in_background()
            log.info("Created store for tenant_id=%d faq=%s", tenant_id, faq)
        return _tenant_stores[tenant_id]

# ---------------------------------------------------------------------------
# HTTP handler
# ---------------------------------------------------------------------------

class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        log.info(fmt, *args)

    def _send_json(self, status: int, obj: dict):
        body = json.dumps(obj).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_json(self) -> dict:
        n   = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(n) if n else b"{}"
        return json.loads(raw)

    def do_GET(self):
        if self.path == "/health":
            self._send_json(200, {"status": "ok", "service": "rag",
                                  "store": store.state, "chunks": len(store._chunks)})
        elif self.path == "/ready":
            st = store.state
            if st == RagStore.READY:
                self._send_json(200, {"status": "ready", "chunks": len(store._chunks)})
            else:
                self._send_json(503, {"status": st})
        else:
            self._send_json(404, {"error": "not found"})

    def do_POST(self):
        if self.path == "/query":
            try:
                body       = self._read_json()
                text       = str(body.get("text", "")).strip()
                top_k      = int(body.get("top_k", RAG_TOP_K))
                tenant_id  = body.get("tenant_id")
                if not text:
                    self._send_json(400, {"error": "text required"})
                    return
                active_store = get_tenant_store(int(tenant_id)) if tenant_id else store
                context = active_store.query(text, top_k)
                log.info("query tenant=%s top_k=%d → %d chars", tenant_id, top_k, len(context))
                self._send_json(200, {"context": context})
            except Exception as e:
                log.exception("query error: %s", e)
                self._send_json(500, {"error": str(e)})

        elif self.path == "/generate":
            try:
                body   = self._read_json()
                prompt = str(body.get("prompt", "")).strip()
                if not prompt:
                    self._send_json(400, {"error": "prompt required"})
                    return
                reply = store.generate(prompt)
                log.info("generate → %r", reply)
                self._send_json(200, {"reply": reply})
            except Exception as e:
                log.exception("generate error: %s", e)
                self._send_json(500, {"error": str(e)})

        elif self.path == "/rebuild":
            body = self._read_json() if self.headers.get("Content-Length", "0") != "0" else {}
            tenant_id = body.get("tenant_id")
            target = get_tenant_store(int(tenant_id)) if tenant_id else store
            started = target.build_in_background()
            if started:
                self._send_json(202, {"status": "building", "tenant_id": tenant_id})
            else:
                self._send_json(200, {"status": "already_building"})

        else:
            self._send_json(404, {"error": "not found"})


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    store.build_in_background()   # non-blocking; /ready returns 503 until done
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    log.info("RAG service listening on http://%s:%d (ThreadingHTTPServer)", HOST, PORT)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        log.info("Shutting down")
