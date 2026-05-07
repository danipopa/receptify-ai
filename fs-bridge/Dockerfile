FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt .
COPY main.py .

ENV FS_HOST=127.0.0.1 \
    FS_PORT=8021 \
    FS_PASSWORD=R3c3pt1fy#ESL@xP9kZm2X \
    HOST=0.0.0.0 \
    PORT=9094 \
    WAV_DIR=/tmp/fs-bridge-wav \
    LOG_LEVEL=INFO

EXPOSE 9094

ENTRYPOINT []
CMD ["python3", "main.py"]
