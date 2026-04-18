# Upstage Document Parse

Verified on: 2026-04-18
Official docs: https://console.upstage.ai/docs/capabilities/parse/api-quickstart

Layout-aware document parsing: detects headings, paragraphs, tables, lists, charts and returns structured HTML/Markdown/text plus per-element coordinates. Parse uses OCR under the hood — reach for this (not the raw OCR endpoint) whenever you need document structure.

## Endpoint

```
POST https://api.upstage.ai/v1/document-digitization
Authorization: Bearer $UPSTAGE_API_KEY
Content-Type: multipart/form-data
```

This endpoint is **shared with Document OCR**. The `model` form field selects which capability runs.

## Model aliases

| Alias | Points to | RPS (Sync / Async) |
|-------|-----------|--------------------|
| `document-parse` | `document-parse-260128` | 1 / 2 |
| `document-parse-nightly` | — | 1 / 2 |

## Form fields

| Field | Required | Example |
|-------|----------|---------|
| `document` | yes | file binary |
| `model` | yes | `document-parse` |
| `ocr` | optional | `force` (run OCR even on digital-born PDFs) |
| `base64_encoding` | optional | `['table']` — return base64 crops for the listed element types |

## Minimal request (Python)

```python
import os, requests

def parse_document(file_path: str) -> dict:
    with open(file_path, "rb") as f:
        resp = requests.post(
            "https://api.upstage.ai/v1/document-digitization",
            headers={"Authorization": f"Bearer {os.environ['UPSTAGE_API_KEY']}"},
            files={"document": f},
            data={
                "model": "document-parse",
                "ocr": "force",
                "base64_encoding": "['table']",
            },
        )
    resp.raise_for_status()
    return resp.json()
```

## Response (excerpt)

```json
{
  "api": "2.0",
  "content": {
    "html": "<h1 id='0'>INVOICE</h1>...",
    "markdown": "",
    "text": ""
  },
  "elements": [{
    "id": 0,
    "page": 1,
    "category": "heading1",
    "content": {"html": "<h1 id='0'>INVOICE</h1>", "markdown": "", "text": ""},
    "coordinates": [{"x": 0.06, "y": 0.05}, {"x": 0.24, "y": 0.05},
                    {"x": 0.24, "y": 0.10}, {"x": 0.06, "y": 0.10}]
  }],
  "model": "document-parse-251217",
  "usage": {"pages": 1}
}
```

Coordinates are normalized to `[0, 1]` against page dimensions. Element categories observed: `heading1`, `paragraph`, `list` (full taxonomy and chart/table element shapes — see "Understanding output" docs page, **unverified — confirm against docs**).

## Async mode

Large documents can be processed at 2 RPS via the Async API — endpoint path **unverified — confirm against docs** (Handling large documents page).

## Input requirements

Same file pipeline as OCR / Information Extract: JPEG, PNG, BMP, PDF, TIFF, HEIC, DOCX, PPTX, XLSX, HWP, HWPX. Max 50 MB, 100 pages, 200,000,000 pixels per page at 150 DPI. Confirm edge cases against docs (**unverified for Parse specifically**).

## Notes

- For plain text only (no layout), prefer `upstage-ocr.md` — it's cheaper.
- To feed Parse output into a RAG pipeline: use `content.html` as the canonical representation, chunk by `elements[]`, then embed each chunk with `embedding-passage` (see `upstage-embeddings.md`).
