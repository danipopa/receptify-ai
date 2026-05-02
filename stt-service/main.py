"""
stt-service — Whisper HTTP transcription API.

POST /transcribe   multipart: audio (PCM bytes) + sample_rate (int)
                   returns: {"text": "...", "duration": 1.94, "language": "en"}
GET  /health
GET  /ready

Environment variables:
  WHISPER_MODEL      base
  WHISPER_DEVICE     cpu
  WHISPER_COMPUTE    int8
  WHISPER_LANGUAGE   en
  HOST               0.0.0.0
  PORT               9092
  LOG_LEVEL          INFO
"""

import asyncio
import datetime
import io
import json
import logging
import os
import wave
from concurrent.futures import ThreadPoolExecutor

import numpy as np
from aiohttp import web
from faster_whisper import WhisperModel

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

WHISPER_MODEL_NAME = os.getenv("WHISPER_MODEL",   "base")
WHISPER_DEVICE     = os.getenv("WHISPER_DEVICE",  "cpu")
WHISPER_COMPUTE    = os.getenv("WHISPER_COMPUTE", "int8")
WHISPER_LANGUAGE   = os.getenv("WHISPER_LANGUAGE","en")
HOST               = os.getenv("HOST",            "0.0.0.0")
PORT               = int(os.getenv("PORT",        "9092"))
LOG_LEVEL          = os.getenv("LOG_LEVEL",       "INFO").upper()

WHISPER_RATE = 16000

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

class JsonFormatter(logging.Formatter):
    def format(self, record):
        return json.dumps({
            "ts":      datetime.datetime.utcnow().isoformat() + "Z",
            "level":   record.levelname,
            "msg":     record.getMessage(),
            "service": "stt",
        })

_h = logging.StreamHandler()
_h.setFormatter(JsonFormatter())
logging.root.setLevel(LOG_LEVEL)
logging.root.handlers = [_h]
log = logging.getLogger("stt")

# ---------------------------------------------------------------------------
# Whisper (loaded once at startup)
# ---------------------------------------------------------------------------

log.info("Loading Whisper model=%s device=%s compute=%s",
         WHISPER_MODEL_NAME, WHISPER_DEVICE, WHISPER_COMPUTE)
model = WhisperModel(WHISPER_MODEL_NAME, device=WHISPER_DEVICE, compute_type=WHISPER_COMPUTE)
log.info("Whisper ready")

executor = ThreadPoolExecutor(max_workers=2)

NOISE_WORDS = {
    "uh", "um", "hmm", "bam", "thankyou", "thanks", "okay", "ok", "hellohello",
}

import re

def is_noise(text: str) -> bool:
    clean = re.sub(r"[.,\s]", "", text).strip().lower()
    if not clean or len(clean) < 3:
        return True
    if clean in NOISE_WORDS:
        return True
    if re.fullmatch(r"[0-9\-]+", clean):
        return True
    return False


def _resample(pcm: bytes, src_rate: int) -> np.ndarray:
    arr = np.frombuffer(pcm, dtype="<i2").astype(np.float32) / 32768.0
    if src_rate == WHISPER_RATE or len(arr) == 0:
        return arr
    old_len = len(arr)
    new_len = int(old_len * WHISPER_RATE / src_rate)
    return np.interp(
        np.linspace(0, old_len - 1, new_len),
        np.arange(old_len),
        arr,
    ).astype(np.float32)


def _transcribe(pcm: bytes, sample_rate: int) -> dict:
    audio = _resample(pcm, sample_rate)
    duration = len(pcm) / sample_rate / 2

    segments, info = model.transcribe(
        audio,
        language=WHISPER_LANGUAGE,
        beam_size=1,
        vad_filter=False,
        condition_on_previous_text=False,
    )
    text = " ".join(s.text.strip() for s in segments).strip()

    if is_noise(text):
        text = ""

    return {"text": text, "duration": round(duration, 3), "language": info.language}

# ---------------------------------------------------------------------------
# HTTP handlers
# ---------------------------------------------------------------------------

async def transcribe(request: web.Request) -> web.Response:
    try:
        reader = await request.multipart()

        pcm         = b""
        sample_rate = 48000

        async for part in reader:
            if part.name == "audio":
                pcm = await part.read()
            elif part.name == "sample_rate":
                text = await part.text()
                sample_rate = int(text)

        if not pcm:
            return web.json_response({"error": "audio field required"}, status=400)

        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(executor, _transcribe, pcm, sample_rate)

        log.info("Transcribed: %r (%.2fs)", result["text"], result["duration"])
        return web.json_response(result)

    except Exception as e:
        log.exception("Transcribe error: %s", e)
        return web.json_response({"error": str(e)}, status=500)


async def health(_):
    return web.json_response({"status": "ok", "service": "stt"})


async def ready(_):
    return web.json_response({"status": "ready"})

# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

def make_app() -> web.Application:
    app = web.Application(client_max_size=50 * 1024 * 1024)  # 50 MB
    app.router.add_post("/transcribe", transcribe)
    app.router.add_get("/health", health)
    app.router.add_get("/ready",  ready)
    return app


if __name__ == "__main__":
    log.info("Starting STT service on %s:%d", HOST, PORT)
    web.run_app(make_app(), host=HOST, port=PORT, access_log=None)
