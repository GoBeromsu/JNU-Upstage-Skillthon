# Upstage Embeddings

Verified on: 2026-04-18
Official docs: https://console.upstage.ai/docs/capabilities/embed

OpenAI-compatible embeddings for semantic search, classification, and clustering. Outputs are normalized (magnitude 1), so dot product equals cosine similarity.

## Endpoint

```
POST https://api.upstage.ai/v1/embeddings
Authorization: Bearer $UPSTAGE_API_KEY
Content-Type: application/json
```

OpenAI SDK base URL: `https://api.upstage.ai/v1`.

## Model aliases

| Alias | Points to | RPM / TPM | Use for |
|-------|-----------|-----------|---------|
| `embedding-query` | `solar-embedding-1-large-query` | 100 / 300,000 | short search queries |
| `embedding-passage` | `solar-embedding-1-large-passage` | 100 / 300,000 | indexed corpus/documents |

Batch limit: up to **100 inputs** per request, total **≤ 204,800 tokens**.

## Client setup

```python
from openai import OpenAI
import os

client = OpenAI(
    api_key=os.environ["UPSTAGE_API_KEY"],
    base_url="https://api.upstage.ai/v1",
)
```

## Single text

```python
resp = client.embeddings.create(
    model="embedding-query",
    input="What is the weather today?",
)
vector = resp.data[0].embedding  # list[float], magnitude 1
```

## Batch

```python
passages = ["Text one", "Text two", "Text three"]
resp = client.embeddings.create(model="embedding-passage", input=passages)
vectors = [d.embedding for d in resp.data]
```

## Similarity

```python
import numpy as np

def most_similar(query: str, passages: list[str]) -> str:
    q = client.embeddings.create(model="embedding-query", input=query).data[0].embedding
    ps = [d.embedding for d in
          client.embeddings.create(model="embedding-passage", input=passages).data]
    return passages[int(np.argmax([np.dot(q, p) for p in ps]))]
```

## Response

```json
{
  "object": "list",
  "data": [{
    "object": "embedding",
    "index": 0,
    "embedding": [0.01850688, -0.0066606696, ...]
  }],
  "model": "embedding-query",
  "usage": {"prompt_tokens": 21, "total_tokens": 21}
}
```

## Notes

- Always use `embedding-query` for the **query side** and `embedding-passage` for the **corpus side** — they are trained asymmetrically.
- For RAG: embed corpus once with `embedding-passage`, store vectors, then embed each user query with `embedding-query` at retrieval time.
