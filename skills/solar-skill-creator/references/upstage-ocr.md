# Upstage Document OCR

Verified on: 2026-04-18
Official docs: https://console.upstage.ai/docs/capabilities/parse/document-ocr

Raw text + word-level bounding boxes + per-word confidence from any document image. Use this when you need positional OCR output and do **not** care about layout structure. For structured output (headings, tables, markdown), use `upstage-document-parse.md` instead.

## Endpoint

```
POST https://api.upstage.ai/v1/document-digitization
Authorization: Bearer $UPSTAGE_API_KEY
Content-Type: multipart/form-data
```

Shared endpoint with Document Parse — the `model` form field selects the capability.

## Model aliases

| Alias | Points to | RPS |
|-------|-----------|-----|
| `ocr` | `ocr-250904` | 1 |

## Form fields

| Field | Required | Example |
|-------|----------|---------|
| `document` | yes | file binary |
| `model` | yes | `ocr` |

## Minimal request (Python)

```python
import os, requests

def ocr_document(file_path: str) -> dict:
    with open(file_path, "rb") as f:
        resp = requests.post(
            "https://api.upstage.ai/v1/document-digitization",
            headers={"Authorization": f"Bearer {os.environ['UPSTAGE_API_KEY']}"},
            files={"document": f},
            data={"model": "ocr"},
        )
    resp.raise_for_status()
    return resp.json()
```

## Response

```json
{
  "apiVersion": "1.1",
  "confidence": 0.9924988460974842,
  "metadata": {"pages": [{"height": 256, "page": 1, "width": 786}]},
  "mimeType": "multipart/form-data",
  "modelVersion": "ocr-250904",
  "numBilledPages": 1,
  "pages": [{
    "confidence": 0.9924988460974842,
    "height": 256, "id": 0, "width": 786,
    "text": "Print the words \nhello, world",
    "words": [{
      "id": 0,
      "text": "Print",
      "confidence": 0.9950619419121907,
      "boundingBox": {"vertices": [
        {"x": 65, "y": 52}, {"x": 221, "y": 55},
        {"x": 221, "y": 104}, {"x": 64, "y": 101}
      ]}
    }]
  }],
  "stored": true,
  "text": "Print the words \nhello, world"
}
```

Bounding boxes are **absolute pixel coordinates** (unlike Document Parse which uses normalized 0–1). Confidence scores are produced at character level then calibrated to word level — low-confidence words are the right trigger for human review.

## Input requirements

- Formats: JPEG, PNG, BMP, PDF, TIFF, HEIC, DOCX, PPTX, XLSX, HWP, HWPX
- Max 50 MB, 100 pages, 200,000,000 pixels per page at 150 DPI
- Character sets: Alphanumeric, Hangul, Hanja supported; Hanzi/Kanji beta
- Text size: optimal when text ≤ ~30% of page

## Robustness

Trained to ignore watermarks and checkboxes, and to detect upper-left corners of word boxes even on rotated pages.

## Notes

- If you need HTML/Markdown output or to reason about tables, reach for **Document Parse** instead — it wraps OCR with layout analysis.
- OCR does not provide line-level groupings in the top-level response; assemble lines yourself from `words[].boundingBox.vertices` if needed.
