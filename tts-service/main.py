"""
tts-service — Piper TTS HTTP API.

POST /synthesize   JSON: {"text": "...", "sample_rate": 8000}
                   returns: audio/wav bytes
GET  /health
GET  /ready

Environment variables:
  PIPER_BIN          /opt/ai-ivr-venv/bin/piper
  PIPER_MODEL        /opt/piper/en_US-lessac-medium.onnx
  OUTPUT_SAMPLE_RATE 8000
  PIPER_TIMEOUT      10
  HOST               0.0.0.0
  PORT               9093
  LOG_LEVEL          INFO
"""

import asyncio
import datetime
import io
import json
import logging
import os
import re
import subprocess
import tempfile
import wave
from concurrent.futures import ThreadPoolExecutor

from aiohttp import web

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

PIPER_BIN          = os.getenv("PIPER_BIN",    "/opt/ai-ivr-venv/bin/piper")
PIPER_MODEL        = os.getenv("PIPER_MODEL",  "/opt/piper/en_US-lessac-medium.onnx")
OUTPUT_SAMPLE_RATE = int(os.getenv("OUTPUT_SAMPLE_RATE", "8000"))
PIPER_TIMEOUT      = int(os.getenv("PIPER_TIMEOUT", "10"))
HOST               = os.getenv("HOST", "0.0.0.0")
PORT               = int(os.getenv("PORT", "9093"))
LOG_LEVEL          = os.getenv("LOG_LEVEL", "INFO").upper()

MAX_TEXT_CHARS = 300

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

class JsonFormatter(logging.Formatter):
    def format(self, record):
        return json.dumps({
            "ts":      datetime.datetime.utcnow().isoformat() + "Z",
            "level":   record.levelname,
            "msg":     record.getMessage(),
            "service": "tts",
        })

_h = logging.StreamHandler()
_h.setFormatter(JsonFormatter())
logging.root.setLevel(LOG_LEVEL)
logging.root.handlers = [_h]
log = logging.getLogger("tts")

executor = ThreadPoolExecutor(max_workers=2)

# ---------------------------------------------------------------------------
# TTS helpers
# ---------------------------------------------------------------------------

ANSI_RE   = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")
CTRL_RE   = re.compile(r"[\x00-\x1f\x7f-\x9f]")
SPIN_RE   = re.compile(r"[⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏]")

def clean_text(text: str) -> str:
    text = ANSI_RE.sub("", text)
    text = CTRL_RE.sub("", text)
    text = SPIN_RE.sub("", text)
    text = text.replace("\n", " ").replace("\r", " ").strip()
    text = re.sub(r"\s+", " ", text)
    if len(text) > MAX_TEXT_CHARS:
        text = text[:MAX_TEXT_CHARS].rsplit(" ", 1)[0].strip()
    return text


def _synthesize(text: str, out_rate: int) -> bytes:
    with tempfile.TemporaryDirectory() as tmp:
        raw_wav = os.path.join(tmp, "raw.wav")
        out_wav = os.path.join(tmp, "out.wav")

        try:
            subprocess.run(
                [PIPER_BIN, "--model", PIPER_MODEL, "--output_file", raw_wav],
                input=text,
                text=True,
                timeout=PIPER_TIMEOUT,
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except subprocess.TimeoutExpired:
            subprocess.run(["pkill", "-9", "-f", "piper"], check=False)
            raise RuntimeError("Piper timeout")
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Piper failed: {e}")

        if not os.path.exists(raw_wav) or os.path.getsize(raw_wav) == 0:
            raise RuntimeError("Piper produced no output")

        subprocess.run(
            ["ffmpeg", "-y", "-i", raw_wav,
             "-ar", str(out_rate), "-ac", "1", "-sample_fmt", "s16", out_wav],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True,
            timeout=15,
        )

        if not os.path.exists(out_wav) or os.path.getsize(out_wav) == 0:
            raise RuntimeError("ffmpeg produced no output")

        with open(out_wav, "rb") as f:
            return f.read()

# ---------------------------------------------------------------------------
# HTTP handlers
# ---------------------------------------------------------------------------

async def synthesize(request: web.Request) -> web.Response:
    try:
        body = await request.json()
        text     = clean_text(str(body.get("text", "")))
        out_rate = int(body.get("sample_rate", OUTPUT_SAMPLE_RATE))

        if not text:
            return web.json_response({"error": "text is required"}, status=400)

        log.info("Synthesizing: %r @ %dHz", text, out_rate)

        loop = asyncio.get_event_loop()
        wav_bytes = await loop.run_in_executor(executor, _synthesize, text, out_rate)

        return web.Response(body=wav_bytes, content_type="audio/wav")

    except Exception as e:
        log.exception("Synthesize error: %s", e)
        return web.json_response({"error": str(e)}, status=500)


async def health(_):
    return web.json_response({"status": "ok", "service": "tts"})


async def ready(_):
    return web.json_response({"status": "ready"})

# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

def make_app() -> web.Application:
    app = web.Application()
    app.router.add_post("/synthesize", synthesize)
    app.router.add_get("/health", health)
    app.router.add_get("/ready",  ready)
    return app


if __name__ == "__main__":
    log.info("Starting TTS service on %s:%d", HOST, PORT)
    web.run_app(make_app(), host=HOST, port=PORT, access_log=None)
