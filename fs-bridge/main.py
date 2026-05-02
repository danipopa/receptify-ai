"""
fs-bridge — FreeSWITCH ESL HTTP bridge.

Wraps fs_cli subprocess calls in a clean HTTP API so no other service
needs to know about FreeSWITCH binaries or the ESL protocol.

Endpoints:
  GET  /health
  GET  /ready
  GET  /uuid/{uuid}/exists             → {"exists": true}
  POST /uuid/{uuid}/broadcast          body: WAV bytes (audio/wav)
                                       → {"status": "ok", "duration": 3.2}
  POST /uuid/{uuid}/command            body: {"command": "..."}
                                       → {"output": "..."}

Environment variables:
  FS_CLI         /usr/local/freeswitch/bin/fs_cli
  FS_HOST        127.0.0.1
  FS_PORT        8021
  FS_PASSWORD    ClueCon
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
import subprocess
import tempfile
import wave
from http.server import BaseHTTPRequestHandler, HTTPServer

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

FS_CLI      = os.getenv("FS_CLI",      "/usr/local/freeswitch/bin/fs_cli")
FS_HOST     = os.getenv("FS_HOST",     "127.0.0.1")
FS_PORT     = os.getenv("FS_PORT",     "8021")
FS_PASSWORD = os.getenv("FS_PASSWORD", "ClueCon")
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
# FreeSWITCH helpers
# ---------------------------------------------------------------------------

def _fs_cmd(command: str, timeout: int = 5) -> str:
    try:
        result = subprocess.check_output(
            [FS_CLI,
             "-H", FS_HOST,
             "-P", FS_PORT,
             "-p", FS_PASSWORD,
             "-x", command],
            text=True,
            timeout=timeout,
            stderr=subprocess.STDOUT,
        ).strip()
        return result
    except subprocess.TimeoutExpired:
        log.warning("fs_cli timeout: %s", command)
    except subprocess.CalledProcessError as e:
        log.warning("fs_cli error: %s → %s", command, e.output)
    except Exception as e:
        log.warning("fs_cli exception: %s", e)
    return ""


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

                # Write WAV to temp file (fs_cli path must be filesystem-accessible)
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
