FROM ghcr.io/danipopa/freeswitch:latest

RUN apt-get update && apt-get install -y --no-install-recommends python3 python3-pip && rm -rf /var/lib/apt/lists/*

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

ENTRYPOINT []
CMD ["python3", "main.py"]
