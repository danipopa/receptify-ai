FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY main.py .

ENV FAQ_FILE=/opt/receptify-ai/context/ai-ivr-context.txt \
    EMBEDDING_MODEL=nomic-embed-text \
    LLM_MODEL=llama3.2:1b \
    OLLAMA_HOST=ollama:11434 \
    RAG_CHUNK_WORDS=60 \
    RAG_TOP_K=3 \
    OLLAMA_TIMEOUT=20 \
    HOST=0.0.0.0 \
    PORT=9091 \
    LOG_LEVEL=INFO

EXPOSE 9091

CMD ["python", "main.py"]
