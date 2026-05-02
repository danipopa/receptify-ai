# context/

This directory contains the knowledge base for the RAG service.

## Files

| File | Description |
|---|---|
| `ai-ivr-context.txt` | Plain-text FAQ / knowledge base loaded by the RAG service |

## How to edit

Open `ai-ivr-context.txt` and write your content in plain English sentences.
After editing, trigger a rebuild without restarting the service:

```bash
curl -X POST http://localhost:9091/rebuild
```

## Tips for good retrieval

- Write in full sentences, not bullet points without context.
- Keep related facts in the same paragraph (they become the same chunk).
- Each chunk is ~60 words by default (`RAG_CHUNK_WORDS` env var).
- Avoid abbreviations the caller might not use — spell things out.
