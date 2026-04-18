# Upstage Information Extract (Universal)

Verified on: 2026-04-18
Official docs: https://console.upstage.ai/docs/capabilities/extract/universal-extraction

Schema-driven, zero-shot key/value extraction from any document type — invoices, receipts, bank statements, contracts, forms. You supply a JSON Schema in `response_format` and the model returns a strictly-conforming JSON object as the assistant message. OpenAI Chat Completions compatible.

## Endpoint

Base URL differs from Chat/Embeddings — the capability is namespaced under `/information-extraction`:

```
POST https://api.upstage.ai/v1/information-extraction/chat/completions
Authorization: Bearer $UPSTAGE_API_KEY
Content-Type: application/json
```

OpenAI SDK: `base_url="https://api.upstage.ai/v1/information-extraction"`.

## Model aliases

| Alias | Points to | RPS (Sync / Async) |
|-------|-----------|--------------------|
| `information-extract` | `information-extract-260304` | 1 / 2 |
| `information-extract-nightly` | — | 1 / 2 |

## Request shape

1. Attach the document as a base64 data URL inside a `user` message's `image_url` content part.
2. Describe the desired output via `response_format = {"type": "json_schema", "json_schema": {...}}`.
3. Optional: `extra_body={"mode": "enhanced"}` for complex tables / poor scans / handwriting (Beta, higher cost).

```python
import base64, json, os
from openai import OpenAI

client = OpenAI(
    api_key=os.environ["UPSTAGE_API_KEY"],
    base_url="https://api.upstage.ai/v1/information-extraction",
)

with open("bank_statement.png", "rb") as f:
    b64 = base64.b64encode(f.read()).decode()

resp = client.chat.completions.create(
    model="information-extract",
    messages=[{
        "role": "user",
        "content": [{
            "type": "image_url",
            "image_url": {"url": f"data:application/octet-stream;base64,{b64}"},
        }],
    }],
    response_format={
        "type": "json_schema",
        "json_schema": {
            "name": "bank_statement",
            "schema": {
                "type": "object",
                "properties": {
                    "bank_name": {"type": "string", "description": "Name of bank"},
                    "transactions": {
                        "type": "array",
                        "items": {"type": "object", "properties": {
                            "transaction_date": {"type": "string"},
                            "transaction_description": {"type": "string"},
                        }},
                    },
                },
            },
        },
    },
)

result = json.loads(resp.choices[0].message.content)
```

## Response

```json
{
  "id": "iex-AQZoWf2p5j6TO-AE",
  "choices": [{
    "finish_reason": "stop",
    "message": {"content": "{\"bank_name\":\"Bank of Dream\"}", "role": "assistant"}
  }],
  "created": 1742838017,
  "model": "information-extract-260304",
  "usage": {"completion_tokens": 9, "prompt_tokens": 951, "total_tokens": 960}
}
```

`message.content` is a **stringified** JSON that strictly matches the schema. Always `json.loads()` it.

## Schema rules

- `json_schema.name`: ≤ 64 chars, alphanumerics / `_` / `-` only.
- `json_schema.schema`: follows JSON Schema Syntax. See **Writing a schema** docs page for advanced patterns (arrays of objects, enums, descriptions — unverified details, confirm against docs).

## Input requirements

- Formats: JPEG, PNG, BMP, PDF, TIFF, HEIC, DOCX, PPTX, XLSX, HWP, HWPX
- Max 50 MB, 100 pages, 200,000,000 pixels per page at 150 DPI
- Character sets: Alphanumeric, Hangul, Hanja, Katakana, Hiragana supported; Hanzi/Kanji beta

## Notes

- For document types you ship the same schema for repeatedly (e.g. invoices at scale), check whether **Prebuilt extraction** is a better fit — it uses fine-tuned per-document-type models (unverified endpoint/pricing, confirm against docs).
- To extract only the relevant pages from a large PDF first, pair with Document Parse (`upstage-document-parse.md`) and feed just the needed elements back in.
