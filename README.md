# neurolinker-sdk

NeuroLinker is a document intelligence service by Ainexxo S.R.L. that automates the full ingestion pipeline for RAG applications — from PDF extraction to vector-store loading. This SDK is the official Python client for the NeuroLinker API: it provides sync and async clients for the complete pipeline (extraction full and field-based, bucket management, chunking, embedding, and vector-store loading).

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
- [End-to-end pipeline](#end-to-end-pipeline)
- [Error handling](#error-handling)
- [Support](#support)
- [License](#license)

## Installation

```bash
pip install neurolinker-sdk
```

Requires Python 3.11+.

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

The five modules are designed to compose end-to-end. A typical RAG ingestion run goes through them in order:

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

The SDK groups the API into five modules reachable as attributes on the client:

| Module | Purpose |
|---|---|
| `extraction` | PDF extraction — full and field-based |
| `management` | Bucket CRUD |
| `chunking` | Chunking jobs |
| `embedding` | Embedding jobs |
| `vector_store` | Vector-store collections and load jobs |

## Extraction

PDF processing — full extraction or schema-based field extraction. The two pipelines are independent: pick one per document depending on what you want as output.

| Method | When to use it | Output |
|---|---|---|
| `extraction.extract(...)` | You want the full document content for downstream pipelines (RAG, search, chunking) | Markdown, structured JSON, per-page images, page/section summaries |
| `extraction.extract_fields(...)` | You only need a structured payload that conforms to a JSON Schema you supply (invoices, forms, contracts) | A JSON object matching your schema, retrievable via `documents.fields(...)` |

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
Submit a chunking job. Pass an instance of one of the three chunking configs — `SectionGreedyConfig`, `MdHeaderLevelConfig`, or `BlockWindowConfig` — described below.

- `client.chunking.jobs.get(bucket_uid, job_uid)`
Retrieve the current state of a chunking job.

- `client.chunking.jobs.wait(bucket_uid, job_uid, timeout_s=None, poll_interval_s=None, poll_max_interval_s=None)`
Poll until terminal status, with the same overrides as `wait_for_request`.

- `client.chunking.analyze(bucket_uid)`
Run statistical analysis on a bucket **after a chunking job has completed** — returns chunk-size distribution and a base64-encoded plot built from the existing output. Useful for inspecting the result of a chunking pass and deciding whether to re-run with adjusted parameters.

- `client.chunking.results(bucket_uid)`
Fetch the chunking output files for a bucket. Returns a `dict[filename, bytes]`. File content transits directly between the client and storage, not through the API server.

### Choosing a chunking strategy

Three strategies are available — pick based on your document structure:

| Strategy | Best for | What it does |
|---|---|---|
| `SectionGreedyConfig` | Well-structured documents (papers, reports, manuals). **Recommended default.** | Respects natural section boundaries and packs each chunk to a token budget (`t_min`–`t_max`) |
| `MdHeaderLevelConfig` | FAQ-style or hierarchical knowledge bases where chunks should map 1:1 to headings | Splits at heading boundaries up to `chunk_at_level` |
| `BlockWindowConfig` | Unstructured or continuous text (transcripts, plain narratives) where natural boundaries don't help | Sliding window over blocks with configurable overlap |


Example configurations:

```python
from neurolinker_sdk.chunking import (
    BlockWindowConfig, MdHeaderLevelConfig, SectionGreedyConfig,
)

# (1) Structure-aware: respects natural sections, packs each chunk to a token budget.
SectionGreedyConfig(
    t_min=200, t_max=1500,                       # token budget per chunk
    model_name="Alibaba-NLP/gte-large-en-v1.5",  # tokenizer used for the budget
    parse_figures=True, parse_tables=True,
    parse_headers=True, parse_footers=False,
)

# (2) Markdown-header-aware: splits at headings up to a given level.
MdHeaderLevelConfig(chunk_at_level=2)

# (3) Sliding window over blocks with configurable overlap.
BlockWindowConfig(
    t_max=1000,
    overlap_blocks=2,
    overlap_mode="within_budget",  # or "extra_budget"
)
```


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
- External LiteLLM models use the LiteLLM `model_name` as-is and carry their own `api_key` directly on each `EmbeddingVector`.

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

## End-to-end pipeline

The five modules are designed to compose. The client manually sequences each step — there is no automatic orchestrator.

```python
from neurolinker_sdk import NeuroLinker, extract_request_uid, extract_document_ids
from neurolinker_sdk.chunking import SectionGreedyConfig
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
        chunking=SectionGreedyConfig(t_min=100, t_max=512),
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

- **Platform documentation** (pricing, quotas, account management): https://neurolinker.ainexxo.com/docs/index.html
- **API key & dashboard**: https://neurolinker.ainexxo.com (login → API KEY section)
- **Bug reports & feature requests**: open an issue on the SDK repository.

## License

Released under the MIT License — see the [`LICENSE`](./LICENSE) file at the project root.
