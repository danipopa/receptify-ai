FROM python:3.13-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    NO_TORCH_COMPILE=1 \
    MOSHI_DEVICE=cpu \
    MOSHI_HOST=0.0.0.0 \
    MOSHI_SERVER_PORT=8998 \
    MOSHI_CPU_THREADS=4

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates libgomp1 libportaudio2 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .

RUN python -m pip install --no-cache-dir \
      --index-url https://pypi.org/simple \
      --extra-index-url https://download.pytorch.org/whl/cpu \
      torch==2.9.1+cpu \
    && python -m pip install --no-cache-dir --no-deps moshi==0.2.13 \
    && python -m pip install --no-cache-dir -r requirements.txt

COPY run_server.py .

EXPOSE 8998

CMD ["python", "run_server.py"]
