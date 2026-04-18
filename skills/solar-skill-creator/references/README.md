# Upstage API reference — selector

Pick the reference file that matches the user's intent. If you are not sure which Upstage API the user needs, **ask them before picking one** — the wrong choice wastes credits and produces misleading output.

| User intent | Reference file | Endpoint |
|-------------|---------------|----------|
| Generate / summarize / reason over text (chat, agents, tool use) | [`upstage-chat.md`](upstage-chat.md) | `POST /v1/chat/completions` |
| Embed text for search, RAG, clustering, classification | [`upstage-embeddings.md`](upstage-embeddings.md) | `POST /v1/embeddings` |
| Convert a document into structured HTML/Markdown with layout (tables, headings, charts) | [`upstage-document-parse.md`](upstage-document-parse.md) | `POST /v1/document-digitization` (`model=document-parse`) |
| Extract specific key/value fields from a document against a JSON Schema | [`upstage-information-extract.md`](upstage-information-extract.md) | `POST /v1/information-extraction/chat/completions` |
| Extract raw text + word bounding boxes from a document image | [`upstage-ocr.md`](upstage-ocr.md) | `POST /v1/document-digitization` (`model=ocr`) |

## Composing APIs

Most real-world skills chain several of these together:

- **RAG over PDFs** → Document Parse (layout) → chunk `elements[]` → Embeddings (`embedding-passage` for corpus, `embedding-query` at query time) → Chat (`solar-pro3`) with retrieved chunks as context.
- **Structured form extraction** → Information Extract with a JSON Schema; fall back to Document Parse + Chat if the schema is too dynamic.
- **Scanned archive search** → OCR (for text + positions) → Embeddings → Chat for answer synthesis.

## Authentication (applies to all APIs)

Every request expects a bearer token:

```
Authorization: Bearer $UPSTAGE_API_KEY
```

Copy `assets/.env.example` to `.env`, put your key in, and load it with something like `os.environ["UPSTAGE_API_KEY"]`. Tell the user not to commit `.env`.
