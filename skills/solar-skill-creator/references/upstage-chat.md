# Upstage Chat (Solar LLM)

Verified on: 2026-04-18
Official docs: https://console.upstage.ai/docs/capabilities/chat

OpenAI-compatible Chat Completions backed by the Solar family of LLMs (MoE and dense variants). Drop-in replacement for `openai.chat.completions.create` — only the `base_url` and `model` change.

## Endpoint

```
POST https://api.upstage.ai/v1/chat/completions
Authorization: Bearer $UPSTAGE_API_KEY
Content-Type: application/json
```

OpenAI SDK base URL: `https://api.upstage.ai/v1`.

## Model aliases

Prefer aliases so new model versions are picked up automatically.

| Alias | Points to | RPM / TPM |
|-------|-----------|-----------|
| `solar-pro3` | `solar-pro3-260323` | 100 / 50,000 |
| `solar-pro2` | `solar-pro2-251215` | 100 / 50,000 |
| `solar-mini` | `solar-mini-250422` | 100 / 50,000 |
| `syn-pro` | `syn-pro-251021` | 100 / 50,000 |
| `solar-pro2-nightly` | — | 100 / 50,000 |
| `solar-mini-nightly` | — | 100 / 50,000 |

(`solar-pro3-260126` is still reachable as a dated pin but **deprecation scheduled** — unverified cut-off date, confirm against docs.)

## Client setup

```python
from openai import OpenAI
import os

client = OpenAI(
    api_key=os.environ["UPSTAGE_API_KEY"],
    base_url="https://api.upstage.ai/v1",
)
```

## Single-turn

```python
resp = client.chat.completions.create(
    model="solar-pro3",
    messages=[{"role": "user", "content": "Hello"}],
)
print(resp.choices[0].message.content)
```

## System prompt + multi-turn (stateless)

```python
messages = [
    {"role": "system", "content": "You summarize bug reports into one sentence."},
    {"role": "user", "content": user_text},
]
reply = client.chat.completions.create(model="solar-pro3", messages=messages)
messages.append({"role": "assistant", "content": reply.choices[0].message.content})
```

## Streaming

```python
stream = client.chat.completions.create(
    model="solar-pro3",
    messages=[{"role": "user", "content": "Tell me a story"}],
    stream=True,
)
for chunk in stream:
    if chunk.choices[0].delta.content:
        print(chunk.choices[0].delta.content, end="")
```

## Response (non-streaming)

```json
{
  "id": "e1a90437-df41-45cd-acc6-a7bacbdd2a86",
  "object": "chat.completion",
  "created": 1707269210,
  "model": "solar-pro3",
  "choices": [{
    "index": 0,
    "message": {"role": "assistant", "content": "Hello and welcome!"},
    "logprobs": null,
    "finish_reason": "stop"
  }],
  "usage": {"prompt_tokens": 23, "completion_tokens": 12, "total_tokens": 35},
  "system_fingerprint": null
}
```

## Notes

- Supports the standard OpenAI parameters (`temperature`, `top_p`, `max_tokens`, `stop`, `stream`, function calling). Full parameter matrix: see docs (unverified — confirm against docs).
- On `429 Too Many Requests`, back off and retry — rate limits are per-minute.
