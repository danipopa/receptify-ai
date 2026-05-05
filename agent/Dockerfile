FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 \
    gcc \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY main.py .

ENV WS_HOST=0.0.0.0 \
    WS_PORT=9090 \
    HTTP_PORT=9095 \
    STT_URL=http://stt-service:9092 \
    RAG_URL=http://rag-service:9091 \
    TTS_URL=http://tts-service:9093 \
    FS_BRIDGE_URL=http://fs-bridge:9094 \
    RECORDING_DIR=/tmp/recordings \
    RECORDING_ENABLED=false \
    LOG_LEVEL=INFO

EXPOSE 9090 9095

CMD ["python", "main.py"]
