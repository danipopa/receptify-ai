FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY main.py .

ENV WHISPER_MODEL=base \
    WHISPER_DEVICE=cpu \
    WHISPER_COMPUTE=int8 \
    WHISPER_LANGUAGE=en \
    HOST=0.0.0.0 \
    PORT=9092 \
    LOG_LEVEL=INFO

EXPOSE 9092

CMD ["python", "main.py"]
