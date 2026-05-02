FROM python:3.11-slim

# FreeSWITCH CLI must be available — mount the host binary or install FS client tools
# For K8s: use hostPath or a sidecar that shares the socket.
WORKDIR /app
COPY requirements.txt .
COPY main.py .

ENV FS_CLI=/usr/local/freeswitch/bin/fs_cli \
    FS_HOST=127.0.0.1 \
    FS_PORT=8021 \
    FS_PASSWORD=ClueCon \
    HOST=0.0.0.0 \
    PORT=9094 \
    WAV_DIR=/tmp/fs-bridge-wav \
    LOG_LEVEL=INFO

EXPOSE 9094

CMD ["python", "main.py"]
