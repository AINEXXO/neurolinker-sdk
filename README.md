# neurolinker-sdk

NeuroLinker is a document intelligence service by Ainexxo S.R.L. that automates the full ingestion pipeline for RAG applications — from PDF extraction to vector-store loading. This SDK is the official Python client for the NeuroLinker API: it provides sync and async clients for the complete pipeline (extraction full and field-based, bucket management, chunking, embedding, and vector-store loading), plus RAG evaluation with Ragas metrics (one-shot batch and continuous tracking).

## Table of contents

- [Installation](#installation)
- [Quick start](#quick-start)
- [Pipeline overview](#pipeline-overview)
- [Client](#client)
- [Extraction](#extraction)
- [Management](#management)
- [Chunking](#chunking)
- [Embedding](#embedding)
- [Vector Store](#vector-store)
- [Evaluation](#evaluation)
- [End-to-end pipeline](#end-to-end-pipeline)
- [Error handling](#error-handling)
- [Support](#support)
- [License](#license)

## Installation

```bash
pip install neurolinker-sdk
```

Requires Python 3.11+.

For continuous **evaluation tracking** of a live RAG, install the tracking extra plus your framework's OpenInference instrumentor — e.g. `pip install neurolinker-sdk[tracking] openinference-instrumentation-langchain`. Any OpenInference instrumentor works (`instrument()` auto-discovers it); for a custom RAG traced manually, `[tracking]` alone is enough. See [Evaluation](#evaluation).

## Quick start

Get your API key at https://neurolinker.ainexxo.com — login → API KEY section.

```bash
export NEUROLINKER_API_KEY="your_token"
```

Or store it in a `.env` file at the project root — load it once at startup and `NeuroLinker.from_env()` picks it up automatically:

```python
from dotenv import load_dotenv
load_dotenv()  # reads .env into os.environ
```

**Sync**

```python
from neurolinker_sdk import NeuroLinker

with NeuroLinker.from_env() as client:
    # Submit a PDF for extraction
    response = client.extraction.extract(urls=["https://example.com/your-doc.pdf"])
    request_uid = client.extraction.extract_request_uid(response)

    # Wait for completion (the SDK polls until the job reaches a terminal state)
    status = client.extraction.wait_for_request(request_uid)
    doc_ids = client.extraction.extract_document_ids(status)

    # Fetch the extracted content
    docs = client.extraction.documents.json(doc_ids)
    print(docs)
```

**Async**

```python
from neurolinker_sdk import AsyncNeuroLinker

async with AsyncNeuroLinker.from_env() as client:
    response = await client.extraction.extract(urls=["https://example.com/your-doc.pdf"])
    request_uid = client.extraction.extract_request_uid(response)
    status = await client.extraction.wait_for_request(request_uid)
    doc_ids = client.extraction.extract_document_ids(status)
    docs = await client.extraction.documents.json(doc_ids)
    print(docs)
```

## Pipeline overview

The ingestion modules compose end-to-end. A typical RAG ingestion run goes through them in order:

```
   PDF (URL or upload)
        │
        ▼
  ┌──────────────┐
  │  extraction  │   text, structured layout, sections, summaries
  └──────────────┘
        │
        ▼
  ┌──────────────┐
  │  management  │   create a bucket and attach the extracted documents
  └──────────────┘
        │
        ▼
  ┌──────────────┐
  │   chunking   │   split documents into retrieval-sized chunks
  └──────────────┘
        │
        ▼
  ┌──────────────┐
  │  embedding   │   compute dense / sparse vectors for each chunk
  └──────────────┘
        │
        ▼
  ┌──────────────┐
  │ vector_store │   upsert into your vector database collection
  └──────────────┘
```

Two concepts to keep in mind:

- A **bucket** is the persistent container that holds extracted documents for the downstream pipeline. Chunking, embedding and vector-store jobs all read from a `bucket_uid`, never directly from extraction request UIDs. Create one with `management.buckets.create`, then attach extraction outputs with `management.buckets.add_sources`.
- Each module is **independent** — you don't have to run the full pipeline.


## Client

### Constructors

- `NeuroLinker(token, base_url="https://neurolinker.api.ainexxo.com", timeout_s=600.0, poll_interval_s=2.0, poll_max_interval_s=10.0, http_client=None)`
Sync client. `token` is required; all parameters are keyword-only.

- `AsyncNeuroLinker(token, base_url="https://neurolinker.api.ainexxo.com", timeout_s=600.0, poll_interval_s=2.0, poll_max_interval_s=10.0, http_client=None)`
Async client. Same parameters as the sync version.

- `NeuroLinker.from_env(timeout_s=None, poll_interval_s=None, poll_max_interval_s=None)`
Loads `NEUROLINKER_API_KEY` from the environment. Per-call overrides accepted for all timing parameters.

`from_env()` also reads (all optional):
- `NEUROLINKER_BASE_URL` — overrides the default API endpoint
- `NEUROLINKER_E2E_TIMEOUT_S` — request timeout (default `600`)
- `NEUROLINKER_E2E_POLL_INTERVAL_S` — initial polling interval (default `2`)
- `NEUROLINKER_E2E_POLL_MAX_INTERVAL_S` — max polling interval (default `10`)

- `AsyncNeuroLinker.from_env(timeout_s=None, poll_interval_s=None, poll_max_interval_s=None)`
Async version of `from_env`.

### Modules

The SDK groups the API into six modules reachable as attributes on the client:

| Module | Purpose |
|---|---|
| `extraction` | PDF extraction — full and field-based |
| `management` | Bucket CRUD |
| `chunking` | Chunking jobs |
| `embedding` | Embedding jobs |
| `vector_store` | Vector-store collections and load jobs |
| `evaluation` | RAG evaluation — one-shot batch (`.oneshot`) + continuous tracking (`.tracking`) |

## Extraction

PDF processing — full extraction or schema-based field extraction. The two pipelines are independent: pick one per document depending on what you want as output.

| Method | When to use it | Output |
|---|---|---|
| `extraction.extract(...)` | You want the full document content for downstream pipelines (RAG, search, chunking) | Markdown, structured JSON, per-page images, page/section summaries |
| `extraction.extract_fields(...)` | You only need a structured payload that conforms to a JSON Schema you supply (invoices, forms, contracts) | A JSON object matching your schema, retrievable via `documents.fields(...)` |
| `extraction.extract_fields_from_markdown(...)` | You already ran full extraction and want scalar fields from a document's markdown (no re-upload) | A JSON object matching your schema per document, retrievable via `documents.scalars(...)` |

Both reserve credits at submit time on a per-page basis (see the platform documentation for pricing).

- `client.extraction.extract(documents=None, urls=None, alias=None, description=None, enrichment_mode=None)`
Submit a full-extraction job. Provide **either** `documents=[("file.pdf", b"...")]` (local PDF) **or** `urls=["https://..."]` (PDF URLs). The two are mutually exclusive — exactly one is required. Optional `enrichment_mode` is `"base"` (Picture/Table get description only) or `"turbo"` (description + `extracted_text` + `legend` with neighbouring-page context). Omit to use the backend default.

- `client.extraction.extract_fields(json_schema, documents=None, urls=None, alias=None, description=None)`
Submit a field-extraction job. `json_schema` is required and must follow JSON Schema Draft 7 (supported subset). Provide **either** `documents=[("file.pdf", b"...")]` (local PDFs) **or** `urls=["https://..."]` (PDF URLs). Same XOR rule as `extract`. Example:

```python
client.extraction.extract_fields(
    json_schema={
        "type": "object",
        "properties": {
            "invoice_number": {"type": "string"},
            "issue_date":     {"type": "string", "description": "ISO date (YYYY-MM-DD)"},
            "total_amount":   {"type": "number"},
            "line_items": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "description": {"type": "string"},
                        "quantity":    {"type": "integer"},
                        "unit_price":  {"type": "number"},
                    },
                },
            },
        },
        "required": ["invoice_number", "total_amount"],
    },
    urls=["https://example.com/invoice.pdf"],
)
```

After completion, retrieve the extracted fields via `client.extraction.documents.fields(document_ids)`.

- `client.extraction.extract_fields_from_markdown(json_schema, document_ids, alias=None, description=None)`
Extract scalar fields from the markdown of **already full-extracted** documents — no re-upload. `document_ids` are the `document_uid` values of completed full-extraction documents; `json_schema` follows the same supported subset as `extract_fields`. The response carries a `document_map` mapping each source `document_uid` to a new one — poll the batch with `wait_for_request(request_uid)` and retrieve the values via `documents.scalars(new_ids)`. Use `extract_markdown_document_ids(submit_response)` to pull the new ids. Example:

```python
client.extraction.extract_fields_from_markdown(
    json_schema={
        "type": "object",
        "properties": {"invoice_number": {"type": "string"}, "total_amount": {"type": "number"}},
        "required": ["invoice_number"],
    },
    document_ids=["<completed-full-extraction-document_uid>"],
)
```

- `client.extraction.generate_schema(description)`
Generate a JSON Schema from a natural-language description — the returned schema is ready to be passed to `extract_fields`. Example: `description="Extract invoice number, issue date, and total amount from an invoice"`.

- `client.extraction.list_tasks()`
List the processing tasks available in the system.

- `client.extraction.status.request(request_id)`
Check the status of an extraction request by request UID.

- `client.extraction.status.document(document_id)`
Check the status of a single document by document UID.

- `client.extraction.wait_for_request(request_uid, timeout_s=None, poll_interval_s=None, poll_max_interval_s=None)`
Polling helper that waits for terminal status (`completed`, `failed`, `pending`), handling transient `404` during early processing. Per-call overrides for timeout / poll cadence.

- `client.extraction.documents.markdown(document_ids, content_types=None)`
Retrieve markdown payloads for the given document IDs. `content_types` accepts `ContentType` enum values or strings.

- `client.extraction.documents.json(document_ids, content_types=None)`
Retrieve structured JSON payloads, with optional content-type filtering.

- `client.extraction.documents.images(document_ids)`
Retrieve extracted image metadata (signed URLs).

- `client.extraction.documents.page_summaries(document_ids)`
Retrieve per-page summaries.

- `client.extraction.documents.section_summaries(document_ids)`
Retrieve summaries grouped by detected sections.

- `client.extraction.documents.document_summary(document_ids, summary_type="page" | "section")`
Retrieve a single consolidated summary. `summary_type` is required.

- `client.extraction.documents.fields(document_ids)`
Retrieve the structured fields payload for documents processed via `extract_fields`. Returns an error entry for documents processed via full extraction.

- `client.extraction.make_zip(job_uid, document_uid=None, local_images=False, content_types=None)`
Request a ZIP archive for a completed extraction job (entire job or a single document). With `local_images=True`, JSON/Markdown references are rewritten to local relative image paths. `content_types` (e.g. `["text"]`) filters JSON/Markdown content included in the ZIP.

### Filtering content

Some retrieval methods accept an optional filter to keep only specific kinds of content or summary granularity. Two enums are exported from the top-level package and can be passed as values or as plain strings.

- `ContentType` — used by `documents.markdown`, `documents.json`, and `make_zip` to filter which content kinds are returned:
  - `TEXT` — paragraphs and prose
  - `FORMULA` — math formulas
  - `TABLES` — extracted tables
  - `IMAGES` — extracted figures

  Omit `content_types` (default `None`) to get the full document with every content type. Pass a list (e.g. `content_types=[ContentType.TEXT]`) to keep only the kinds you need — useful for trimming payloads in RAG pipelines.

- `SummaryType` — used by `documents.document_summary` to select granularity: `PAGE` for per-page summaries, `SECTION` for per-section summaries.


## Management

CRUD for **buckets**, the persistent containers that hold extracted documents for chunking, embedding, and vector-store jobs. Those modules always read from a `bucket_uid`, never from raw extraction request UIDs — create a bucket once, attach extraction outputs to it with `buckets.add_sources`, and reuse it across runs.

- `client.management.buckets.create(name="my-bucket")`
Create a new bucket.

- `client.management.buckets.list()`
List all buckets owned by the API key.

- `client.management.buckets.get(bucket_uid)`
Retrieve a single bucket.

- `client.management.buckets.delete(bucket_uid)`
Delete a bucket.

- `client.management.buckets.add_sources(bucket_uid, sources=[{"request_uid": "...", "doc_uids": [...]}, ...])`
Attach extraction request UIDs (and optionally specific document UIDs) to a bucket. After this call the bucket is a valid input for chunking / embedding / vector-store jobs. Returns `None`.


## Chunking

Chunking jobs over a bucket.

- `client.chunking.jobs.create(bucket_uid, chunking=...)`
Submit a chunking job. Pass an instance of one of the five chunking configs (`RecursiveConfig`, `FixedSizeConfig`, `SentenceConfig`, `MarkdownHeaderConfig`, `ByTitleConfig`) described below.

- `client.chunking.jobs.get(bucket_uid, job_uid)`
Retrieve the current state of a chunking job.

- `client.chunking.jobs.wait(bucket_uid, job_uid, timeout_s=None, poll_interval_s=None, poll_max_interval_s=None)`
Poll until terminal status, with the same overrides as `wait_for_request`.

- `client.chunking.analyze(bucket_uid)`
Run statistical analysis on a bucket **after a chunking job has completed** — returns chunk-size distribution and a base64-encoded plot built from the existing output. Useful for inspecting the result of a chunking pass and deciding whether to re-run with adjusted parameters.

- `client.chunking.results(bucket_uid)`
Fetch the chunking output files for a bucket. Returns a `dict[filename, bytes]`. File content transits directly between the client and storage, not through the API server.

### Choosing a chunking strategy

Five strategies are available. Pick based on your documents and queries:

| Strategy | Best for | What it does |
|---|---|---|
| `RecursiveConfig` | Most documents. **General-purpose default.** | Splits on the largest natural boundary that fits (paragraph, line, sentence, word) and packs the pieces up to `chunk_size` tokens, with `chunk_overlap` tokens of whole sentences repeated between chunks |
| `FixedSizeConfig` | Uniform chunk sizes, benchmarking, unstructured text | Windows of exactly `chunk_size` tokens with `chunk_overlap` tokens of overlap, cut anywhere in the text |
| `SentenceConfig` | Prose, Q&A, legal and narrative text where a cut sentence loses meaning | Packs whole sentences up to `chunk_size` tokens, with whole-sentence overlap |
| `MarkdownHeaderConfig` | FAQ-style or hierarchical knowledge bases where chunks should map 1:1 to headings | One chunk per section at `heading_level`; deeper sections stay with their parent, oversized sections are split to fit `chunk_size` |
| `ByTitleConfig` | Well-structured documents (manuals, reports, papers) | A new chunk at every heading; short sections are combined while the chunk is below `min_chunk_size` |

In every strategy figures and tables are kept whole (a figure or table larger than `chunk_size` becomes its own chunk) and are never repeated as overlap.

Example configurations:

```python
from neurolinker_sdk.chunking import (
    ByTitleConfig, FixedSizeConfig, MarkdownHeaderConfig, RecursiveConfig,
    SentenceConfig, TokenizerConfig,
)

# (1) General-purpose default.
RecursiveConfig(
    chunk_size=512, chunk_overlap=64,                          # tokens
    tokenizer=TokenizerConfig(provider="huggingface", name="BAAI/bge-m3"),
    parse_figures=True, parse_tables=True,
    parse_headers=True, parse_footers=False,
)

# (2) Exact token windows, here measured with the OpenAI tokenizer.
FixedSizeConfig(
    chunk_size=400, chunk_overlap=40,
    tokenizer=TokenizerConfig(provider="tiktoken", name="cl100k_base"),
)

# (3) Whole sentences only.
SentenceConfig(chunk_size=384, chunk_overlap=48)

# (4) One chunk per "##" section.
MarkdownHeaderConfig(heading_level=2, chunk_size=1024)

# (5) A chunk per section, combining sections shorter than 128 tokens.
ByTitleConfig(chunk_size=1024, min_chunk_size=128)
```

Defaults when a field is omitted: `chunk_size=512`, `chunk_overlap=64`, `min_chunk_size=128`, `heading_level=2`. With a custom `chunk_size`, an omitted `chunk_overlap` defaults to `chunk_size // 8` and an omitted `min_chunk_size` to `chunk_size // 4` (capped at the defaults above). `chunk_size` ranges from 16 to 8192, and `chunk_overlap` / `min_chunk_size` must stay below it.

`tokenizer` (available on all five methods) measures `chunk_size` and overlap; match it to the embedding model you will use. `provider="huggingface"` takes any public Hugging Face Hub repository id (`org/model`, default `BAAI/bge-m3`, the tokenizer of `ainexxo-bge-m3`); `provider="tiktoken"` takes an OpenAI encoding, `cl100k_base` (`text-embedding-3-*`, `text-embedding-ada-002`) or `o200k_base`. A Hugging Face repository that is missing, private or gated is rejected when the job is submitted.

`metadata_request_uid` (optional, all methods) names a markdown field extraction run on the bucket whose per-document fields the vector load joins on every record.

## Embedding

Embedding jobs over a chunked bucket. Before configuring a job there are two quick choices to make: **which vector type(s)** to compute, and **which chunk fields** to feed in.

### Choosing dense vs sparse (vs both)

| Vector type | When to use | Notes |
|---|---|---|
| **Dense** | Semantic similarity — "find chunks that mean roughly the same thing". Default choice for general-purpose RAG retrieval. | Supported by all internal and external models. |
| **Sparse** | Lexical / keyword matching — "find chunks that mention this exact term or phrase". Useful for technical jargon, entity names, code identifiers. | Only some internal models support sparse output; external providers typically offer dense only. |
| **Both (hybrid)** | Best of both worlds. Configure dense **and** sparse on the same modality; combine the scores at query time on your vector DB. | Recommended when retrieval recall matters and you can afford the extra storage. |

The available internal models and the vector types each one supports are listed by `client.embedding.list_models()` — call it at runtime to pick a compatible model. For external providers, refer to the provider's own documentation.

### Available fields per modality

`inputs` is the list of chunk fields concatenated before being passed to the embedding model. Each field is only valid on the content types marked below — using a field on the wrong content type is rejected at submit time.

| Field | Text | Image | Table | Description |
|---|:---:|:---:|:---:|---|
| `content` | ✓ | | ✓ | Main text payload for text chunks and table items |
| `description` | | ✓ | ✓ | Semantic description generated for images/tables |
| `extracted_text` | | ✓ | | OCR text extracted from the image |
| `data` | | | ✓ | Structured table payload flattened for embedding |
| `legend` | | ✓ | ✓ | Inline legend / explanatory note associated with the element |
| `header_path` | ✓ | ✓ | ✓ | Parent header hierarchy prepended when requested |
| `image_base64` | | ✓ | | Base64-encoded image bytes for vision-capable models |

### Methods

- `client.embedding.jobs.create(bucket_uid, embeddings=...)`
Submit an embedding job. Pass a list of flat `Content` definitions describing which content to embed (text / image / table), which chunk fields to use as input, and which dense / sparse vectors to compute.

- `client.embedding.jobs.get(bucket_uid, job_uid)`
Retrieve the current state of an embedding job.

- `client.embedding.jobs.wait(bucket_uid, job_uid, timeout_s=None, poll_interval_s=None, poll_max_interval_s=None)`
Poll until terminal status.

- `client.embedding.list_models()`
List the embedding models available on the backend.

- `client.embedding.results(bucket_uid)`
Fetch the embedding output files for a bucket. Same shape as `chunking.results`.

The primary SDK API is a flat list of `Content` entries. Each `Content` block declares a `content_type`, the `inputs` to concatenate, and one or more `EmbeddingVector`s to compute with that same input set. If you need different inputs for the same modality, create multiple `Content` entries with the same `content_type`.

```python
from neurolinker_sdk.embedding import Content, EmbeddingVector

text_dense = EmbeddingVector(
    vector_type="dense",
    field_name="text_dense",
    model_name="ainexxo-bge-m3",
)

text_sparse = EmbeddingVector(
    vector_type="sparse",
    field_name="text_sparse",
    model_name="ainexxo-splade",
)

image_dense = EmbeddingVector(
    vector_type="dense",
    field_name="image_dense",
    model_name="jina_ai/jina-embeddings-v4",
    api_key="jina_api_key",
)

embeddings = [
    Content(
        content_type="text",
        inputs=["content"],
        vectors=[text_dense, text_sparse],
    ),
    Content(
        content_type="image",
        inputs=["image_base64", "description"],
        vectors=[image_dense],
    ),
    Content(
        content_type="table",
        inputs=["content", "description", "data"],
        vectors=[
            EmbeddingVector(
                vector_type="dense",
                field_name="table_dense",
                model_name="text-embedding-3-small",
                api_key="sk_openai_api_key",
            )
        ],
    ),
]

client.embedding.jobs.create(
    bucket_uid="your_bucket_uid",
    embeddings=embeddings,
)
```

Conventions worth knowing:
- `field_name` cannot start with `item_` or `chunk_` — those prefixes are reserved for internal fields. This is the name you reference later as `source` in a `FieldMapping` when loading into a vector store, so keep it stable across runs of the same project.
- `Content.vectors` is the inner list of vectors to compute for that content block.
- Internal Ainexxo models use `model_name="ainexxo-..."` and omit `api_key`.
- External LiteLLM models use the LiteLLM `model_name` as-is and carry their own `api_key` directly on each `EmbeddingVector`. See the [LiteLLM supported embedding models](https://docs.litellm.ai/docs/embedding/supported_embedding) for valid model names.

## Vector Store

Bring your own cluster — the SDK upserts your embeddings into a collection on the vector database you specify in `VectorDBConfig`.

**Currently supported vector databases:**

- Milvus / Zilliz
- Qdrant
- Pinecone

You don't pass a `provider` field — it is detected from the URI of your cluster. Supply the URI and the cluster's connection token as `api_key` on `VectorDBConfig`. The same `VectorDBConfig` is used by both `collections.create(...)` and `jobs.create(...)`.

- `client.vector_store.collections.create(collection={...}, vector_db_config={...}, database="")`
Create a vector-store collection. Idempotent — returns `already_existed=true` if it already exists. `collection` accepts a `CollectionSchema` (or dict). `vector_db_config` is a `VectorDBConfig` (or dict) selecting the backend and its connection details. `database` is optional and provider-specific — set it according to your provider's documentation; Qdrant requires it empty.

- `client.vector_store.jobs.create(bucket_uid, collection_name, field_mappings=[...], vector_db_config=..., database="")`
Submit a vector-load job — reads the embedding output for `bucket_uid` and writes it into `collection_name`. `field_mappings` describes how chunk fields map to collection fields. `database` follows the same rule as above.

- `client.vector_store.jobs.get(bucket_uid, job_uid)`
Retrieve the current state of a vector-load job.

- `client.vector_store.jobs.wait(bucket_uid, job_uid, timeout_s=None, poll_interval_s=None, poll_max_interval_s=None)`
Poll until terminal status.

Loading embeddings into a vector database needs three pieces: a `CollectionSchema` (the target collection's structure, made of `FieldDef` columns), a `VectorDBConfig` (cluster connection details), and a list of `FieldMapping`s (how to populate the collection columns from the embedded records).

The `source` of a `FieldMapping` references one of three namespaces. The data has two levels:

- **Parent chunk** — produced by the chunking step. Carries the full multimodal content of a section of the document (text plus inline figure/table descriptions). Typically what you feed to the LLM at retrieval time.
- **Embedding items** — derived from the parent, one per modality present in the chunk: a text item with the chunk's text content, one image item per figure (with its description, image bytes, OCR text, legend…), one table item per table (with its content, data, and description). The vector embeddings live on these items.

For example, a chunk containing 2 figures and 1 table produces 4 items (1 text + 2 image + 1 table). At query time you match against the items' vectors but typically retrieve the parent's `chunk_content` to give the LLM the surrounding context.

| Namespace | When to use as `source` | Examples |
|---|---|---|
| `chunk_*` | Per-chunk fields — typically the **context you feed to the LLM** at retrieval time. | `chunk_id`, `chunk_source_file`, `chunk_content` (full chunk, multimodal), `chunk_header_path`, `chunk_pages` |
| `item_*` | Per-item fields — the row you upsert. | `item_id` (primary key), `item_element_type` (`text` / `image` / `table`) |
| `<field_name>` | The dense or sparse vector itself. | `text_dense`, `text_sparse` (the `field_name` you picked in `EmbeddingVector`) |

`chunk_*` fields — available on every chunk regardless of which modality items it produced:

| Source | Description |
|---|---|
| `chunk_id` | Id of the parent chunk |
| `chunk_source_file` | Document the chunk comes from |
| `chunk_content` | Full chunk content (text plus inline figure/table descriptions) — typical LLM context at retrieval |
| `chunk_header_path` | Section/heading hierarchy leading to the chunk |
| `chunk_pages` | Pages spanned by the chunk |

Modality-specific `item_*` fields — each is only present on items of the corresponding modality:

| Source | Text | Image | Table | Description |
|---|:---:|:---:|:---:|---|
| `item_content` | ✓ | | ✓ | Text content for text items and flattened content for table items |
| `item_description` | | ✓ | ✓ | Semantic description carried by image/table items |
| `item_extracted_text` | | ✓ | | OCR text extracted from the image |
| `item_data` | | | ✓ | Table data in key:value form |
| `item_legend` | | ✓ | ✓ | Legend / inline explanatory text |
| `item_image_base64` | | ✓ | | Base64-encoded image bytes |

```python
from neurolinker_sdk.vector_store import (
    CollectionSchema, FieldDef, FieldMapping, VectorDBConfig,
)

# A collection's schema — abstract dtypes, the provider translates them.
collection = CollectionSchema(
    name="my_collection",
    description="Documents indexed by SDK",
    fields=[
        FieldDef(name="chunk_id",   dtype="text", is_primary=True),
        FieldDef(name="content",    dtype="text"),
        FieldDef(name="text_dense", dtype="dense_vector", dim=1024, distance="cosine"),
    ],
)

# Map each collection field to a source from one of the three namespaces above.
field_mappings = [
    FieldMapping(name="chunk_id",   source="item_id"),
    FieldMapping(name="content",    source="item_content"),
    FieldMapping(name="text_dense", source="text_dense"),  # matches field_name above
]

# Vector-DB connection — supply your cluster URI and its connection token.
vdb = VectorDBConfig(
    uri="https://your-cluster-uri",
    api_key="<your-vector-db-token>",
)

client.vector_store.collections.create(collection=collection, vector_db_config=vdb)
load_job = client.vector_store.jobs.create(
    bucket_uid="<your-bucket-uid>",
    collection_name="my_collection",
    field_mappings=field_mappings,
    vector_db_config=vdb,
)
client.vector_store.jobs.wait("<your-bucket-uid>", load_job["job_uid"])
```

Supported `dtype` values: `text`, `int`, `float`, `bool`, `json`, `dense_vector` (requires `dim`), `sparse_vector`. Supported `distance` for `dense_vector`: `cosine` (default), `dot`, `euclidean`. Do not set `distance` on scalar or `sparse_vector` fields. A collection can have at most one field with `is_primary=True`.

Provider-specific settings live in two places:

- **`FieldDef.options`** — per-field knobs (e.g. Milvus `max_length`).
- **`CollectionSchema.options`** — collection-wide knobs (e.g. Pinecone serverless `cloud` / `region`).

The common schema contract (`name`, `dtype`, `dim`, `distance`, `is_primary`) is portable across providers — reach for `options` only when targeting a specific provider's capability. Unknown keys are rejected.

**Field options** (`FieldDef.options`):

| Provider | Applies to | Supported keys | Notes |
|---|---|---|---|
| Milvus / Zilliz | all fields | `description` | Adds a description to the field. |
| Milvus / Zilliz | `text` fields | `max_length`, `enable_analyzer`, `enable_match` | Maximum text length, analyzer, and exact-match indexing. |
| Milvus / Zilliz | primary key field | `auto_id` | Auto-generate the primary key value. Defaults to `False`. |

Pinecone and Qdrant do not currently take field options.

**Collection options** (`CollectionSchema.options`):

| Provider | Supported keys | Notes |
|---|---|---|
| Pinecone | `cloud`, `region` | Serverless index placement. Defaults to `aws` / `us-east-1`. |

Milvus / Zilliz and Qdrant do not currently take collection options.

Example — Pinecone serverless index in `eu-central-1`:

```python
CollectionSchema(
    name="neurolinker-docs",
    options={"cloud": "aws", "region": "eu-central-1"},
    fields=[
        FieldDef(name="chunk_id",   dtype="text", is_primary=True),
        FieldDef(name="text_dense", dtype="dense_vector", dim=1024),
    ],
)
```

## Evaluation

Evaluate your RAG with [Ragas](https://docs.ragas.io) metrics, in two complementary modes:

- **One-shot** (`client.evaluation.oneshot`) — score a batch dataset of pre-computed RAG outputs.
- **Tracking** (`client.evaluation.tracking` + `instrument`) — attach to a live RAG and score every query automatically, continuously.

### One-shot

Upload a JSONL dataset of pre-computed RAG outputs; the service scores every row and returns the per-row scores plus an aggregated summary. Black-box: the dataset is the only input — not coupled to buckets or the rest of the pipeline.

The dataset is JSONL (one JSON object per line) with the Ragas-canonical columns. `user_input` and `response` are required; `retrieved_contexts` (list of strings) and `reference` (string) are optional — including them unlocks more metrics (faithfulness, the context metrics, answer/factual correctness, ...).

- `client.evaluation.oneshot.jobs.create(dataset=("data.jsonl", b"..."))`
Upload the JSONL dataset and enqueue the evaluation in one request. The dataset is passed in memory as `(filename, bytes)`; the filename must end with `.jsonl`. Returns the body carrying `eval_uid` + `status`.

- `client.evaluation.oneshot.jobs.get(eval_uid)`
Retrieve the current state of an evaluation (`pending` → `processing` → `completed` / `failed`); on completion it also carries `metrics_computed` / `metrics_skipped`.

- `client.evaluation.oneshot.jobs.wait(eval_uid, timeout_s=None, poll_interval_s=None, poll_max_interval_s=None)`
Poll until terminal status (`completed` / `failed`).

- `client.evaluation.oneshot.results(eval_uid)`
Fetch the result of a completed evaluation. Returns the parsed `result.json` — `{eval_uid, rows, summary}`: per-row metric scores plus an aggregated summary (mean / percentiles / count per metric). Raises if the result isn't available yet — call `jobs.wait` first.

Example:

```python
import json

from neurolinker_sdk import NeuroLinker

rows = [
    {
        "user_input": "What is the capital of France?",
        "response": "The capital of France is Paris.",
        "retrieved_contexts": ["Paris is the capital and largest city of France."],
        "reference": "Paris is the capital of France.",
    },
]
dataset = ("data.jsonl", "\n".join(json.dumps(r) for r in rows).encode("utf-8"))

with NeuroLinker.from_env() as client:
    job = client.evaluation.oneshot.jobs.create(dataset=dataset)
    client.evaluation.oneshot.jobs.wait(job["eval_uid"])
    result = client.evaluation.oneshot.results(job["eval_uid"])
    print(result["summary"])
```

### Tracking (continuous)

Observe a RAG **in production**: attach the tracer once, and every query is traced to NeuroLinker, scored with Ragas, and surfaced in the dashboard. Same metrics as one-shot (the reference-free ones), computed continuously per query.

**1. Create a track (once).** The `track_uid` ties every traced query to this app — store it.

```python
with NeuroLinker.from_env() as client:
    track = client.evaluation.tracking.tracks.create(name="prod-rag")
    print(track["track_uid"])
```

**2. Instrument your app — one line.** Install the tracking extra + your framework's OpenInference instrumentor, then call `instrument()` at startup:

```bash
pip install neurolinker-sdk[tracking] openinference-instrumentation-langchain
# swap "langchain" for your framework (llama-index, openai, anthropic, haystack, ...)
# instrument() auto-discovers whatever instrumentor is installed — no allow-list
```

```python
import neurolinker_sdk

neurolinker_sdk.instrument(track_uid="<track_uid>")
```

Your framework's calls are now traced **automatically**. Notes:

- In a pre-forking server (gunicorn/uvicorn with workers), call `instrument()` **after** the fork (e.g. a post-fork hook), so the exporter thread lives in each worker.
- NeuroLinker uses a tracer provider **of its own**: only OpenInference spans (your framework's instrumentor, `record_query`, `@retriever`) are sent to NeuroLinker. An OpenTelemetry setup your app already has is left untouched, and its own spans (HTTP, database) never reach NeuroLinker. The call is idempotent.
- The two traces stay apart: a NeuroLinker span never nests under one of your app's spans (under an HTTP request span it starts a new trace, since NeuroLinker scores each trace from its root), and your app's spans opened during a `record_query`, a `continue_trace` or an `@retriever` search keep their own parent, so your APM's traces are unchanged. One exception is outside the SDK's control: OpenInference instrumentors make their own spans OpenTelemetry's current span, so an app span opened inside a framework call they trace (an HTTP call made by the LLM client, for example) has that span as its parent, which your APM never receives.
- `OTEL_SDK_DISABLED=true` turns all OpenTelemetry recording off, NeuroLinker's included; `instrument()` warns when it is set.
- A short-lived script should call `provider.force_flush()` (on the returned provider) before exiting, so the last spans are sent.

**Custom RAG with no framework instrumentor.** Install `[tracking]` and wrap each query, handing over the pieces explicitly:

```python
from neurolinker_sdk import instrument, record_query

instrument(track_uid="<track_uid>", manual=True)  # manual=True silences the "no instrumentor" notice

with record_query(user_input=question) as q:
    docs = my_retriever(question)
    q.set_contexts([d.text for d in docs])             # unlocks the context metrics
    resp = my_llm(question, docs)                      # your own LLM call
    q.set_response(resp.text)
    q.set_llm(                                         # optional — values come from the LLM response
        model=resp.model,
        input_tokens=resp.usage.input_tokens,
        output_tokens=resp.usage.output_tokens,
    )
```

**Agents: first input, final output.** In an agent, what happens between the user's message and the final output varies (LLM-written sub-queries, tools, sub-agents), but the start and the end are known to your code. Mark them with the same `record_query`: wrap one user turn, pass the user's own words (not the prompt built around them) and record the final output. Every search traced with `@retriever` during the turn counts as its context, and NeuroLinker scores the turn's question, its retrieved documents and its answer:

```python
with record_query(user_input=user_message) as q:
    final_text = await run_agent(prompt_with_session_context)
    q.set_response(final_text)
```

The query span is the root of its trace, so the turn is scored as one query wherever your code opens it, also inside a request your APM traces.

**Searches in another service.** When the searches run in another process, such as an MCP server the agent calls, carry the trace across: send `q.trace_headers()` with the calls, and wrap the work of each incoming request in `continue_trace(headers)` on the other side. Both processes call `instrument()` with the **same track**.

```python
# Agent side: every call to the search service carries the query's trace.
with record_query(user_input=user_message) as q:
    async with httpx.AsyncClient(headers=q.trace_headers()) as http:
        ...

# Service side: the searches join the caller's query.
from neurolinker_sdk import continue_trace

with continue_trace(request.headers):
    results = vector_search(query)
```

The header is `neurolinker-traceparent` (W3C trace-context format), separate from the standard `traceparent` so it never mixes with your app's own tracing. Without it, `continue_trace` does nothing and each search is a trace of its own, scored on its own. If the caller's query never reaches the track, its searches are never scored, so send the header only from a process that tracks.

**Test your instrumentation.** `capture_spans()` records NeuroLinker spans in memory instead of sending them:

```python
from neurolinker_sdk.evaluation.tracking import capture_spans

with capture_spans() as spans:
    vector_search("calibration interval")
(span,) = spans.get_finished_spans()
assert span.attributes["input.value"] == "calibration interval"
```

**Searches your framework does not trace (`@retriever`).** Every search is also scored on its own: the query against the documents it returned (`context_relevance` for the set, plus a relevance per document). Framework retrievers (LangChain, LlamaIndex, ...) emit these spans automatically. When your code calls the vector DB directly, or the search runs in a separate service such as an MCP server, decorate the function that runs it, in the process that runs it:

```python
from neurolinker_sdk import RetrievedDocument, instrument, retriever

instrument(track_uid="<track_uid>", manual=True)   # once, in THIS process

@retriever(to_documents=lambda hits: [
    RetrievedDocument(content=h["entity"]["text"], id=h["id"], score=h["distance"])
    for h in hits[0]
])
def vector_search(query: str, top_k: int = 10):
    return milvus.search("manuals", data=[embed(query)], limit=top_k, output_fields=["text"])
```

- `to_documents` maps your search result to strings or `RetrievedDocument`s; without it, the function must already return strings. Your function's return value is passed through unchanged, and tracing never breaks the search.
- The query is the parameter named `query`, else the first one; pass `query_arg="..."` otherwise.
- Works on sync and async functions. Standalone, each call is its own trace (scored as a search). Inside `record_query(...)`, or inside `continue_trace(...)` in a service the query called, the span is also that query's context.
- No trace-context propagation is needed for search scores: the span carries both the query and the documents. Propagation only adds the search to its query's contexts.

Tell NeuroLinker how to read the result, and attach the context of the call:

```python
@retriever(
    ranked=True,                                     # order = relevance: scores hit@1, MRR, nDCG
    metadata=lambda args: {"filter_expression": args["filter_expression"]},
    to_documents=to_docs,
)
def vector_search(query: str, filter_expression: str | None = None): ...

@retriever(ranked=False, to_documents=to_docs)      # filter-only lookup: scored as a set
def lookup(query: str | None = None, filter_expression: str = ""): ...
```

- `ranked`: does the order of the documents reflect relevance to the query? `True` for vector, keyword, hybrid or reranked search; `False` for filter-only lookups or results ordered by anything else (date, price). Left out, NeuroLinker infers it from the document scores. Ranking metrics are only computed for ranked searches.
- `metadata`: a dict, or a function of the call's arguments by parameter name, recorded as the span's OpenInference `metadata` (JSON). Use it for the filter expression, the collection, `top_k`.
- A call whose query is `None` is still recorded (document count, latency, metadata) but not judged: there is no question to judge the documents against.
- `max_documents` (default `50`) caps the documents recorded on the span; the true count is always sent. The SDK also never records more than fit in the span's attribute limit (OpenTelemetry's `OTEL_SPAN_ATTRIBUTE_COUNT_LIMIT`, default `128`, about 40 documents with id and score): past it, OpenTelemetry would evict the span's kind and query, and the search would silently vanish. It warns when the limit cuts the list; raise the limit to record more.

**Scope.** A track scores both levels by default (`scope="queries_and_retrievals"`). An agent that wraps its turns in `record_query` scores like any RAG. For a system whose root span is not a question and answer and that does not mark one, such as an automation that searches a knowledge base along the way, score searches only: `tracks.create(name=..., scope="retrievals_only")` or `tracks.set_scope(track_uid, scope="retrievals_only")`.

**Read the dashboard.**

- `client.evaluation.tracking.tracks.create(name=..., scope=...)` / `.list()` / `.set_active(track_uid, active=...)` / `.set_scope(track_uid, scope=...)`
Manage tracks. A disabled track stops accepting traces; its history stays readable.

- `client.evaluation.tracking.queries(track_uid, limit=100)`
The per-query rows a track has accumulated (input/output, metrics, latency), most recent first.

- `client.evaluation.tracking.query(track_uid, trace_id)`
Drill-down for one query — adds the retrieved contexts, model and token counts.

- `client.evaluation.tracking.retrievals(track_uid, limit=100)` / `.retrieval(track_uid, span_id)`
The per-search rows (query, document count, `ranked`, `k`, metadata, latency, and the metrics: `context_relevance` and `relevant_document_ratio` for every judged search, plus `hit_at_1`, `reciprocal_rank` and `ndcg` for ranked ones), most recent first; the drill-down adds each judged document with its position and relevance. A ranked search is judged on its top `k` documents, an unranked one on a random sample of `k`.

```python
with NeuroLinker.from_env() as client:
    for row in client.evaluation.tracking.queries(track_uid)["queries"]:
        print(row["user_input"], row["metrics"])
```

## End-to-end pipeline

The ingestion modules compose end to end — the client manually sequences each step; there is no automatic orchestrator. (Evaluation sits outside this chain: batch scoring via `oneshot`, plus continuous tracking of a live RAG.)

```python
from neurolinker_sdk import NeuroLinker, extract_request_uid, extract_document_ids
from neurolinker_sdk.chunking import RecursiveConfig
from neurolinker_sdk.embedding import Content, EmbeddingVector
from neurolinker_sdk.vector_store import CollectionSchema, FieldDef, FieldMapping, VectorDBConfig

with NeuroLinker.from_env() as client:
    # 1. Extract a PDF
    submit = client.extraction.extract(urls=["https://arxiv.org/pdf/2301.07041"])
    request_uid = extract_request_uid(submit)
    status = client.extraction.wait_for_request(request_uid)
    doc_uids = extract_document_ids(status)

    # 2. Create a bucket and attach the extracted documents
    bucket_uid = client.management.buckets.create(name="my-bucket")["bucket_uid"]
    client.management.buckets.add_sources(
        bucket_uid,
        sources=[{"request_uid": request_uid, "doc_uids": doc_uids}],
    )

    # 3. Chunk
    chunk_job = client.chunking.jobs.create(
        bucket_uid=bucket_uid,
        chunking=RecursiveConfig(chunk_size=512, chunk_overlap=64),
    )
    client.chunking.jobs.wait(bucket_uid, chunk_job["job_uid"])

    # 4. Embed with an internal model (no key required)
    models = client.embedding.list_models()
    model = next(m for m in models["models"] if "dense" in (m.get("vector_types") or []))
    embed_job = client.embedding.jobs.create(
        bucket_uid=bucket_uid,
        embeddings=[
            Content(
                content_type="text",
                inputs=["content"],
                vectors=[
                    EmbeddingVector(
                        vector_type="dense",
                        field_name="text_dense",
                        model_name=model["name"],
                    ),
                ],
            )
        ],
    )
    client.embedding.jobs.wait(bucket_uid, embed_job["job_uid"])

    # 5. Create a collection and load the embeddings
    vdb = VectorDBConfig(uri="https://your-cluster-uri", api_key="<your-vector-db-token>")
    client.vector_store.collections.create(
        collection=CollectionSchema(
            name="my_collection",
            fields=[
                FieldDef(name="chunk_id",   dtype="text", is_primary=True),
                FieldDef(name="content",    dtype="text"),
                FieldDef(name="text_dense", dtype="dense_vector", dim=1024),
            ],
        ),
        vector_db_config=vdb,
    )
    load_job = client.vector_store.jobs.create(
        bucket_uid=bucket_uid,
        collection_name="my_collection",
        field_mappings=[
            FieldMapping(name="chunk_id",   source="item_id"),
            FieldMapping(name="content",    source="item_content"),
            FieldMapping(name="text_dense", source="text_dense"),
        ],
        vector_db_config=vdb,
    )
    client.vector_store.jobs.wait(bucket_uid, load_job["job_uid"])
```

The same flow works with `AsyncNeuroLinker` — wrap everything in `async with AsyncNeuroLinker.from_env() as client:` and prefix every call with `await`. Useful inside FastAPI endpoints or async workers.

## Error handling

The SDK raises two exception types, both importable from `neurolinker_sdk`:

- **`NeuroLinkerAPIError`** — non-2xx response from the API. Carries `status_code`, `method`, `url`, `response_text`, `response_json`.
- **`NeuroLinkerConfigError`** — client-side validation failure (missing config, invalid argument, schema validation).

## Support

- **Platform documentation** (pricing, quotas, account management): https://neurolinker.ainexxo.com/docs/
- **API key & dashboard**: https://neurolinker.ainexxo.com (login → API KEY section)
- **Bug reports & feature requests**: open an issue on the SDK repository.

## License

Released under the MIT License — see the [`LICENSE`](./LICENSE) file at the project root.
