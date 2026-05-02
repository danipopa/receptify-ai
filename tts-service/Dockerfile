FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg wget \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Download Piper voice model (baked into image — no volume needed)
ARG PIPER_MODEL_URL=https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx
RUN mkdir -p /opt/piper \
    && wget -q -O /opt/piper/en_US-lessac-medium.onnx       "$PIPER_MODEL_URL" \
    && wget -q -O /opt/piper/en_US-lessac-medium.onnx.json  "${PIPER_MODEL_URL}.json"

COPY main.py .

ENV PIPER_BIN=/usr/local/bin/piper \
    PIPER_MODEL=/opt/piper/en_US-lessac-medium.onnx \
    OUTPUT_SAMPLE_RATE=8000 \
    PIPER_TIMEOUT=10 \
    HOST=0.0.0.0 \
    PORT=9093 \
    LOG_LEVEL=INFO

EXPOSE 9093

CMD ["python", "main.py"]
