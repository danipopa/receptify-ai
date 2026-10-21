"""
rag-service — Retrieval-Augmented Generation microservice.

Chunks the FAQ file, embeds chunks via Ollama embeddings API,
does cosine-similarity search at query time, and proxies LLM generation.

Endpoints:
  GET  /health
  GET  /ready
  POST /query      {"text": "...", "top_k": 3}   → {"context": "..."}
  POST /generate   {"prompt": "..."}              → {"reply": "..."}
  POST /generate_stream {"prompt": "..."}          → newline-delimited JSON tokens
  POST /rebuild                                   → 202 {"status": "building"} (non-blocking)

Environment variables:
  FAQ_FILE          /opt/ai-ivr-context.txt
  EMBEDDING_MODEL   nomic-embed-text
  LLM_MODEL         llama3.2:1b
  OLLAMA_HOST       127.0.0.1:11434 or https://ollama.example.com
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
import time
import urllib.request
from collections import OrderedDict
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
LLM_NUM_PREDICT = int(os.getenv("LLM_NUM_PREDICT", "48"))
LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.1"))
HOST            = os.getenv("HOST",  "0.0.0.0")
PORT            = int(os.getenv("PORT", "9091"))
LOG_LEVEL       = os.getenv("LOG_LEVEL", "INFO").upper()
API_URL         = os.getenv("API_URL", "http://receptify-api").rstrip("/")
INTERNAL_TOKEN  = os.getenv("INTERNAL_TOKEN", "").strip()
MAX_WORKSPACE_STORES = 64

os.environ.setdefault("HOME", "/root")
os.environ["OLLAMA_HOST"] = OLLAMA_HOST
OLLAMA_BASE_URL = OLLAMA_HOST if OLLAMA_HOST.startswith(("http://", "https://")) else f"http://{OLLAMA_HOST}"

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
        self._text_override: str | None     = None
        self._content_revision              = 0

    @property
    def state(self) -> str:
        with self._lock:
            return self._state

    # ---- helpers -----------------------------------------------------------

    def _ollama_post(self, path: str, payload: dict, timeout: int = 10) -> dict:
        data = json.dumps(payload).encode()
        req  = urllib.request.Request(
            f"{OLLAMA_BASE_URL}{path}",
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
        if self._text_override is not None:
            return self._text_override
        if os.path.exists(self.faq_file):
            with open(self.faq_file, "r", encoding="utf-8") as f:
                return f.read()
        return "Working hours are Monday to Friday, 9 AM to 5 PM."

    @staticmethod
    def _split_chunks(text: str) -> list[str]:
        words = text.split()
        return [
            " ".join(words[i : i + RAG_CHUNK_WORDS])
            for i in range(0, len(words), RAG_CHUNK_WORDS)
            if words[i : i + RAG_CHUNK_WORDS]
        ]

    def set_content(self, text: str) -> bool:
        with self._lock:
            if self._text_override == text:
                return False
            self._text_override = text
            self._content_revision += 1
            self._chunks = []
            self._embeddings = None
            self._state = self.EMPTY
            return True

    # ---- public ------------------------------------------------------------

    def build(self) -> int:
        """(Re)build synchronously. Returns chunk count."""
        with self._lock:
            self._state = self.BUILDING
            revision = self._content_revision
            workspace_content = self._text_override is not None

        try:
            text  = self._load_text()
            chunks = self._split_chunks(text)
            if not chunks:
                log.warning("No chunks to embed — empty FAQ?")
                with self._lock:
                    if revision != self._content_revision:
                        self._state = self.EMPTY
                        return 0
                    self._chunks     = []
                    self._embeddings = None
                    self._state      = self.EMPTY
                return 0

            if workspace_content:
                with self._lock:
                    if revision != self._content_revision:
                        self._state = self.EMPTY
                        return 0
                    self._chunks = chunks
                    self._embeddings = None
                    self._state = self.READY
                log.info("Workspace lexical index ready: %d chunks", len(chunks))
                return len(chunks)

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
                # pre-normalise once so query() is a single dot-product
                norms = np.linalg.norm(matrix, axis=1, keepdims=True)
                matrix = matrix / np.where(norms == 0, 1e-9, norms)

            with self._lock:
                if revision != self._content_revision:
                    self._state = self.EMPTY
                    return 0
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
                while True:
                    with self._lock:
                        revision = self._content_revision
                    self.build()
                    with self._lock:
                        if revision == self._content_revision or not self._load_text().strip():
                            break
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
            chunks = self._split_chunks(self._load_text())
            if not chunks:
                return ""

        if embeddings is None:
            return self._keyword_context(text, chunks, top_k)

        q = self._embed(text, warn=False)
        if q is None or q.shape != embeddings[0].shape:
            return self._keyword_context(text, chunks, top_k)

        # embeddings are pre-normalised at build time
        scores = embeddings @ (q / (np.linalg.norm(q) or 1e-9))
        top    = np.argsort(scores)[::-1][:top_k]
        return "\n\n".join(chunks[i] for i in top)

    @staticmethod
    def _keyword_context(text: str, chunks: list[str], top_k: int) -> str:
        stop_words = {
            "a", "an", "and", "are", "as", "at", "be", "can", "do", "does",
            "for", "from", "how", "i", "in", "is", "it", "me", "my", "of",
            "on", "or", "our", "that", "the", "their", "they", "this", "to",
            "we", "what", "with", "you", "your",
        }
        terms = set(re.findall(r"[a-z0-9]+", text.lower())) - stop_words
        limit = max(1, min(int(top_k), len(chunks)))
        if not terms:
            return "\n\n".join(chunks[:limit])

        tokenized_chunks = [
            set(re.findall(r"[a-z0-9]+", chunk.lower()))
            for chunk in chunks
        ]
        ranked = sorted(
            (
                (len(terms & tokens), index)
                for index, tokens in enumerate(tokenized_chunks)
                if terms & tokens
            ),
            key=lambda item: (-item[0], item[1]),
        )
        selected = [chunks[index] for _, index in ranked[:limit]] or chunks[:limit]
        log.info("Keyword fallback selected %d of %d chunks", len(selected), len(chunks))
        return "\n\n".join(selected)

    def generate(self, prompt: str) -> str:
        try:
            r = self._ollama_post(
                "/api/generate",
                {
                    "model": LLM_MODEL,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "num_predict": LLM_NUM_PREDICT,
                        "temperature": LLM_TEMPERATURE,
                    },
                },
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

    def generate_stream(self, prompt: str):
        payload = {
            "model": LLM_MODEL,
            "prompt": prompt,
            "stream": True,
            "options": {
                "num_predict": LLM_NUM_PREDICT,
                "temperature": LLM_TEMPERATURE,
            },
        }
        data = json.dumps(payload).encode()
        req = urllib.request.Request(
            f"{OLLAMA_BASE_URL}/api/generate",
            data=data,
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=OLLAMA_TIMEOUT) as resp:
            for raw_line in resp:
                if not raw_line.strip():
                    continue
                try:
                    item = json.loads(raw_line)
                except json.JSONDecodeError:
                    continue
                token = item.get("response", "")
                token = ANSI_RE.sub("", token)
                token = CTRL_RE.sub("", token)
                token = SPIN_RE.sub("", token)
                if token:
                    yield {"token": token}
                if item.get("done"):
                    yield {"done": True}
                    break


store = RagStore()

# Per-tenant store registry: tenant_id (int) → RagStore
_tenant_stores: dict[int, RagStore] = {}
_tenant_stores_lock = threading.Lock()
_workspace_stores: OrderedDict[int, tuple[RagStore, str]] = OrderedDict()
_workspace_stores_lock = threading.Lock()


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


def get_workspace_store(workspace_id: int) -> RagStore:
    request = urllib.request.Request(
        f"{API_URL}/internal/client_workspaces/{workspace_id}/knowledge",
        headers={"X-Internal-Token": INTERNAL_TOKEN} if INTERNAL_TOKEN else {},
    )
    with urllib.request.urlopen(request, timeout=5) as response:
        content_data = json.loads(response.read())

    revision = str(content_data.get("updated_at", ""))
    content = str(content_data.get("content", ""))
    if not revision:
        raise ValueError(f"Workspace {workspace_id} knowledge response is missing updated_at")

    with _workspace_stores_lock:
        cached = _workspace_stores.get(workspace_id)
        if cached and cached[1] == revision:
            _workspace_stores.move_to_end(workspace_id)
            return cached[0]

        active_store = cached[0] if cached else RagStore(faq_file="")
        changed = active_store.set_content(content)
        _workspace_stores[workspace_id] = (active_store, revision)
        _workspace_stores.move_to_end(workspace_id)
        while len(_workspace_stores) > MAX_WORKSPACE_STORES:
            _workspace_stores.popitem(last=False)
        if changed or cached is None:
            active_store.build_in_background()
        log.info(
            "Loaded client workspace knowledge workspace_id=%d status=%s chars=%d",
            workspace_id,
            content_data.get("knowledge_status", "unknown"),
            len(content),
        )
        return active_store


# ---------------------------------------------------------------------------
# HTTP handler
# ---------------------------------------------------------------------------

class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        if self.path.partition("?")[0] not in ("/health", "/ready"):
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
                workspace_id = body.get("workspace_id")
                if not text:
                    self._send_json(400, {"error": "text required"})
                    return
                if workspace_id:
                    active_store = get_workspace_store(int(workspace_id))
                else:
                    active_store = get_tenant_store(int(tenant_id)) if tenant_id else store
                t0 = time.monotonic()
                context = active_store.query(text, top_k)
                duration_ms = round((time.monotonic() - t0) * 1000)
                log.info(
                    "query tenant=%s workspace=%s top_k=%d → %d chars %dms",
                    tenant_id, workspace_id, top_k, len(context), duration_ms
                )
                self._send_json(200, {"context": context, "duration_ms": duration_ms})
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

        elif self.path == "/generate_stream":
            try:
                body   = self._read_json()
                prompt = str(body.get("prompt", "")).strip()
                if not prompt:
                    self._send_json(400, {"error": "prompt required"})
                    return

                self.send_response(200)
                self.send_header("Content-Type", "application/x-ndjson")
                self.send_header("Cache-Control", "no-cache")
                self.end_headers()

                emitted = False
                t0 = time.monotonic()
                for item in store.generate_stream(prompt):
                    if "token" in item:
                        emitted = True
                    if item.get("done"):
                        item["duration_ms"] = round((time.monotonic() - t0) * 1000)
                    self.wfile.write(json.dumps(item).encode() + b"\n")
                    self.wfile.flush()

                if not emitted:
                    fallback = "Sorry, I do not have that information."
                    self.wfile.write(json.dumps({"token": fallback}).encode() + b"\n")
                    self.wfile.write(json.dumps({"done": True, "duration_ms": round((time.monotonic() - t0) * 1000)}).encode() + b"\n")
                    self.wfile.flush()
                log.info("generate_stream complete")
            except (BrokenPipeError, ConnectionResetError):
                log.info("generate_stream client disconnected")
            except Exception as e:
                log.exception("generate_stream error: %s", e)
                try:
                    self.wfile.write(json.dumps({"error": str(e)}).encode() + b"\n")
                    self.wfile.flush()
                except Exception:
                    pass

        elif self.path == "/rebuild":
            body = self._read_json() if self.headers.get("Content-Length", "0") != "0" else {}
            tenant_id = body.get("tenant_id")
            workspace_id = body.get("workspace_id")
            if workspace_id:
                target = get_workspace_store(int(workspace_id))
            else:
                target = get_tenant_store(int(tenant_id)) if tenant_id else store
            started = target.build_in_background()
            if started:
                self._send_json(202, {"status": "building", "tenant_id": tenant_id, "workspace_id": workspace_id})
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
