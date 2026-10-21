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

### Tux development cluster

For the development cluster on Tux, use `k8s/development` instead of applying
the production-oriented manifests above. It isolates workloads and data in the
`receptify-dev` namespace, routes RAG traffic internally to
`http://rag-service:9091`, and exposes the frontend and API on NodePorts
`30082` and `30083`. FreeSWITCH and public ingress are intentionally excluded.

The overlay uses development images in Tux's internal registry at
`192.168.100.16:30501` and runtime secrets in `receptify-dev`. After the images
are published to that registry and the secrets are present, apply it with:

```bash
kubectl kustomize --load-restrictor LoadRestrictionsNone k8s/development \
  | ssh -p 22122 root@10.0.0.250 'kubectl apply -f -'
```

Tux forwards frontend port `30082` and API port `30083` from its LAN address
to their NodePorts on the Kubernetes node. From a device on the Tux LAN, open:

```text
http://10.0.0.250:30082
```

The frontend uses the Tux API at `http://10.0.0.250:30083/api/v1`. The Tux
firewall limits both forwarding rules to sources in `10.0.0.0/24`. To measure
RAG generation and TTS latency inside the cluster:

```bash
ssh -p 22122 root@10.0.0.250 \
  'NAMESPACE=receptify-dev bash -s' < scripts/measure-k8s-latency.sh
```

#### Testing voice interruption and turn-end timing

The development agent currently has caller barge-in disabled. To compare
behavior during a call, toggle it without rebuilding the image:

```bash
# Enable interruption for a test; the higher RMS threshold helps reject noise.
ssh -p 22122 root@10.0.0.250 \
  'kubectl -n receptify-dev set env deployment/agent BARGE_IN_ENABLED=true BARGE_IN_RMS_THRESHOLD=0.015 && kubectl -n receptify-dev rollout status deployment/agent'

# Disable it again.
ssh -p 22122 root@10.0.0.250 \
  'kubectl -n receptify-dev set env deployment/agent BARGE_IN_ENABLED=false && kubectl -n receptify-dev rollout status deployment/agent'
```

The manifest keeps barge-in disabled, so applying the development overlay
restores that safe default. `BARGE_IN_MS` controls how long speech must persist
before interrupting playback; `BARGE_IN_RMS_THRESHOLD` controls its minimum
audio level. The development starting threshold is `0.015`.

`SILENCE_MS` is the quiet interval used to decide that the caller's turn ended.
The development value is `450` ms (previously `600` ms); lower values reduce
response delay but can cut off callers who pause mid-sentence. This timer only
helps once audio is classified as quiet, so background noise that remains above
the speech threshold may still delay endpointing.

Platform administrator access is assigned directly in the database; public
registration cannot grant this role. After applying the API migration, promote
an existing account on Tux with:

```bash
ssh -p 22122 root@10.0.0.250 \
  'kubectl -n receptify-dev exec deployment/receptify-api -- bundle exec rails runner '\''Tenant.find_by!(email: "admin@receptify.local").update!(platform_admin: true)'\'''
```

The admin overview reports plans, subscription status, expiry dates, phone
numbers, calls, and appointments. Invoice/payment history is not currently
stored by the application.

### FreeSWITCH dialplan

Point `uuid_audio_stream` at the agent NodePort:

```xml
<action application="uuid_audio_stream"
        data="${uuid} start ws://NODE_IP:30090/ws/${uuid} mono 48000 read"/>
```

### Linphone on the Tux development LAN

The development FreeSWITCH endpoint is available only from the Tux LAN:

| Setting | Value |
|---|---|
| SIP server | `10.0.0.250` |
| SIP transport | UDP |
| SIP port | `5060` |
| SIP username / authentication username | `1000` |
| Password | Read from the `FS_LINPHONE_PASSWORD` key in the `receptify-dev-telephony` Kubernetes Secret |
| Call destination | `+12025550100` (reserved US test number; internal routing only) |
| RTP ports | UDP `20000-20100` |

Retrieve the Linphone password on Tux with:

```bash
ssh -p 22122 root@10.0.0.250 \
  "kubectl -n receptify-dev get secret receptify-dev-telephony -o jsonpath='{.data.FS_LINPHONE_PASSWORD}' | base64 -d; echo"
```

The Tux forwarding rules accept SIP/RTP only from `10.0.0.0/24`. Register with
username `1000`, then call `+12025550100` to reach the Receptify agent. This
reserved test number is routed internally; no outbound PSTN route is configured.

### Client workspaces and appointment booking

Open **Client Workspaces** in the account dashboard. On first use, the page
creates the Mobiletel and inregistrare-marca.com starter workspaces with
editable, unpublished RAG drafts and 30-minute appointment-type placeholders.
Review the draft content before publishing it to the phone agent.

For each workspace, configure its time zone, appointment types, weekly working
hours, and any date-specific closures or blocks. A phone DID can be assigned to
a workspace from **Phone Numbers**. Calls to a real DID or a simulator number
route to its workspace, where the voice booking flow collects the caller’s name
and callback number, optionally records an appointment reason, offers available
times, repeats the selected time, and books only after an explicit verbal
confirmation. Bookings appear in the workspace dashboard; outbound email/SMS
confirmation is not enabled.

Phone numbers requested from a workspace are simulator-only values. They are
kept separate from provider DIDs, but FreeSWITCH can route them to their
associated workspace when dialed from a registered Linphone account (for
example, extension `1000`). They are not real telephone numbers and cannot be
reached from the public phone network. Workspace locales are stored for
configuration, but the current development STT/TTS deployment remains
English-only.

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
| `BARGE_IN_ENABLED` | `true` | Allow caller speech to interrupt AI playback |
| `BARGE_IN_MS` | `400` | Caller speech duration required to interrupt AI playback |
| `BARGE_IN_RMS_THRESHOLD` | `0.006` | Minimum audio level for barge-in |
| `SILENCE_MS` | `600` | Quiet interval before processing caller speech |
| `TTS_CHUNK_CHARS` | `120` | Maximum streamed text chunk size before forcing TTS |
| `RMS_THRESHOLD` | `0.010` | Minimum energy to trigger VAD |
