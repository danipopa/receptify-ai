"""
agent — WebSocket audio ingest, VAD, orchestration.

Receives 48kHz mono PCM from FreeSWITCH uuid_audio_stream,
delegates STT / RAG / TTS to downstream microservices,
plays the reply back via fs-bridge.

Environment variables (all optional, sensible defaults shown):
  WS_HOST            0.0.0.0
  WS_PORT            9090
  HTTP_PORT          9095       health/ready/metrics sidecar
  STT_URL            http://stt-service:9092
  RAG_URL            http://rag-service:9091
  TTS_URL            http://tts-service:9093
  FS_BRIDGE_URL      http://fs-bridge:9094
  RECORDING_DIR      /tmp/recordings
  RECORDING_ENABLED  false
  MUTE_BUFFER_SEC    0.5
  WELCOME_MESSAGE    Thank you for calling. How can I help you today?
  SILENCE_MS         900
  MIN_SPEECH_SEC     0.8
  MAX_SPEECH_SEC     8.0
  RMS_THRESHOLD      0.010
  LOG_LEVEL          INFO
"""

import asyncio
import datetime
import json
import logging
import os
import struct
import time
import wave
from urllib.parse import parse_qs, urlparse

import aiohttp
import numpy as np
import webrtcvad
import websockets

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

WS_HOST     = os.getenv("WS_HOST",        "0.0.0.0")
WS_PORT     = int(os.getenv("WS_PORT",    "9090"))
HTTP_PORT   = int(os.getenv("HTTP_PORT",  "9095"))

STT_URL       = os.getenv("STT_URL",       "http://stt-service:9092")
RAG_URL       = os.getenv("RAG_URL",       "http://rag-service:9091")
TTS_URL       = os.getenv("TTS_URL",       "http://tts-service:9093")
FS_BRIDGE_URL = os.getenv("FS_BRIDGE_URL", "http://fs-bridge:9094")

RECORDING_DIR     = os.getenv("RECORDING_DIR",     "/tmp/recordings")
RECORDING_ENABLED = os.getenv("RECORDING_ENABLED", "false").lower() == "true"
MUTE_BUFFER_SEC   = float(os.getenv("MUTE_BUFFER_SEC", "0.5"))

WELCOME_MESSAGE   = os.getenv(
    "WELCOME_MESSAGE",
    "Thank you for calling. How can I help you today?",
)

CAPTURE_RATE      = 48000
SAMPLE_RATE       = CAPTURE_RATE
FRAME_MS          = 20
FRAME_SIZE        = int(SAMPLE_RATE * FRAME_MS / 1000) * 2   # bytes

SILENCE_MS        = int(os.getenv("SILENCE_MS",    "900"))
MIN_SPEECH_SEC    = float(os.getenv("MIN_SPEECH_SEC", "0.8"))
MAX_SPEECH_SEC    = float(os.getenv("MAX_SPEECH_SEC", "8.0"))
RMS_THRESHOLD     = float(os.getenv("RMS_THRESHOLD",  "0.010"))

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()

# ---------------------------------------------------------------------------
# Logging — structured JSON
# ---------------------------------------------------------------------------

class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        doc = {
            "ts":      datetime.datetime.utcnow().isoformat() + "Z",
            "level":   record.levelname,
            "msg":     record.getMessage(),
            "service": "agent",
        }
        for k in ("call_uuid", "frame", "rms", "dur"):
            if hasattr(record, k):
                doc[k] = getattr(record, k)
        if record.exc_info:
            doc["exc"] = self.formatException(record.exc_info)
        return json.dumps(doc)

handler = logging.StreamHandler()
handler.setFormatter(JsonFormatter())
logging.root.setLevel(LOG_LEVEL)
logging.root.handlers = [handler]
log = logging.getLogger("agent")

# ---------------------------------------------------------------------------
# Setup
# ---------------------------------------------------------------------------

os.makedirs(RECORDING_DIR, exist_ok=True)
vad = webrtcvad.Vad(2)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def extract_uuid(path: str) -> str | None:
    parsed = urlparse(path)
    for key in ("uuid", "call_uuid", "channel_uuid"):
        val = parse_qs(parsed.query).get(key)
        if val:
            return val[0]
    parts = [p for p in parsed.path.split("/") if p]
    if len(parts) >= 2 and parts[0] == "ws":
        return parts[1]
    return None


def save_wav(audio_bytes: bytes, name: str) -> str:
    path = os.path.join(RECORDING_DIR, name)
    with wave.open(path, "wb") as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(SAMPLE_RATE)
        f.writeframes(audio_bytes)
    return path


def rms(audio_bytes: bytes) -> float:
    arr = np.frombuffer(audio_bytes, dtype="<i2").astype(np.float32) / 32768.0
    return float(np.sqrt(np.mean(arr ** 2))) if len(arr) else 0.0

# ---------------------------------------------------------------------------
# Downstream service clients
# ---------------------------------------------------------------------------

async def stt_transcribe(session: aiohttp.ClientSession, pcm: bytes) -> str:
    try:
        form = aiohttp.FormData()
        form.add_field("audio", pcm, content_type="application/octet-stream",
                       filename="audio.pcm")
        form.add_field("sample_rate", str(SAMPLE_RATE))
        async with session.post(f"{STT_URL}/transcribe", data=form, timeout=aiohttp.ClientTimeout(total=15)) as r:
            data = await r.json()
            return data.get("text", "")
    except Exception as e:
        log.warning("STT service error: %s", e)
        return ""


async def rag_query(session: aiohttp.ClientSession, text: str) -> str:
    try:
        async with session.post(
            f"{RAG_URL}/query",
            json={"text": text, "top_k": 3},
            timeout=aiohttp.ClientTimeout(total=5),
        ) as r:
            data = await r.json()
            return data.get("context", "")
    except Exception as e:
        log.warning("RAG service error: %s", e)
        return ""


async def tts_synthesize(session: aiohttp.ClientSession, text: str) -> bytes | None:
    try:
        async with session.post(
            f"{TTS_URL}/synthesize",
            json={"text": text, "sample_rate": 8000},
            timeout=aiohttp.ClientTimeout(total=12),
        ) as r:
            if r.status == 200:
                return await r.read()
    except Exception as e:
        log.warning("TTS service error: %s", e)
    return None


async def fs_broadcast(session: aiohttp.ClientSession, call_uuid: str, wav_bytes: bytes) -> float:
    """Send WAV to fs-bridge; returns audio duration in seconds."""
    try:
        async with session.post(
            f"{FS_BRIDGE_URL}/uuid/{call_uuid}/broadcast",
            data=wav_bytes,
            headers={"Content-Type": "audio/wav"},
            timeout=aiohttp.ClientTimeout(total=10),
        ) as r:
            data = await r.json()
            return float(data.get("duration", 3.0))
    except Exception as e:
        log.warning("fs-bridge error: %s", e)
    return 0.0


async def fs_uuid_exists(session: aiohttp.ClientSession, call_uuid: str) -> bool:
    try:
        async with session.get(
            f"{FS_BRIDGE_URL}/uuid/{call_uuid}/exists",
            timeout=aiohttp.ClientTimeout(total=3),
        ) as r:
            data = await r.json()
            return bool(data.get("exists", False))
    except Exception as e:
        log.warning("fs-bridge exists error: %s", e)
    return False

# ---------------------------------------------------------------------------
# Core pipeline
# ---------------------------------------------------------------------------

async def process_audio(
    session: aiohttp.ClientSession,
    pcm: bytes,
    call_uuid: str | None,
) -> float:
    audio_rms = rms(pcm)
    dur = len(pcm) / SAMPLE_RATE / 2
    log.info("Processing speech", extra={"call_uuid": call_uuid, "dur": round(dur, 2), "rms": round(audio_rms, 4)})

    if audio_rms < 0.003:
        log.info("Skipping: very low RMS", extra={"call_uuid": call_uuid})
        return 0.0

    if RECORDING_ENABLED:
        ts = datetime.datetime.utcnow().strftime("%Y%m%d-%H%M%S-%f")
        save_wav(pcm, f"input-{ts}.wav")

    text = await stt_transcribe(session, pcm)
    if not text:
        log.info("STT returned empty text", extra={"call_uuid": call_uuid})
        return 0.0

    log.info("Caller said: %s", text, extra={"call_uuid": call_uuid})

    context = await rag_query(session, text)

    # Build prompt
    prompt_context = context or "No specific context available."
    prompt = (
        "You are a telephone receptionist. Answer the caller using ONLY the information in the context below.\n"
        "Context:\n"
        f"{prompt_context}\n\n"
        "Instructions:\n"
        "- Give a direct, short answer in one sentence (max 20 words).\n"
        "- Use only facts from the context above.\n"
        "- If the answer is clearly present in the context, state it.\n"
        "- Only say 'Sorry, I do not have that information' if the topic is truly absent from the context.\n"
        f"Caller: {text}\n"
        "Answer:"
    )

    # Ask LLM via RAG service /generate endpoint (ollama passthrough)
    reply = await llm_generate(session, prompt)
    if not reply:
        reply = "Sorry, I do not have that information."

    log.info("AI reply: %s", reply, extra={"call_uuid": call_uuid})

    wav_bytes = await tts_synthesize(session, reply)
    if not wav_bytes:
        log.warning("TTS produced no audio", extra={"call_uuid": call_uuid})
        return 0.0

    if not call_uuid:
        return 0.0

    if not await fs_uuid_exists(session, call_uuid):
        log.info("Call UUID gone: %s", call_uuid, extra={"call_uuid": call_uuid})
        return 0.0

    tts_dur = await fs_broadcast(session, call_uuid, wav_bytes)
    log.info("Broadcast done, duration=%.2fs", tts_dur, extra={"call_uuid": call_uuid})
    return tts_dur


async def llm_generate(session: aiohttp.ClientSession, prompt: str) -> str:
    """Calls RAG service /generate which proxies Ollama."""
    try:
        async with session.post(
            f"{RAG_URL}/generate",
            json={"prompt": prompt},
            timeout=aiohttp.ClientTimeout(total=25),
        ) as r:
            data = await r.json()
            return data.get("reply", "")
    except Exception as e:
        log.warning("LLM generate error: %s", e)
    return ""

# ---------------------------------------------------------------------------
# WebSocket handler
# ---------------------------------------------------------------------------

async def handler(websocket):
    path = getattr(getattr(websocket, "request", None), "path", None) \
           or getattr(websocket, "path", "/ws")
    conn_ts = datetime.datetime.utcnow().strftime("%Y%m%d-%H%M%S")
    call_uuid = extract_uuid(path)

    log.info("Client connected path=%s uuid=%s", path, call_uuid)

    audio_buffer    = bytearray()
    pre_speech_buf  = bytearray()
    raw_all_frames  = bytearray()

    speech_detected = False
    silence_count   = 0
    frame_count     = 0
    processing      = False
    muted_until     = 0.0

    min_bytes     = int(SAMPLE_RATE * 2 * MIN_SPEECH_SEC)
    max_bytes     = int(SAMPLE_RATE * 2 * MAX_SPEECH_SEC)
    silence_limit = SILENCE_MS // FRAME_MS
    pre_bytes     = int(SAMPLE_RATE * 2 * 0.4)

    async with aiohttp.ClientSession() as session:
        # Play welcome message on call connect
        if call_uuid and WELCOME_MESSAGE:
            await asyncio.sleep(0.8)   # let FreeSWITCH finish call setup
            log.info("Sending welcome message", extra={"call_uuid": call_uuid})
            wav = await tts_synthesize(session, WELCOME_MESSAGE)
            if wav:
                tts_dur = await fs_broadcast(session, call_uuid, wav)
                muted_until = time.monotonic() + tts_dur + MUTE_BUFFER_SEC
            else:
                log.warning("Welcome TTS failed", extra={"call_uuid": call_uuid})

        try:
            async for message in websocket:
                if isinstance(message, str):
                    try:
                        meta = json.loads(message)
                        call_uuid = (
                            meta.get("uuid")
                            or meta.get("call_uuid")
                            or meta.get("channel_uuid")
                            or call_uuid
                        )
                    except Exception:
                        pass
                    continue

                if not message:
                    continue

                raw_all_frames.extend(message)

                for i in range(0, len(message) - FRAME_SIZE + 1, FRAME_SIZE):
                    frame = message[i : i + FRAME_SIZE]
                    frame_count += 1

                    arr = np.frombuffer(frame, dtype="<i2").astype(np.float32) / 32768.0
                    frame_rms = float(np.sqrt(np.mean(arr ** 2)))

                    try:
                        vad_speech = vad.is_speech(frame, SAMPLE_RATE)
                    except Exception:
                        vad_speech = False

                    is_active = (vad_speech and frame_rms > 0.004) or frame_rms > RMS_THRESHOLD

                    if time.monotonic() < muted_until:
                        is_active = False

                    if frame_count % 200 == 0:
                        log.debug("frame=%d rms=%.4f vad=%s active=%s buf=%d",
                                  frame_count, frame_rms, vad_speech, is_active, len(audio_buffer),
                                  extra={"call_uuid": call_uuid, "frame": frame_count})

                    pre_speech_buf.extend(frame)
                    if len(pre_speech_buf) > pre_bytes:
                        pre_speech_buf = pre_speech_buf[-pre_bytes:]

                    if is_active:
                        if not speech_detected:
                            audio_buffer = bytearray(pre_speech_buf)
                            speech_detected = True
                            log.info("Speech started", extra={"call_uuid": call_uuid})
                        audio_buffer.extend(frame)
                        silence_count = 0
                    else:
                        if speech_detected:
                            audio_buffer.extend(frame)
                            silence_count += 1

                    should_process = (
                        speech_detected
                        and not processing
                        and len(audio_buffer) >= min_bytes
                        and (silence_count >= silence_limit or len(audio_buffer) >= max_bytes)
                    )

                    if should_process:
                        captured = bytes(audio_buffer)
                        audio_buffer    = bytearray()
                        pre_speech_buf  = bytearray()
                        silence_count   = 0
                        speech_detected = False
                        processing      = True
                        log.info("Speech ended, captured=%d bytes", len(captured),
                                 extra={"call_uuid": call_uuid})

                        try:
                            tts_dur = await process_audio(session, captured, call_uuid)
                            if tts_dur > 0:
                                muted_until = time.monotonic() + tts_dur + MUTE_BUFFER_SEC
                        finally:
                            processing = False

        except websockets.exceptions.ConnectionClosed:
            log.info("WebSocket closed by FreeSWITCH", extra={"call_uuid": call_uuid})
        except Exception as e:
            log.exception("Handler error: %s", e, extra={"call_uuid": call_uuid})
        finally:
            if RECORDING_ENABLED and raw_all_frames:
                save_wav(bytes(raw_all_frames), f"raw-{conn_ts}.wav")
            log.info("Client disconnected, frames=%d", frame_count, extra={"call_uuid": call_uuid})

# ---------------------------------------------------------------------------
# HTTP health sidecar
# ---------------------------------------------------------------------------

async def http_health_server():
    from aiohttp import web

    async def health(_):
        return web.json_response({"status": "ok", "service": "agent"})

    async def ready(_):
        return web.json_response({"status": "ready"})

    app = web.Application()
    app.router.add_get("/health", health)
    app.router.add_get("/ready",  ready)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", HTTP_PORT)
    await site.start()
    log.info("Health server on :%d", HTTP_PORT)

# ---------------------------------------------------------------------------
# WebSocket upgrade logger
# ---------------------------------------------------------------------------

async def process_request(connection, request):
    log.info("WS upgrade from=%s path=%s",
             connection.remote_address, request.path)
    return None

# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

async def main():
    loop = asyncio.get_running_loop()

    # Graceful shutdown on SIGTERM
    import signal
    stop = loop.create_future()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, lambda: stop.set_result(None))

    await http_health_server()

    log.info("Starting WS server ws://%s:%d", WS_HOST, WS_PORT)
    async with websockets.serve(
        handler,
        WS_HOST,
        WS_PORT,
        max_size=None,
        ping_interval=None,
        ping_timeout=None,
        close_timeout=5,
        reuse_port=True,
        process_request=process_request,
    ):
        log.info("Agent ready on ws://%s:%d", WS_HOST, WS_PORT)
        await stop

    log.info("Agent shut down cleanly")


if __name__ == "__main__":
    asyncio.run(main())
