root@openclaw:/opt/ai-stream-agent# cat agent.py 
import asyncio
import datetime
import json
import os
import re
import subprocess
import time
import wave
from urllib.parse import urlparse, parse_qs

import numpy as np
import webrtcvad
import websockets
from faster_whisper import WhisperModel


CAPTURE_RATE = 48000
SAMPLE_RATE = CAPTURE_RATE
WHISPER_RATE = 16000

FRAME_MS = 20
FRAME_SIZE = int(SAMPLE_RATE * FRAME_MS / 1000) * 2

SILENCE_MS = 900
MIN_SPEECH_SECONDS = 0.8
MAX_SPEECH_SECONDS = 8
RMS_THRESHOLD = 0.010

RECORDING_DIR = "/opt/receptify-ai/recordings"

WS_HOST = "0.0.0.0"
WS_PORT = 9090

OLLAMA = "/usr/local/bin/ollama"
MODEL_NAME = "llama3.2:1b"

PIPER = "/opt/receptify-ai/venv/bin/piper"
PIPER_MODEL = "/opt/receptify-ai/piper/en_US-lessac-medium.onnx"
FS_CLI = "/usr/local/freeswitch/bin/fs_cli"

FAQ_FILE = "/opt/receptify-ai/context/ai-ivr-context.txt"

MAX_REPLY_CHARS = 180
OLLAMA_TIMEOUT = 20
PIPER_TIMEOUT = 10
MUTE_BUFFER_SECONDS = 0.5  # extra silence after TTS before listening again

os.environ["HOME"] = "/root"
os.environ["OLLAMA_HOST"] = "127.0.0.1:11434"

os.makedirs(RECORDING_DIR, exist_ok=True)

vad = webrtcvad.Vad(2)
whisper = WhisperModel("base", device="cpu", compute_type="int8")


def load_faq() -> str:
    if os.path.exists(FAQ_FILE):
        with open(FAQ_FILE, "r", encoding="utf-8") as f:
            return f.read()
    return "Working hours are Monday to Friday, 9 AM to 5 PM."


def extract_uuid_from_path(path: str) -> str | None:
    parsed = urlparse(path)
    qs = parse_qs(parsed.query)

    for key in ("uuid", "call_uuid", "channel_uuid"):
        if key in qs and qs[key]:
            return qs[key][0]

    parts = [p for p in parsed.path.split("/") if p]
    if len(parts) >= 2 and parts[0] == "ws":
        return parts[1]

    return None


def is_noise_text(text: str) -> bool:
    clean = text.replace(".", "").replace(",", "").replace(" ", "").strip().lower()

    if not clean or len(clean) < 3:
        return True

    bad = {
        "uh",
        "um",
        "hmm",
        "bam",
        "thankyou",
        "thanks",
        "okay",
        "ok",
        "hellohello",
    }

    if clean in bad:
        return True

    if re.fullmatch(r"[0-9\-\s]+", text.strip()):
        return True

    return False


def normalize_reply(reply: str) -> str:
    reply = re.sub(r"\x1b\[[0-?]*[ -/]*[@-~]", "", reply)
    reply = re.sub(r"[\x00-\x1f\x7f-\x9f]", "", reply)
    reply = re.sub(r"[⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏]", "", reply)

    reply = reply.replace("\n", " ").replace("\r", " ").strip()
    reply = re.sub(r"\s+", " ", reply)

    if not reply:
        return "Sorry, I do not have that information."

    if len(reply) > MAX_REPLY_CHARS:
        reply = reply[:MAX_REPLY_CHARS].rsplit(" ", 1)[0].strip()

    return reply


def save_wav(audio_bytes: bytes, filename: str, rate: int = SAMPLE_RATE) -> str:
    filepath = os.path.join(RECORDING_DIR, filename)

    with wave.open(filepath, "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(rate)
        wav_file.writeframes(audio_bytes)

    print(f"Saved WAV: {filepath}")
    return filepath


def get_wav_duration(filepath: str) -> float:
    try:
        with wave.open(filepath, "r") as f:
            return f.getnframes() / float(f.getframerate())
    except Exception:
        return 3.0


def pcm48k_to_float16k(audio_bytes: bytes) -> np.ndarray:
    audio_np = np.frombuffer(audio_bytes, dtype="<i2").astype(np.float32) / 32768.0

    if len(audio_np) == 0:
        return audio_np

    old_len = len(audio_np)
    new_len = int(old_len * WHISPER_RATE / CAPTURE_RATE)

    return np.interp(
        np.linspace(0, old_len - 1, new_len),
        np.arange(old_len),
        audio_np,
    ).astype(np.float32)


def run_cmd(cmd: list[str], input_text: str | None = None, timeout: int = 20) -> str:
    try:
        return subprocess.check_output(
            cmd,
            input=input_text,
            text=True,
            stderr=subprocess.STDOUT,
            timeout=timeout,
        ).strip()
    except subprocess.TimeoutExpired:
        print("Command timeout:", " ".join(cmd))
    except subprocess.CalledProcessError as e:
        print("Command failed:", " ".join(cmd))
        print(e.output)
    except Exception as e:
        print("Command error:", e)

    return ""


def uuid_exists(call_uuid: str) -> bool:
    try:
        result = subprocess.check_output(
            [FS_CLI, "-x", f"uuid_exists {call_uuid}"],
            text=True,
            timeout=3,
        ).strip()
        return result == "true"
    except Exception as e:
        print("uuid_exists error:", e)
        return False


def build_reply(text: str) -> str:
    lower = text.lower()

    if "working hour" in lower or "business hour" in lower or "hours" in lower:
        return "Our working hours are Monday through Friday, 9 AM to 5 PM."

    if "contact" in lower or "reach you" in lower or "phone number" in lower or "email" in lower:
        return "You can contact us by phone during business hours or send us an email anytime."

    faq = load_faq()

    prompt = f"""
You are a short phone assistant.

Use this FAQ/context when possible:
{faq}

Rules:
- Answer in one short sentence.
- Maximum 20 words.
- If the answer is not in the FAQ/context, say: Sorry, I do not have that information.

Caller said:
{text}
"""

    reply = run_cmd(
        [OLLAMA, "run", MODEL_NAME, "--nowordwrap", prompt],
        timeout=OLLAMA_TIMEOUT,
    )

    return normalize_reply(reply or "Sorry, I do not have that information.")


def synthesize_tts(reply: str, ts: str) -> str | None:
    raw_wav = f"/tmp/tts-{ts}.wav"
    out_wav = f"/tmp/tts-{ts}-8k.wav"

    reply = normalize_reply(reply)

    try:
        subprocess.run(
            [PIPER, "--model", PIPER_MODEL, "--output_file", raw_wav],
            input=reply,
            text=True,
            timeout=PIPER_TIMEOUT,
            check=False,
        )
    except subprocess.TimeoutExpired:
        print("Piper timeout. Killing stuck Piper processes.")
        subprocess.run(["pkill", "-9", "-f", "piper"], check=False)
        return None
    except Exception as e:
        print("Piper error:", e)
        return None

    if not os.path.exists(raw_wav) or os.path.getsize(raw_wav) == 0:
        print("Piper did not generate audio.")
        return None

    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-i",
            raw_wav,
            "-ar",
            "8000",
            "-ac",
            "1",
            "-sample_fmt",
            "s16",
            out_wav,
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )

    if not os.path.exists(out_wav) or os.path.getsize(out_wav) == 0:
        print("ffmpeg did not generate output TTS WAV.")
        return None

    return out_wav


async def process_audio(audio_bytes: bytes, call_uuid: str | None) -> float:
    duration = len(audio_bytes) / SAMPLE_RATE / 2
    print(f"Processing speech: {len(audio_bytes)} bytes, {duration:.2f}s")

    ts = datetime.datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    save_wav(audio_bytes, f"input-{ts}.wav", rate=SAMPLE_RATE)

    audio_np = np.frombuffer(audio_bytes, dtype="<i2").astype(np.float32) / 32768.0
    rms = float(np.sqrt(np.mean(audio_np ** 2))) if len(audio_np) else 0.0
    print(f"Captured RMS: {rms:.4f}")

    if rms < 0.003:
        print("Ignoring very low-level audio.")
        return 0.0

    audio_16k = pcm48k_to_float16k(audio_bytes)

    segments, _ = whisper.transcribe(
        audio_16k,
        language="en",
        beam_size=1,
        vad_filter=False,
        condition_on_previous_text=False,
    )

    text = " ".join(s.text.strip() for s in segments).strip()

    if is_noise_text(text):
        print("Ignoring noise/silence transcription:", repr(text))
        return 0.0

    print("Caller said:", text)

    reply = normalize_reply(build_reply(text))
    print("AI reply:", repr(reply))

    out_wav = synthesize_tts(reply, ts)

    if not out_wav:
        print("No TTS audio generated.")
        return 0.0

    if not call_uuid:
        print("No call UUID found. Cannot play response into call.")
        return 0.0

    if not uuid_exists(call_uuid):
        print(f"Call UUID no longer exists: {call_uuid}")
        return 0.0

    tts_duration = get_wav_duration(out_wav)
    print(f"TTS duration: {tts_duration:.2f}s")

    cmd = f"uuid_broadcast {call_uuid} {out_wav} aleg"
    print("Playing response:", cmd)
    subprocess.run([FS_CLI, "-x", cmd], check=False)

    return tts_duration


async def handler(websocket):
    path = getattr(websocket, "request", None)
    if path and hasattr(path, "path"):
        ws_path = path.path
    else:
        ws_path = getattr(websocket, "path", "/ws")

    conn_ts = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    print(f"Client connected [{conn_ts}] path={ws_path}")

    call_uuid = extract_uuid_from_path(ws_path)

    if call_uuid:
        print("Call UUID from path:", call_uuid)

    audio_buffer = bytearray()
    pre_speech_buffer = bytearray()
    raw_all_frames = bytearray()

    speech_detected = False
    silence_count = 0
    frame_count = 0
    processing = False
    muted_until = 0.0  # monotonic timestamp: ignore input until TTS finishes

    min_audio_bytes = int(SAMPLE_RATE * 2 * MIN_SPEECH_SECONDS)
    max_audio_bytes = int(SAMPLE_RATE * 2 * MAX_SPEECH_SECONDS)
    silence_frames = SILENCE_MS // FRAME_MS
    pre_speech_bytes = int(SAMPLE_RATE * 2 * 0.4)

    try:
        async for message in websocket:
            if isinstance(message, str):
                print("Metadata:", message)

                try:
                    meta = json.loads(message)
                    call_uuid = (
                        meta.get("uuid")
                        or meta.get("call_uuid")
                        or meta.get("channel_uuid")
                        or call_uuid
                    )
                    print("Call UUID:", call_uuid)
                except Exception:
                    pass

                continue

            if not message:
                continue

            if frame_count == 0:
                print(
                    f"First binary chunk: {len(message)} bytes, "
                    f"first 16 bytes: {message[:16].hex()}"
                )
                print("Expected 20ms mono 48k PCM = 1920 bytes")

            raw_all_frames.extend(message)

            for i in range(0, len(message) - FRAME_SIZE + 1, FRAME_SIZE):
                frame = message[i:i + FRAME_SIZE]
                frame_count += 1

                frame_np = np.frombuffer(frame, dtype="<i2").astype(np.float32) / 32768.0
                frame_rms = float(np.sqrt(np.mean(frame_np ** 2)))

                try:
                    vad_speech = vad.is_speech(frame, SAMPLE_RATE)
                except Exception:
                    vad_speech = False

                is_active = (vad_speech and frame_rms > 0.004) or frame_rms > RMS_THRESHOLD

                # Suppress input during TTS playback to prevent echo detection
                if time.monotonic() < muted_until:
                    is_active = False

                if frame_count % 100 == 0:
                    print(
                        f"[frame {frame_count}] rms={frame_rms:.4f} "
                        f"vad={vad_speech} active={is_active} "
                        f"buffer={len(audio_buffer)}"
                    )

                pre_speech_buffer.extend(frame)
                if len(pre_speech_buffer) > pre_speech_bytes:
                    pre_speech_buffer = pre_speech_buffer[-pre_speech_bytes:]

                if is_active:
                    if not speech_detected:
                        audio_buffer = bytearray(pre_speech_buffer)
                        speech_detected = True
                        print("Speech started")

                    audio_buffer.extend(frame)
                    silence_count = 0
                else:
                    if speech_detected:
                        audio_buffer.extend(frame)
                        silence_count += 1

                should_process = (
                    speech_detected
                    and not processing
                    and len(audio_buffer) >= min_audio_bytes
                    and (
                        silence_count >= silence_frames
                        or len(audio_buffer) >= max_audio_bytes
                    )
                )

                if should_process:
                    print(f"Speech ended. buffer={len(audio_buffer)} bytes")

                    captured = bytes(audio_buffer)

                    audio_buffer = bytearray()
                    pre_speech_buffer = bytearray()
                    silence_count = 0
                    speech_detected = False
                    processing = True

                    try:
                        tts_dur = await process_audio(captured, call_uuid)
                        if tts_dur > 0:
                            muted_until = time.monotonic() + tts_dur + MUTE_BUFFER_SECONDS
                            print(f"Muting input for {tts_dur + MUTE_BUFFER_SECONDS:.2f}s")
                    finally:
                        processing = False

    except websockets.exceptions.ConnectionClosed:
        print("WebSocket closed by FreeSWITCH.")
    except Exception as e:
        print("Connection handler error:", e)
    finally:
        if raw_all_frames:
            save_wav(bytes(raw_all_frames), f"raw-session-{conn_ts}.wav", rate=SAMPLE_RATE)

        print(f"Client disconnected. Total frames: {frame_count}")


async def process_request(connection, request):
    print(f"WebSocket upgrade from {connection.remote_address}")
    print(f"  Path: {request.path}")

    for header, value in request.headers.items():
        print(f"  {header}: {value}")

    return None


async def main():
    print(f"Starting AI stream agent on ws://{WS_HOST}:{WS_PORT}/ws")
    print(f"Binding to {WS_HOST}:{WS_PORT}")

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
        print(f"WebSocket server listening on port {WS_PORT}")
        await asyncio.Future()


if __name__ == "__main__":
    asyncio.run(main())
