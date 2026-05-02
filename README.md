# Receptify AI — Cloud Native

A cloud-native AI phone receptionist built on FreeSWITCH, Whisper, Piper TTS, Ollama, and RAG.

## Architecture

```
FreeSWITCH (uuid_audio_stream)
       │  WebSocket PCM 48kHz
       ▼
┌─────────────┐   HTTP    ┌─────────────┐
│   agent     │──────────►│ stt-service │  Whisper transcription
│  :9090 (WS) │◄──────────│   :9092     │
│  :9095 (HTTP│           └─────────────┘
│  /health    │   HTTP    ┌─────────────┐
│  /ready)    │──────────►│ rag-service │  Ollama embeddings + LLM
└─────────────┘◄──────────│   :9091     │
       │                  └─────────────┘
       │           HTTP   ┌─────────────┐
       └─────────────────►│ tts-service │  Piper TTS
       │◄─────────────────│   :9093     │
       │                  └─────────────┘
       │           HTTP   ┌─────────────┐
       └─────────────────►│  fs-bridge  │  fs_cli wrapper
                          │   :9094     │
                          └─────────────┘
```

## Services

| Service | Port | Description |
|---|---|---|
| agent | 9090 (WS), 9095 (HTTP) | WebSocket ingest, VAD, orchestration |
| stt-service | 9092 | Whisper speech-to-text |
| rag-service | 9091 | RAG retrieval + Ollama LLM |
| tts-service | 9093 | Piper text-to-speech |
| fs-bridge | 9094 | FreeSWITCH fs_cli HTTP wrapper |

## Project Layout

```
latest/
├── agent/            # WebSocket agent
│   ├── main.py
│   ├── Dockerfile
│   └── requirements.txt
├── stt-service/      # Whisper HTTP API
├── tts-service/      # Piper HTTP API
├── rag-service/      # RAG + Ollama passthrough
├── fs-bridge/        # FreeSWITCH bridge
├── k8s/              # Kubernetes manifests
│   ├── agent.yaml
│   ├── stt-service.yaml
│   ├── tts-service.yaml
│   ├── rag-service.yaml
│   └── fs-bridge.yaml
├── volumes/          # Local dev mounts (git-ignored)
│   ├── faq/          # ai-ivr-context.txt
│   └── piper/        # piper binary + .onnx model
└── docker-compose.yml
```

## Quick Start (Docker Compose)

### 1. Prerequisites

```bash
# Ollama running on host
ollama serve
ollama pull llama3.2:1b
ollama pull nomic-embed-text
```

### 2. Prepare volumes

```bash
mkdir -p volumes/faq volumes/piper

# Place your FAQ content
cp /opt/ai-ivr-context.txt volumes/faq/

# Copy Piper binary and model
cp /opt/ai-ivr-venv/bin/piper volumes/piper/
cp /opt/piper/en_US-lessac-medium.onnx volumes/piper/
```

### 3. Start

```bash
cd latest/
docker compose up --build
```

### 4. Verify all services

```bash
curl http://localhost:9091/health   # rag-service
curl http://localhost:9092/health   # stt-service
curl http://localhost:9093/health   # tts-service
curl http://localhost:9094/health   # fs-bridge
curl http://localhost:9095/health   # agent
```

### 5. Test RAG

```bash
curl -X POST http://localhost:9091/query \
  -H "Content-Type: application/json" \
  -d '{"text": "what are your hours?"}'
```

### 6. Hot-reload FAQ

```bash
# Edit volumes/faq/ai-ivr-context.txt then:
curl -X POST http://localhost:9091/rebuild
```

## Kubernetes Deployment

```bash
# Create namespace
kubectl create namespace receptify-ai
kubectl config set-context --current --namespace=receptify-ai

# FAQ content
kubectl create configmap faq-context \
  --from-file=ai-ivr-context.txt=/opt/ai-ivr-context.txt

# FreeSWITCH ESL password
kubectl create secret generic freeswitch-secret \
  --from-literal=esl-password=YOUR_ESL_PASSWORD

# Apply all manifests
kubectl apply -f k8s/

# Watch rollout
kubectl rollout status deployment/rag-service
kubectl rollout status deployment/stt-service
kubectl rollout status deployment/tts-service
kubectl rollout status deployment/agent
```

### FreeSWITCH dialplan

Point `uuid_audio_stream` at the agent NodePort:

```xml
<action application="uuid_audio_stream"
        data="${uuid} start ws://NODE_IP:30090/ws/${uuid} mono 48000 read"/>
```

## Environment Variables

All services are fully configured via environment variables. See each service's
`Dockerfile` for the complete list with defaults.

### Key agent variables

| Variable | Default | Description |
|---|---|---|
| `STT_URL` | `http://stt-service:9092` | STT service URL |
| `RAG_URL` | `http://rag-service:9091` | RAG service URL |
| `TTS_URL` | `http://tts-service:9093` | TTS service URL |
| `FS_BRIDGE_URL` | `http://fs-bridge:9094` | fs-bridge URL |
| `RECORDING_ENABLED` | `false` | Save input WAV files |
| `MUTE_BUFFER_SEC` | `0.5` | Silence after TTS before listening |
| `RMS_THRESHOLD` | `0.010` | Minimum energy to trigger VAD |
