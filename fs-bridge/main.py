"""
fs-bridge — FreeSWITCH ESL HTTP bridge.

Connects directly to FreeSWITCH ESL (port 8021) over a persistent TCP socket;
no fs_cli binary required.

Endpoints:
  GET  /health
  GET  /ready
  GET  /uuid/{uuid}/exists             → {"exists": true}
  POST /uuid/{uuid}/broadcast          body: WAV bytes (audio/wav)
                                       → {"status": "ok", "duration": 3.2}
  POST /uuid/{uuid}/command            body: {"command": "..."}
                                       → {"output": "..."}
  POST /sync/reload                    → {"status": "ok"}
                                       Triggers ESL "sofia profile external rescan";
                                       FreeSWITCH re-fetches sofia.conf from xml_curl
                                       (picking up gateway add/remove from the API DB).

Environment variables:
  FS_HOST        127.0.0.1
  FS_PORT        8021
  FS_PASSWORD    R3c3pt1fy#ESL@xP9kZm2X
  HOST           0.0.0.0
  PORT           9094
  WAV_DIR        /tmp/fs-bridge-wav
  LOG_LEVEL      INFO
"""

import datetime
import json
import logging
import os
import re
import socket
import threading
import wave
from http.server import BaseHTTPRequestHandler, HTTPServer

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

FS_HOST     = os.getenv("FS_HOST",     "127.0.0.1")
FS_PORT     = int(os.getenv("FS_PORT", "8021"))
FS_PASSWORD = os.getenv("FS_PASSWORD", "R3c3pt1fy#ESL@xP9kZm2X")
HOST        = os.getenv("HOST",        "0.0.0.0")
PORT        = int(os.getenv("PORT",    "9094"))
WAV_DIR     = os.getenv("WAV_DIR",     "/tmp/fs-bridge-wav")
LOG_LEVEL   = os.getenv("LOG_LEVEL",   "INFO").upper()

os.makedirs(WAV_DIR, exist_ok=True)

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

class JsonFormatter(logging.Formatter):
    def format(self, record):
        return json.dumps({
            "ts":      datetime.datetime.utcnow().isoformat() + "Z",
            "level":   record.levelname,
            "msg":     record.getMessage(),
            "service": "fs-bridge",
        })

_h = logging.StreamHandler()
_h.setFormatter(JsonFormatter())
logging.root.setLevel(LOG_LEVEL)
logging.root.handlers = [_h]
log = logging.getLogger("fs-bridge")

UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.IGNORECASE,
)

# ---------------------------------------------------------------------------
# ESL connection
# ---------------------------------------------------------------------------

class ESLConnection:
    """Persistent FreeSWITCH ESL API connection with auto-reconnect."""

    def __init__(self, host: str, port: int, password: str) -> None:
        self._host = host
        self._port = port
        self._password = password
        self._sock: socket.socket | None = None
        self._lock = threading.Lock()

    def _read_packet(self, sock: socket.socket) -> dict:
        """Read one ESL packet → {"headers": {…}, "body": str}."""
        buf = b""
        while b"\n\n" not in buf:
            chunk = sock.recv(4096)
            if not chunk:
                raise ConnectionError("ESL socket closed")
            buf += chunk

        header_bytes, remainder = buf.split(b"\n\n", 1)
        headers: dict[str, str] = {}
        for line in header_bytes.decode(errors="replace").splitlines():
            if ":" in line:
                k, _, v = line.partition(":")
                headers[k.strip()] = v.strip()

        content_len = int(headers.get("Content-Length", 0))
        body = remainder
        while len(body) < content_len:
            chunk = sock.recv(4096)
            if not chunk:
                raise ConnectionError("ESL socket closed")
            body += chunk

        return {"headers": headers, "body": body[:content_len].decode(errors="replace")}

    def _connect(self) -> None:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(10)
        sock.connect((self._host, self._port))

        pkt = self._read_packet(sock)
        if pkt["headers"].get("Content-Type") != "auth/request":
            raise ConnectionError(f"Unexpected ESL greeting: {pkt['headers']}")

        sock.sendall(f"auth {self._password}\n\n".encode())
        pkt = self._read_packet(sock)
        reply = pkt["headers"].get("Reply-Text", "")
        if not reply.startswith("+OK"):
            raise ConnectionError(f"ESL auth rejected: {reply}")

        self._sock = sock
        log.info("ESL connected to %s:%d", self._host, self._port)

    def _close(self) -> None:
        if self._sock:
            try:
                self._sock.close()
            except Exception:
                pass
            self._sock = None

    def api(self, command: str, timeout: int = 10) -> str:
        """Send an ESL API command and return the response body."""
        with self._lock:
            for attempt in range(2):
                try:
                    if self._sock is None:
                        self._connect()
                    self._sock.settimeout(timeout)  # type: ignore[union-attr]
                    self._sock.sendall(f"api {command}\n\n".encode())  # type: ignore[union-attr]
                    pkt = self._read_packet(self._sock)  # type: ignore[arg-type]
                    return pkt["body"].strip()
                except Exception as exc:
                    log.warning("ESL api (attempt %d) %s: %s", attempt + 1, command, exc)
                    self._close()
            return ""


_esl = ESLConnection(FS_HOST, FS_PORT, FS_PASSWORD)


def _fs_cmd(command: str, timeout: int = 5) -> str:
    return _esl.api(command, timeout=timeout)


def uuid_exists(call_uuid: str) -> bool:
    return _fs_cmd(f"uuid_exists {call_uuid}", timeout=3) == "true"


def get_wav_duration(path: str) -> float:
    try:
        with wave.open(path, "r") as f:
            return f.getnframes() / float(f.getframerate())
    except Exception:
        return 3.0


def broadcast_wav(call_uuid: str, wav_path: str) -> float:
    cmd = f"uuid_broadcast {call_uuid} {wav_path} aleg"
    log.info("Broadcast: %s", cmd)
    _fs_cmd(cmd, timeout=8)
    return get_wav_duration(wav_path)


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

    def _read_body(self) -> bytes:
        n = int(self.headers.get("Content-Length", 0))
        return self.rfile.read(n) if n else b""

    def _parse_uuid(self) -> str | None:
        # /uuid/<uuid>/...
        parts = [p for p in self.path.split("/") if p]
        if len(parts) >= 2 and parts[0] == "uuid":
            candidate = parts[1]
            if UUID_RE.match(candidate):
                return candidate
        return None

    def _is_sync_reload(self) -> bool:
        parts = [p for p in self.path.split("/") if p]
        return parts == ["sync", "reload"]

    def do_GET(self):
        if self.path in ("/health", "/ready"):
            self._send_json(200, {"status": "ok", "service": "fs-bridge"})
            return

        call_uuid = self._parse_uuid()
        if call_uuid and self.path.endswith("/exists"):
            exists = uuid_exists(call_uuid)
            self._send_json(200, {"exists": exists, "uuid": call_uuid})
            return

        self._send_json(404, {"error": "not found"})

    def do_POST(self):
        call_uuid = self._parse_uuid()

        if call_uuid and self.path.endswith("/broadcast"):
            try:
                wav_bytes = self._read_body()
                if not wav_bytes:
                    self._send_json(400, {"error": "WAV body required"})
                    return

                if not uuid_exists(call_uuid):
                    self._send_json(404, {"error": "call uuid not found"})
                    return

                # WAV path must be accessible by FreeSWITCH (same node, shared volume)
                ts  = datetime.datetime.utcnow().strftime("%Y%m%d-%H%M%S-%f")
                wav = os.path.join(WAV_DIR, f"tts-{call_uuid[:8]}-{ts}.wav")
                with open(wav, "wb") as f:
                    f.write(wav_bytes)

                duration = broadcast_wav(call_uuid, wav)
                self._send_json(200, {"status": "ok", "duration": duration})

            except Exception as e:
                log.exception("broadcast error: %s", e)
                self._send_json(500, {"error": str(e)})
            return

        if call_uuid and self.path.endswith("/command"):
            try:
                body    = json.loads(self._read_body() or b"{}")
                command = str(body.get("command", "")).strip()
                if not command:
                    self._send_json(400, {"error": "command required"})
                    return
                output = _fs_cmd(command)
                self._send_json(200, {"output": output})
            except Exception as e:
                log.exception("command error: %s", e)
                self._send_json(500, {"error": str(e)})
            return

        if self._is_sync_reload():
            try:
                self._read_body()  # drain
                _fs_cmd("sofia profile external rescan", timeout=15)
                log.info("sofia profile external rescan triggered")
                self._send_json(200, {"status": "ok"})
            except Exception as e:
                log.exception("reload error: %s", e)
                self._send_json(500, {"error": str(e)})
            return

        self._send_json(404, {"error": "not found"})


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    server = HTTPServer((HOST, PORT), Handler)
    log.info("fs-bridge listening on http://%s:%d", HOST, PORT)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        log.info("Shutting down")
