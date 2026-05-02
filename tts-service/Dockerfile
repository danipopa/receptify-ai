FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY main.py .

# Piper binary and model are mounted at runtime via volume / ConfigMap
ENV PIPER_BIN=/opt/ai-ivr-venv/bin/piper \
    PIPER_MODEL=/opt/piper/en_US-lessac-medium.onnx \
    OUTPUT_SAMPLE_RATE=8000 \
    PIPER_TIMEOUT=10 \
    HOST=0.0.0.0 \
    PORT=9093 \
    LOG_LEVEL=INFO

EXPOSE 9093

CMD ["python", "main.py"]
