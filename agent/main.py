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
  AUDIO_PLAYBACK_MODE fs_bridge   fs_bridge|mod_audio_stream
  MOD_AUDIO_STREAM_PROBE_TEXT     optional text played once over websocket on connect
  RECORDING_DIR      /tmp/recordings
  RECORDING_ENABLED  false
  WELCOME_MESSAGE    Thank you for calling. How can I help you today?
  BARGE_IN_MS        400
  TTS_CHUNK_CHARS    120
  SILENCE_MS         600
  MIN_SPEECH_SEC     0.35
  MAX_SPEECH_SEC     8.0
  RMS_THRESHOLD      0.010
  LOG_LEVEL          INFO
"""

import asyncio
import base64
import datetime
import io
import json
import logging
import os
import re
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
FS_BRIDGE_URL  = os.getenv("FS_BRIDGE_URL",  "http://fs-bridge:9094")
API_URL        = os.getenv("API_URL",        "http://receptify-api")
INTERNAL_TOKEN = os.getenv("INTERNAL_TOKEN", "").strip()
AUDIO_PLAYBACK_MODE = os.getenv("AUDIO_PLAYBACK_MODE", "fs_bridge").strip().lower()
MOD_AUDIO_STREAM_PROBE_TEXT = os.getenv("MOD_AUDIO_STREAM_PROBE_TEXT", "").strip()
MOD_AUDIO_STREAM_PROBE_DELAY = float(os.getenv("MOD_AUDIO_STREAM_PROBE_DELAY", "1.2"))

RECORDING_DIR     = os.getenv("RECORDING_DIR",     "/tmp/recordings")
RECORDING_ENABLED = os.getenv("RECORDING_ENABLED", "false").lower() == "true"
BARGE_IN_ENABLED  = os.getenv("BARGE_IN_ENABLED", "true").lower() == "true"
BARGE_IN_MS       = int(os.getenv("BARGE_IN_MS", "400"))
BARGE_IN_RMS_THRESHOLD = float(os.getenv("BARGE_IN_RMS_THRESHOLD", "0.006"))
TTS_CHUNK_CHARS   = int(os.getenv("TTS_CHUNK_CHARS", "120"))
WELCOME_LEAD_IN_MS = 150

WELCOME_MESSAGE   = os.getenv(
    "WELCOME_MESSAGE",
    "Thank you for calling. How can I help you today?",
)

CAPTURE_RATE      = 8000
SAMPLE_RATE       = CAPTURE_RATE
FRAME_MS          = 20
FRAME_SIZE        = int(SAMPLE_RATE * FRAME_MS / 1000) * 2   # bytes  (320 bytes @ 8kHz)

SILENCE_MS        = int(os.getenv("SILENCE_MS",    "600"))
MIN_SPEECH_SEC    = float(os.getenv("MIN_SPEECH_SEC", "0.35"))
MAX_SPEECH_SEC    = float(os.getenv("MAX_SPEECH_SEC", "8.0"))
RMS_THRESHOLD     = float(os.getenv("RMS_THRESHOLD",  "0.010"))

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()

# ---------------------------------------------------------------------------
# Logging — structured JSON
# ---------------------------------------------------------------------------

class JsonFormatter(logging.Formatter):
    _SKIP = frozenset({
        "name", "msg", "args", "created", "filename", "funcName", "levelname",
        "levelno", "lineno", "module", "msecs", "pathname", "process",
        "processName", "relativeCreated", "stack_info", "thread", "threadName",
        "exc_info", "exc_text", "message", "taskName",
    })

    def format(self, record: logging.LogRecord) -> str:
        doc = {
            "ts":      datetime.datetime.utcnow().isoformat() + "Z",
            "level":   record.levelname,
            "msg":     record.getMessage(),
            "service": "agent",
        }
        for k, v in record.__dict__.items():
            if k not in self._SKIP and not k.startswith("_"):
                doc[k] = v
        if record.exc_info:
            doc["exc"] = self.formatException(record.exc_info)
        return json.dumps(doc, default=str)

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
barge_in_vad = webrtcvad.Vad(2)

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


def extract_did(path: str) -> str | None:
    parsed = urlparse(path)
    val = parse_qs(parsed.query).get("did")
    return val[0] if val else None


def speech_frame_is_active(
    frame: bytes,
    frame_rms: float,
    response_active: bool,
    vad_speech: bool,
) -> bool:
    if response_active:
        if not BARGE_IN_ENABLED:
            return False
        try:
            return (
                barge_in_vad.is_speech(frame, SAMPLE_RATE)
                and frame_rms > BARGE_IN_RMS_THRESHOLD
            )
        except Exception:
            return False
    return (vad_speech and frame_rms > 0.004) or frame_rms > RMS_THRESHOLD


async def fetch_did_config(session: aiohttp.ClientSession, did: str) -> dict:
    """Fetch per-DID tenant config from the internal API endpoint."""
    try:
        headers = {"X-Internal-Token": INTERNAL_TOKEN} if INTERNAL_TOKEN else {}
        async with session.get(
            f"{API_URL}/internal/dids/{did}/config",
            headers=headers,
            timeout=aiohttp.ClientTimeout(total=3),
        ) as r:
            if r.status == 200:
                return await r.json()
            log.warning("fetch_did_config status=%d did=%s", r.status, did)
    except Exception as e:
        log.warning("fetch_did_config error: %s", e)
    return {}


def save_wav(audio_bytes: bytes, name: str) -> str:
    path = os.path.join(RECORDING_DIR, name)
    with wave.open(path, "wb") as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(SAMPLE_RATE)
        f.writeframes(audio_bytes)
    return path


def wav_duration(wav_bytes: bytes) -> float:
    try:
        with wave.open(io.BytesIO(wav_bytes), "rb") as f:
            return f.getnframes() / float(f.getframerate())
    except Exception:
        return 3.0


def prepend_wav_silence(wav_bytes: bytes, duration_ms: int) -> bytes:
    with wave.open(io.BytesIO(wav_bytes), "rb") as source:
        params = source.getparams()
        frames = source.readframes(params.nframes)

    silence_frames = params.framerate * duration_ms // 1000
    silence = b"\0" * silence_frames * params.nchannels * params.sampwidth
    output = io.BytesIO()
    with wave.open(output, "wb") as destination:
        destination.setnchannels(params.nchannels)
        destination.setsampwidth(params.sampwidth)
        destination.setframerate(params.framerate)
        destination.setcomptype(params.comptype, params.compname)
        destination.writeframes(silence + frames)
    return output.getvalue()


def rms(audio_bytes: bytes) -> float:
    arr = np.frombuffer(audio_bytes, dtype="<i2").astype(np.float32) / 32768.0
    return float(np.sqrt(np.mean(arr ** 2))) if len(arr) else 0.0

# ---------------------------------------------------------------------------
# Downstream service clients
# ---------------------------------------------------------------------------

async def stt_transcribe(session: aiohttp.ClientSession, pcm: bytes) -> tuple[str, int]:
    try:
        form = aiohttp.FormData()
        form.add_field("audio", pcm, content_type="application/octet-stream",
                       filename="audio.pcm")
        form.add_field("sample_rate", str(SAMPLE_RATE))
        async with session.post(f"{STT_URL}/transcribe", data=form, timeout=aiohttp.ClientTimeout(total=15)) as r:
            data = await r.json()
            return data.get("text", ""), int(data.get("inference_ms", 0))
    except Exception as e:
        log.warning("STT service error: %s", e)
        return "", 0


async def rag_query(
    session: aiohttp.ClientSession,
    text: str,
    tenant_id: int | None = None,
    workspace_id: int | None = None,
    top_k: int = 3,
) -> tuple[str, int]:
    try:
        payload: dict = {"text": text, "top_k": top_k}
        if tenant_id:
            payload["tenant_id"] = tenant_id
        if workspace_id:
            payload["workspace_id"] = workspace_id
        async with session.post(
            f"{RAG_URL}/query",
            json=payload,
            timeout=aiohttp.ClientTimeout(total=12),
        ) as r:
            data = await r.json()
            return data.get("context", ""), int(data.get("duration_ms", 0))
    except Exception as e:
        log.warning("RAG service error: %s", repr(e))
        return "", 0


async def tts_synthesize(session: aiohttp.ClientSession, text: str) -> tuple[bytes | None, int]:
    try:
        async with session.post(
            f"{TTS_URL}/synthesize",
            json={"text": text, "sample_rate": 8000},
            timeout=aiohttp.ClientTimeout(total=12),
        ) as r:
            if r.status == 200:
                synthesis_ms = int(r.headers.get("X-Synthesis-Ms", 0))
                return await r.read(), synthesis_ms
            body = await r.text()
            log.warning("TTS service status=%d body=%s", r.status, body[:500])
    except Exception as e:
        log.warning("TTS service error: %s", e)
    return None, 0


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


async def fs_stop_playback(session: aiohttp.ClientSession, call_uuid: str | None) -> None:
    if not call_uuid:
        return
    try:
        async with session.post(
            f"{FS_BRIDGE_URL}/uuid/{call_uuid}/stop",
            timeout=aiohttp.ClientTimeout(total=3),
        ) as r:
            if r.status not in (200, 404):
                body = await r.text()
                log.warning("fs-bridge stop status=%d body=%s", r.status, body[:500])
    except Exception as e:
        log.warning("fs-bridge stop error: %s", e)


async def mod_audio_stream_playback(websocket, wav_bytes: bytes) -> float:
    """Ask mod_audio_stream to play audio sent back over the same websocket."""
    payload = {
        "type": "streamAudio",
        "data": {
            "audioDataType": "wav",
            "sampleRate": SAMPLE_RATE,
            "audioData": base64.b64encode(wav_bytes).decode("ascii"),
        },
    }
    await websocket.send(json.dumps(payload))
    return wav_duration(wav_bytes)


async def mod_audio_stream_stop(websocket) -> None:
    for payload in ({"type": "stopAudio"}, {"event": "stopAudio"}):
        try:
            await websocket.send(json.dumps(payload))
        except Exception:
            return


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

class CallState:
    def __init__(self) -> None:
        self.generation = 0
        self.response_task: asyncio.Task | None = None
        self.playback_active = False
        self.playback_task: asyncio.Task | None = None
        # Conversation history: list of {"role": "user"|"assistant", "content": str}
        self.history: list[dict] = []
        # Tracks the current turn so interrupt_response can save partial context
        self.pending_user_text: str = ""
        self.pending_reply: str = ""
        self.appointment_flow: dict | None = None

    def next_generation(self) -> int:
        self.generation += 1
        return self.generation

    def is_current(self, generation: int) -> bool:
        return generation == self.generation


def build_prompt(text: str, context: str, history: list[dict] | None = None) -> str:
    prompt_context = context or "No specific context available."
    history_section = ""
    if history:
        lines = []
        for turn in history[-6:]:  # keep last 3 exchanges
            role = "Caller" if turn["role"] == "user" else "Receptionist"
            lines.append(f"{role}: {turn['content']}")
        history_section = "Conversation so far:\n" + "\n".join(lines) + "\n\n"
    return (
        "You are a telephone receptionist. Answer the caller using ONLY the information in the context below.\n"
        "Context:\n"
        f"{prompt_context}\n\n"
        + history_section
        + "Instructions:\n"
        "- Give a direct, short answer in one sentence (max 20 words).\n"
        "- Use only facts from the context above.\n"
        "- If the answer is clearly present in the context, state it.\n"
        "- Only say 'Sorry, I do not have that information' if the topic is truly absent from the context.\n"
        f"Caller: {text}\n"
        "Answer:"
    )


async def internal_api_request(
    session: aiohttp.ClientSession,
    method: str,
    path: str,
    payload: dict | None = None,
) -> dict:
    headers = {"X-Internal-Token": INTERNAL_TOKEN} if INTERNAL_TOKEN else {}
    async with session.request(
        method,
        f"{API_URL}{path}",
        json=payload,
        headers=headers,
        timeout=aiohttp.ClientTimeout(total=6),
    ) as response:
        try:
            data = await response.json()
        except (aiohttp.ContentTypeError, json.JSONDecodeError) as exc:
            body = await response.text()
            raise RuntimeError(f"Internal API returned invalid JSON (HTTP {response.status}): {body[:200]}") from exc
        if response.status < 200 or response.status >= 300:
            raise RuntimeError(data.get("error", f"Internal API request failed (HTTP {response.status})"))
        return data


def parse_preferred_date(text: str, timezone_name: str) -> datetime.date | None:
    from zoneinfo import ZoneInfo

    today = datetime.datetime.now(ZoneInfo(timezone_name)).date()
    normalized = text.lower().strip()
    if re.search(r"\btoday\b", normalized):
        return today
    if re.search(r"\btomorrow\b", normalized):
        return today + datetime.timedelta(days=1)

    iso_date = re.search(r"\b\d{4}-\d{2}-\d{2}\b", normalized)
    if iso_date:
        try:
            return datetime.date.fromisoformat(iso_date.group())
        except ValueError:
            return None

    weekdays = {
        "monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3,
        "friday": 4, "saturday": 5, "sunday": 6,
    }
    for name, weekday in weekdays.items():
        if re.search(rf"\b{name}\b", normalized):
            delta = (weekday - today.weekday()) % 7 or 7
            return today + datetime.timedelta(days=delta)
    return None


def format_slot_choices(slots: list[dict]) -> str:
    return " ".join(
        f"{index}. {slot['local_time']}."
        for index, slot in enumerate(slots, start=1)
    )


def choice_index(text: str, maximum: int) -> int | None:
    choices = {
        1: ("first", "one"),
        2: ("second", "two"),
        3: ("third", "three"),
        4: ("fourth", "four"),
        5: ("fifth", "five"),
        6: ("sixth", "six"),
        7: ("seventh", "seven"),
        8: ("eighth", "eight"),
        9: ("ninth", "nine"),
        10: ("tenth", "ten"),
    }
    match = re.search(r"\b([1-9]\d?)\b", text)
    if match:
        selected = int(match.group(1))
        return selected if selected <= maximum else None
    for index, words in choices.items():
        if index <= maximum and any(re.search(rf"\b{word}\b", text, re.IGNORECASE) for word in words):
            return index
    return None


async def handle_appointment_turn(
    session: aiohttp.ClientSession,
    state: CallState,
    text: str,
    workspace_id: int | None,
    call_uuid: str | None,
) -> str | None:
    if state.appointment_flow is None:
        if not re.search(r"\b(appointment|book(?:ing)?|schedule|consultation)\b", text, re.IGNORECASE):
            return None
        if not workspace_id:
            return "This phone number is not linked to a client workspace, so I cannot book an appointment."
        try:
            config = await internal_api_request(
                session, "GET", f"/internal/client_workspaces/{workspace_id}/appointment_types"
            )
        except (aiohttp.ClientError, asyncio.TimeoutError, RuntimeError) as exc:
            log.warning("Appointment type lookup failed: %s", exc, extra={"call_uuid": call_uuid})
            return "I cannot access the booking calendar right now. No appointment has been made. Please try again later."

        appointment_types = config.get("appointment_types", [])
        if not appointment_types:
            return "There are no appointment types configured for this client yet, so I cannot book a time."
        state.appointment_flow = {
            "stage": "type" if len(appointment_types) > 1 else "name",
            "types": appointment_types,
            "type": appointment_types[0] if len(appointment_types) == 1 else None,
            "timezone": config.get("timezone", "UTC"),
        }
        if len(appointment_types) > 1:
            choices = " ".join(
                f"{index}. {item['name']}."
                for index, item in enumerate(appointment_types, start=1)
            )
            return f"What type of appointment would you like? {choices}"
        return f"I can arrange a {appointment_types[0]['name']}. May I have your name?"

    flow = state.appointment_flow
    if re.fullmatch(r"\s*(cancel|cancel booking|stop booking)\s*[.!]?\s*", text, re.IGNORECASE):
        state.appointment_flow = None
        return "I have not booked an appointment."

    stage = flow["stage"]

    if stage == "type":
        selected = None
        index = choice_index(text, len(flow["types"]))
        if index is not None:
            selected = flow["types"][index - 1]
        if selected is None:
            selected = next(
                (item for item in flow["types"] if item["name"].lower() in text.lower()),
                None,
            )
        if selected is None:
            return "Please say the number or name of the appointment type you want."
        flow["type"] = selected
        flow["stage"] = "name"
        return f"May I have your name for the {selected['name']}?"

    if stage == "name":
        name = text.strip()
        if len(name) < 2 or len(name) > 100:
            return "Please tell me your name so I can add it to the booking."
        flow["caller_name"] = name
        flow["stage"] = "phone"
        return "What callback phone number should I put on the booking? Please include the country code."

    if stage == "phone":
        digits = re.sub(r"\D", "", text)
        if not 7 <= len(digits) <= 15:
            return "I did not get a valid callback number. Please say it again, including the country code."
        flow["callback_number"] = ("+" if text.strip().startswith("+") else "") + digits
        flow["stage"] = "reason"
        return "Would you like to briefly say what the appointment is about? This is optional; say skip to continue."

    if stage == "reason":
        if not re.search(
            r"\b(skip|none|no reason|no thanks|rather not|prefer not|don't want|do not want)\b",
            text,
            re.IGNORECASE,
        ):
            purpose = text.strip()
            if len(purpose) > 500:
                return "Please keep the reason brief, or say skip to continue without one."
            flow["purpose"] = purpose
        flow["stage"] = "date"
        return "What date would you prefer? You can say a weekday, today, tomorrow, or a date like 2026-10-25."

    if stage == "date":
        preferred_date = parse_preferred_date(text, flow["timezone"])
        if preferred_date is None:
            return "I could not identify that date. Please say a weekday, today, tomorrow, or a date like 2026-10-25."
        try:
            result = await internal_api_request(
                session,
                "POST",
                f"/internal/client_workspaces/{workspace_id}/availability",
                {
                    "appointment_type_id": flow["type"]["id"],
                    "from": preferred_date.isoformat(),
                    "to": (preferred_date + datetime.timedelta(days=6)).isoformat(),
                    "limit": 3,
                },
            )
        except (aiohttp.ClientError, asyncio.TimeoutError, RuntimeError) as exc:
            log.warning("Appointment availability lookup failed: %s", exc, extra={"call_uuid": call_uuid})
            return "I cannot check the booking calendar right now. No appointment has been made. Please try again later."
        slots = result.get("slots", [])
        if not slots:
            return "I could not find an opening in the following week. Please suggest another date."
        flow["slots"] = slots
        flow["stage"] = "slot"
        return f"I have these available times: {format_slot_choices(slots)} Which number would you prefer?"

    if stage == "slot":
        index = choice_index(text, len(flow["slots"]))
        if index is None:
            return "Please choose one of the offered times by saying its number."
        selected = flow["slots"][index - 1]
        flow["selected_slot"] = selected
        flow["stage"] = "confirm"
        return (
            f"To confirm, I will book a {flow['type']['name']} for {flow['caller_name']} "
            f"at {selected['local_time']}, with callback number {flow['callback_number']}. "
            "Should I book it? Please say yes or no."
        )

    if stage == "confirm":
        if re.fullmatch(
            r"\s*(yes|yeah|yep|confirm(?:ed)?|correct|book it|that's right|that is right)"
            r"(?:[\s,.!]+please)?[\s.!]*",
            text,
            re.IGNORECASE,
        ):
            try:
                result = await internal_api_request(
                    session,
                    "POST",
                    f"/internal/client_workspaces/{workspace_id}/appointments",
                    {
                        "appointment_type_id": flow["type"]["id"],
                        "caller_name": flow["caller_name"],
                        "callback_number": flow["callback_number"],
                        "purpose": flow.get("purpose"),
                        "starts_at": flow["selected_slot"]["starts_at"],
                        "confirmed": True,
                    },
                )
            except RuntimeError as exc:
                if "no longer available" in str(exc).lower():
                    flow["stage"] = "date"
                    flow.pop("slots", None)
                    flow.pop("selected_slot", None)
                    return "That time was just taken. Please suggest another date and I will check again."
                log.warning("Appointment booking failed: %s", exc, extra={"call_uuid": call_uuid})
                state.appointment_flow = None
                return "I could not complete the booking. No appointment has been made. Please try again later."
            except (aiohttp.ClientError, asyncio.TimeoutError) as exc:
                log.warning("Appointment booking request failed: %s", exc, extra={"call_uuid": call_uuid})
                state.appointment_flow = None
                return "I could not complete the booking. No appointment has been made. Please try again later."
            state.appointment_flow = None
            appointment = result.get("appointment", {})
            return f"Your appointment is booked for {flow['selected_slot']['local_time']}. Your booking reference is {appointment.get('id')}."
        if re.search(r"^\s*(no|cancel|not now|do not|don't)\b", text, re.IGNORECASE):
            state.appointment_flow = None
            return "I have not booked anything. You can ask me to book an appointment whenever you are ready."
        return "Please say yes to book this appointment, or no to leave it unbooked."

    state.appointment_flow = None
    return "I could not continue that booking. No appointment has been made."


def sentence_chunks(buffer: str, force: bool = False) -> tuple[list[str], str]:
    chunks: list[str] = []
    start = 0
    for i, ch in enumerate(buffer):
        if ch in ".!?" and (i + 1 == len(buffer) or buffer[i + 1].isspace()):
            part = buffer[start : i + 1].strip()
            if part:
                chunks.append(part)
            start = i + 1

    remainder = buffer[start:].strip()
    if force and remainder:
        chunks.append(remainder)
        remainder = ""
    elif len(remainder) >= TTS_CHUNK_CHARS:
        split_at = remainder.rfind(" ", 0, TTS_CHUNK_CHARS)
        if split_at < 40:
            split_at = TTS_CHUNK_CHARS
        chunks.append(remainder[:split_at].strip())
        remainder = remainder[split_at:].strip()

    return chunks, remainder


async def llm_generate_stream(session: aiohttp.ClientSession, prompt: str):
    try:
        async with session.post(
            f"{RAG_URL}/generate_stream",
            json={"prompt": prompt},
            timeout=aiohttp.ClientTimeout(total=60, sock_read=15),
        ) as r:
            if r.status != 200:
                body = await r.text()
                log.warning("LLM stream status=%d body=%s", r.status, body[:500])
                return
            async for raw in r.content:
                for line in raw.splitlines():
                    if not line.strip():
                        continue
                    try:
                        item = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    if item.get("error"):
                        log.warning("LLM stream error: %s", item["error"])
                        return
                    token = item.get("token")
                    if token:
                        yield token
                    if item.get("done"):
                        return
    except asyncio.CancelledError:
        raise
    except Exception as e:
        log.warning("LLM stream error: %s", e)


async def play_wav(
    session: aiohttp.ClientSession,
    websocket,
    wav_bytes: bytes,
    call_uuid: str | None,
    state: CallState,
    generation: int,
) -> float:
    if not state.is_current(generation):
        return 0.0

    if AUDIO_PLAYBACK_MODE == "mod_audio_stream":
        dur = await mod_audio_stream_playback(websocket, wav_bytes)
    else:
        if not call_uuid or not await fs_uuid_exists(session, call_uuid):
            return 0.0
        dur = await fs_broadcast(session, call_uuid, wav_bytes)

    if not state.is_current(generation):
        return 0.0
    state.playback_active = True
    try:
        await asyncio.sleep(dur)
    finally:
        if state.is_current(generation):
            state.playback_active = False
    return dur


async def speak_text(
    session: aiohttp.ClientSession,
    websocket,
    text: str,
    call_uuid: str | None,
    state: CallState,
    generation: int,
    leading_silence_ms: int = 0,
) -> float:
    if not state.is_current(generation) or not text.strip():
        return 0.0
    wav_bytes, synthesis_ms = await tts_synthesize(session, text)
    if not wav_bytes:
        log.warning("TTS produced no audio", extra={"call_uuid": call_uuid})
        return 0.0
    if leading_silence_ms:
        wav_bytes = prepend_wav_silence(wav_bytes, leading_silence_ms)
    log.info(
        "TTS audio ready synthesis_ms=%d duration_ms=%d lead_in_ms=%d",
        synthesis_ms,
        round(wav_duration(wav_bytes) * 1000),
        leading_silence_ms,
        extra={"call_uuid": call_uuid},
    )
    state.playback_task = asyncio.create_task(
        play_wav(session, websocket, wav_bytes, call_uuid, state, generation)
    )
    try:
        return await state.playback_task
    finally:
        if state.playback_task and state.playback_task.done():
            state.playback_task = None


async def speak_queue_worker(
    session: aiohttp.ClientSession,
    websocket,
    queue: asyncio.Queue,
    call_uuid: str | None,
    state: CallState,
    generation: int,
) -> float:
    total = 0.0
    while state.is_current(generation):
        chunk = await queue.get()
        try:
            if chunk is None:
                return total
            total += await speak_text(session, websocket, str(chunk), call_uuid, state, generation)
        finally:
            queue.task_done()
    return total


async def interrupt_response(
    session: aiohttp.ClientSession,
    websocket,
    call_uuid: str | None,
    state: CallState,
) -> None:
    # Save partial turn to history before cancelling so next query has context
    if state.pending_user_text:
        state.history.append({"role": "user", "content": state.pending_user_text})
    if state.pending_reply:
        state.history.append({"role": "assistant", "content": state.pending_reply})
    state.pending_user_text = ""
    state.pending_reply = ""

    state.next_generation()
    tasks = [t for t in (state.response_task, state.playback_task) if t and not t.done()]
    for task in tasks:
        task.cancel()
    if AUDIO_PLAYBACK_MODE == "mod_audio_stream":
        await mod_audio_stream_stop(websocket)
    else:
        await fs_stop_playback(session, call_uuid)
    if tasks:
        await asyncio.gather(*tasks, return_exceptions=True)
    state.playback_active = False
    state.response_task = None
    state.playback_task = None


def start_response_task(state: CallState, coro, call_uuid: str | None) -> None:
    task = asyncio.create_task(coro)

    def _log_done(done: asyncio.Task) -> None:
        if done.cancelled():
            return
        exc = done.exception()
        if exc:
            log.warning(
                "Response task failed: %s",
                exc,
                extra={"call_uuid": call_uuid},
                exc_info=(type(exc), exc, exc.__traceback__),
            )

    task.add_done_callback(_log_done)
    state.response_task = task


async def process_audio(
    session: aiohttp.ClientSession,
    websocket,
    pcm: bytes,
    call_uuid: str | None,
    state: CallState,
    generation: int,
    call_config: dict | None = None,
) -> float:
    cfg = call_config or {}
    tenant_id = cfg.get("tenant_id")
    workspace_id = cfg.get("workspace_id")
    top_k     = int(cfg.get("rag_top_k") or 3)

    audio_rms = rms(pcm)
    dur = len(pcm) / SAMPLE_RATE / 2
    log.info("Processing speech", extra={"call_uuid": call_uuid, "dur": round(dur, 2), "rms": round(audio_rms, 4)})

    if audio_rms < 0.003:
        log.info("Skipping: very low RMS", extra={"call_uuid": call_uuid})
        return 0.0

    if RECORDING_ENABLED:
        ts = datetime.datetime.utcnow().strftime("%Y%m%d-%H%M%S-%f")
        save_wav(pcm, f"input-{ts}.wav")

    step_start = time.monotonic()
    text, stt_inference_ms = await stt_transcribe(session, pcm)
    if not state.is_current(generation):
        return 0.0
    stt_ms = round((time.monotonic() - step_start) * 1000)
    log.info(
        "Pipeline stage complete",
        extra={"call_uuid": call_uuid, "stage": "stt", "elapsed_ms": stt_ms, "inference_ms": stt_inference_ms},
    )
    if not text:
        log.info("STT returned empty text", extra={"call_uuid": call_uuid})
        return 0.0

    log.info("Caller said: %s", text, extra={"call_uuid": call_uuid})
    state.pending_user_text = text
    state.pending_reply = ""

    appointment_reply = await handle_appointment_turn(
        session, state, text, workspace_id, call_uuid
    )
    if appointment_reply is not None:
        if not state.is_current(generation):
            return 0.0
        state.pending_reply = appointment_reply
        spoken_dur = await speak_text(
            session, websocket, appointment_reply, call_uuid, state, generation
        )
        state.history.append({"role": "user", "content": text})
        state.history.append({"role": "assistant", "content": appointment_reply})
        if len(state.history) > 12:
            state.history = state.history[-12:]
        state.pending_user_text = ""
        state.pending_reply = ""
        return spoken_dur

    # If there's recent history, enrich the RAG query with the last user turn so
    # short follow-ups like "on Monday" retrieve the right context.
    rag_text = text
    if state.history:
        last_user = next((h["content"] for h in reversed(state.history) if h["role"] == "user"), None)
        if last_user and len(text.split()) <= 6:
            rag_text = f"{last_user} {text}"
            log.info("RAG enriched query: %s", rag_text, extra={"call_uuid": call_uuid})

    step_start = time.monotonic()
    context, rag_server_ms = await rag_query(
        session,
        rag_text,
        tenant_id=tenant_id,
        workspace_id=workspace_id,
        top_k=top_k,
    )
    if not state.is_current(generation):
        return 0.0
    rag_ms = round((time.monotonic() - step_start) * 1000)
    log.info(
        "Pipeline stage complete",
        extra={"call_uuid": call_uuid, "stage": "rag_query", "elapsed_ms": rag_ms, "server_ms": rag_server_ms},
    )

    prompt = build_prompt(text, context, history=state.history or None)

    # Ask LLM via streaming RAG service endpoint and feed sentence chunks to TTS.
    step_start = time.monotonic()
    reply_parts: list[str] = []
    pending = ""
    spoken_dur = 0.0
    speech_queue: asyncio.Queue = asyncio.Queue(maxsize=8)
    speaker = asyncio.create_task(
        speak_queue_worker(session, websocket, speech_queue, call_uuid, state, generation)
    )
    try:
        async for token in llm_generate_stream(session, prompt):
            if not state.is_current(generation):
                return 0.0
            reply_parts.append(token)
            pending += token
            state.pending_reply = re.sub(r"\s+", " ", "".join(reply_parts)).strip()
            chunks, pending = sentence_chunks(pending)
            for chunk in chunks:
                await speech_queue.put(chunk)

        chunks, pending = sentence_chunks(pending, force=True)
        for chunk in chunks:
            await speech_queue.put(chunk)
        await speech_queue.put(None)
        spoken_dur = await speaker
    except asyncio.CancelledError:
        speaker.cancel()
        await asyncio.gather(speaker, return_exceptions=True)
        raise
    finally:
        if not speaker.done():
            speaker.cancel()
            await asyncio.gather(speaker, return_exceptions=True)

    reply = re.sub(r"\s+", " ", "".join(reply_parts)).strip()
    llm_tts_ms = round((time.monotonic() - step_start) * 1000)
    log.info(
        "Pipeline stage complete",
        extra={"call_uuid": call_uuid, "stage": "llm_stream_tts", "elapsed_ms": llm_tts_ms},
    )
    if not reply:
        reply = "Sorry, I do not have that information."
        spoken_dur += await speak_text(session, websocket, reply, call_uuid, state, generation)

    # Save completed turn to history and clear pending state
    state.history.append({"role": "user",      "content": text})
    state.history.append({"role": "assistant", "content": reply})
    if len(state.history) > 12:   # cap at 6 exchanges
        state.history = state.history[-12:]
    state.pending_user_text = ""
    state.pending_reply = ""

    log.info("AI reply: %s", reply, extra={"call_uuid": call_uuid})
    log.info(
        "call_trace",
        extra={
            "call_uuid":        call_uuid,
            "stt_ms":           stt_ms,
            "stt_inference_ms": stt_inference_ms,
            "rag_ms":           rag_ms,
            "rag_server_ms":    rag_server_ms,
            "llm_tts_ms":       llm_tts_ms,
            "total_ms":         stt_ms + rag_ms + llm_tts_ms,
        },
    )
    return spoken_dur


async def llm_generate(session: aiohttp.ClientSession, prompt: str) -> str:
    """Calls RAG service /generate which proxies Ollama."""
    try:
        async with session.post(
            f"{RAG_URL}/generate",
            json={"prompt": prompt},
            timeout=aiohttp.ClientTimeout(total=60),
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
    did       = extract_did(path)

    log.info("WS connected path=%s uuid=%s did=%s",
             path, call_uuid, did)

    audio_buffer    = bytearray()
    pre_speech_buf  = bytearray()
    raw_all_frames  = bytearray()

    speech_detected = False
    silence_count   = 0
    active_count    = 0
    frame_count     = 0
    state           = CallState()

    min_bytes     = int(SAMPLE_RATE * 2 * MIN_SPEECH_SEC)
    max_bytes     = int(SAMPLE_RATE * 2 * MAX_SPEECH_SEC)
    silence_limit = SILENCE_MS // FRAME_MS
    pre_bytes     = int(SAMPLE_RATE * 2 * 0.4)
    barge_frames  = max(1, BARGE_IN_MS // FRAME_MS)

    async with aiohttp.ClientSession() as session:
        # Fetch per-DID tenant config
        call_config: dict = {}
        if did:
            call_config = await fetch_did_config(session, did)
            log.info("DID config did=%s tenant_id=%s", did, call_config.get("tenant_id"),
                     extra={"call_uuid": call_uuid})

        welcome = call_config.get("welcome_message") or WELCOME_MESSAGE

        if MOD_AUDIO_STREAM_PROBE_TEXT:
            await asyncio.sleep(MOD_AUDIO_STREAM_PROBE_DELAY)
            log.info("Sending mod_audio_stream probe", extra={"call_uuid": call_uuid})
            generation = state.next_generation()
            start_response_task(
                state,
                speak_text(session, websocket, MOD_AUDIO_STREAM_PROBE_TEXT, call_uuid, state, generation),
                call_uuid,
            )

        # Play welcome message on call connect
        if call_uuid and welcome and not MOD_AUDIO_STREAM_PROBE_TEXT:
            await asyncio.sleep(0.8)   # let FreeSWITCH finish call setup
            log.info("Sending welcome message", extra={"call_uuid": call_uuid})
            generation = state.next_generation()
            start_response_task(
                state,
                speak_text(
                    session,
                    websocket,
                    welcome,
                    call_uuid,
                    state,
                    generation,
                    leading_silence_ms=WELCOME_LEAD_IN_MS,
                ),
                call_uuid,
            )

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

                    response_active = state.response_task and not state.response_task.done()
                    is_active = speech_frame_is_active(
                        frame, frame_rms, bool(response_active), vad_speech
                    )

                    if frame_count % 200 == 0:
                        log.debug("frame=%d rms=%.4f vad=%s active=%s buf=%d",
                                  frame_count, frame_rms, vad_speech, is_active, len(audio_buffer),
                                  extra={"call_uuid": call_uuid, "frame": frame_count})

                    pre_speech_buf.extend(frame)
                    if len(pre_speech_buf) > pre_bytes:
                        pre_speech_buf = pre_speech_buf[-pre_bytes:]

                    if is_active:
                        active_count += 1
                        if not speech_detected and active_count < barge_frames:
                            continue

                        if not speech_detected:
                            if state.response_task and not state.response_task.done():
                                log.info("Caller barge-in detected; interrupting AI response", extra={"call_uuid": call_uuid})
                                await interrupt_response(session, websocket, call_uuid, state)
                            audio_buffer = bytearray(pre_speech_buf)
                            speech_detected = True
                            log.info("Speech started", extra={"call_uuid": call_uuid})
                        audio_buffer.extend(frame)
                        silence_count = 0
                    else:
                        if not speech_detected:
                            active_count = 0
                        if speech_detected:
                            audio_buffer.extend(frame)
                            silence_count += 1

                    should_process = (
                        speech_detected
                        and len(audio_buffer) >= min_bytes
                        and (silence_count >= silence_limit or len(audio_buffer) >= max_bytes)
                    )

                    if should_process:
                        captured = bytes(audio_buffer)
                        audio_buffer    = bytearray()
                        pre_speech_buf  = bytearray()
                        silence_count   = 0
                        active_count    = 0
                        speech_detected = False
                        log.info("Speech ended, captured=%d bytes", len(captured),
                                 extra={"call_uuid": call_uuid})

                        generation = state.next_generation()
                        start_response_task(
                            state,
                            process_audio(session, websocket, captured, call_uuid, state, generation, call_config),
                            call_uuid,
                        )

        except websockets.exceptions.ConnectionClosed:
            log.info("WebSocket closed by FreeSWITCH", extra={"call_uuid": call_uuid})
        except Exception as e:
            log.exception("Handler error: %s", e, extra={"call_uuid": call_uuid})
        finally:
            await interrupt_response(session, websocket, call_uuid, state)
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
    runner = web.AppRunner(app, access_log=None)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", HTTP_PORT)
    await site.start()
    log.info("Health server on :%d", HTTP_PORT)

# ---------------------------------------------------------------------------
# WebSocket upgrade logger (removed — was incompatible with websockets>=13)
# ---------------------------------------------------------------------------

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
    ):
        log.info("Agent ready on ws://%s:%d", WS_HOST, WS_PORT)
        await stop

    log.info("Agent shut down cleanly")


if __name__ == "__main__":
    asyncio.run(main())
