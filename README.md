# neurolinker-sdk

NeuroLinker is a document intelligence service by Ainexxo S.R.L. that automates the full ingestion pipeline for RAG applications — from PDF extraction to vector-store loading. This SDK is the official Python client for the NeuroLinker API: it provides sync and async clients for the complete pipeline (extraction full and field-based, bucket management, chunking, embedding, and vector-store loading).

## Table of contents

- [Installation](#installation)
- [Quick start](#quick-start)
- [Pipeline overview](#pipeline-overview)
- [Client](#client)
- [Extraction](#extraction)
- [Management](#management)
- [Bringing your own keys (BYOK)](#bringing-your-own-keys-byok)
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

with NeuroLinker(token="nl_****") as client:
    tasks = client.extraction.list_tasks()

# with .env (after load_dotenv())
with NeuroLinker.from_env() as client:
    tasks = client.extraction.list_tasks()
```

**Async**

```python
from neurolinker_sdk import AsyncNeuroLinker

async with AsyncNeuroLinker(token="nl_****") as client:
    tasks = await client.extraction.list_tasks()

# with .env (after load_dotenv())
async with AsyncNeuroLinker.from_env() as client:
    tasks = await client.extraction.list_tasks()
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

- `NeuroLinker(token, base_url=None, timeout_s=600.0, poll_interval_s=2.0, poll_max_interval_s=10.0, http_client=None)`
Sync client. `token` is required; `base_url` defaults to `https://neurolinker.api.ainexxo.com`.

- `AsyncNeuroLinker(token, base_url=None, timeout_s=600.0, poll_interval_s=2.0, poll_max_interval_s=10.0, http_client=None)`
Async client. Same parameters as the sync version.

- `NeuroLinker.from_env(timeout_s=None, poll_interval_s=None, poll_max_interval_s=None)`
Loads `NEUROLINKER_API_KEY` from the environment. Per-call overrides accepted for all timing parameters.

- `AsyncNeuroLinker.from_env(timeout_s=None, poll_interval_s=None, poll_max_interval_s=None)`
Async version of `from_env`.

### Modules

The SDK groups the API into five modules reachable as attributes on the client:

| Module | Purpose |
|---|---|
| `extraction` | PDF extraction — full and field-based |
| `management` | Buckets and secrets CRUD |
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

- `client.extraction.extract(documents=None, urls=None, alias=None, description=None)`
Submit a full-extraction job. Provide **either** `documents=[("file.pdf", b"...")]` (local PDF) **or** `urls=["https://..."]` (PDF URLs). The two are mutually exclusive — exactly one is required.

- `client.extraction.extract_fields(json_schema={...}, documents=None, urls=None, alias=None, description=None)`
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

- `client.extraction.generate_schema(description="...")`
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

CRUD for the two resources that glue the extraction output to the rest of the pipeline.

- **Buckets** are the persistent containers that hold extracted documents for chunking, embedding, and vector-store jobs. Those modules always read from a `bucket_uid`, never from raw extraction request UIDs — create a bucket once, attach extraction outputs to it with `buckets.add_sources`, and reuse it across runs.
- **Secrets** are managed credentials stored in Google Secret Manager. You upload an external API key or vector-DB token once, get back an opaque `secret_id`, and reference that id (instead of the raw value) in every job. See the [BYOK](#bringing-your-own-keys-byok) section for the full flow.

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

- `client.management.secrets.create(name="my-secret", value="...")`
Create a secret in Google Secret Manager. Naming is namespaced server-side as `neurolinker__{user_uid}__{name}`.

- `client.management.secrets.list()`
List secrets owned by the API key.

- `client.management.secrets.update(secret_id, value="...")`
Update an existing secret. Returns `None`.

- `client.management.secrets.delete(secret_id)`
Delete a secret. Returns `None`.


## Bringing your own keys (BYOK)

Some modules call **third-party services on your behalf** and need the corresponding credential:

| Module | When you need a credential |
|---|---|
| `embedding` | Only if you target an **external provider** (Voyage, Jina). Internal models returned by `embedding.list_models()` are hosted by Ainexxo and need no key. |
| `vector_store` | Always — the vector database cluster is yours, you supply its connection token. See [Vector Store](#vector-store) for the list of supported databases. |

Upload the value once with `secrets.create(...)`, get an opaque id back, and reference it in every job via `secret_id`. The actual value never leaves Google Secret Manager — only the id flows through the API. Rotation, audit log and per-tenant isolation come for free.

```python
from neurolinker_sdk import NeuroLinker

with NeuroLinker.from_env() as client:
    # Store each third-party credential once — do this once, then reuse the returned secret_id
    vdb_sid = client.management.secrets.create(
        name="my_vdb_token", value="<your-vector-db-token>"
    )["secret_id"]
    voyage_sid = client.management.secrets.create(
        name="my_voyage_key", value="<your-voyage-key>"
    )["secret_id"]
```

## Chunking

Chunking jobs over a bucket.

- `client.chunking.jobs.create(bucket_uid, chunking=...)`
Submit a chunking job. Pass an instance of one of the three chunking configs — `SectionGreedyConfig`, `MdHeaderLevelConfig`, or `BlockWindowConfig` — described below.

- `client.chunking.jobs.get(job_uid)`
Retrieve the current state of a chunking job.

- `client.chunking.jobs.wait(job_uid, timeout_s=None, poll_interval_s=None, poll_max_interval_s=None)`
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

`inputs` is the list of chunk fields concatenated before being passed to the embedding model. Each field is only valid on the modalities marked below — using a field on the wrong modality is rejected at submit time.

| Field | Text | Image | Table | Description |
|---|:---:|:---:|:---:|---|
| `content` | ✓ | | | Main text content of the chunk |
| `caption` | ✓ | ✓ | ✓ | Figure or table caption |
| `detailed_description` | ✓ | ✓ | ✓ | LLM-generated semantic description |
| `extracted_text` | ✓ | ✓ | | OCR text extracted from the element |
| `data` | ✓ | | ✓ | Table data in key:value format |
| `aliases` | ✓ | ✓ | ✓ | Symbol/abbreviation mappings |
| `header_path` | ✓ | | | Parent header hierarchy leading to this chunk |
| `image_base64` | | ✓ | | Base64-encoded image (required for vision models) |

### Methods

- `client.embedding.jobs.create(bucket_uid, modalities=...)`
Submit an embedding job. Pass an `EmbeddingModalities` instance describing which modalities to embed (text / image / table) and which dense / sparse vectors to compute per modality.

- `client.embedding.jobs.get(job_uid)`
Retrieve the current state of an embedding job.

- `client.embedding.jobs.wait(job_uid, timeout_s=None, poll_interval_s=None, poll_max_interval_s=None)`
Poll until terminal status.

- `client.embedding.list_models()`
List the embedding models available on the backend.

- `client.embedding.results(bucket_uid)`
Fetch the embedding output files for a bucket. Same shape as `chunking.results`.

An `EmbeddingModalities` instance is a nested structure: up to three modalities (`text` / `image` / `table`), each with `dense` and/or `sparse` vectors, each referencing a model and the chunk fields to use as input.

```python
from neurolinker_sdk.embedding import (
    EmbeddingModalities, ImageModality, ModalityVectors, ModelRef,
    TableModality, TextModality, VectorConfig,
)

# Use list_models() to discover available internal models
models = client.embedding.list_models()
model = next(m for m in models["models"] if "dense" in (m.get("vector_types") or []))

# Single text dense embedding using an internal model
modalities = EmbeddingModalities(
    text=TextModality(vectors=ModalityVectors(
        dense=VectorConfig(
            vector_name="text_dense",   # free name — referenced later as source in field_mappings
            model=ModelRef(endpoint=model["endpoint"], model_name=model["name"]),
            inputs=["content"],         # chunk fields to embed; default = ["content"]
        ),
    )),
)

# Alternative: multi-modal — text dense + sparse, image dense, table dense
modalities_multimodal = EmbeddingModalities(
    text=TextModality(vectors=ModalityVectors(
        dense=VectorConfig(
            vector_name="text_dense",
            model=ModelRef(endpoint=model["endpoint"], model_name=model["name"]),
            inputs=["content"],
        ),
        sparse=VectorConfig(
            vector_name="text_sparse",
            model=ModelRef(endpoint=model["endpoint"], model_name=model["name"]),
            inputs=["content"],
        ),
    )),
    image=ImageModality(vectors=ModalityVectors(
        dense=VectorConfig(
            vector_name="image_dense",
            model=ModelRef(endpoint=model["endpoint"], model_name=model["name"]),
            inputs=["caption", "detailed_description"],
        ),
    )),
    table=TableModality(vectors=ModalityVectors(
        dense=VectorConfig(
            vector_name="table_dense",
            model=ModelRef(endpoint=model["endpoint"], model_name=model["name"]),
            inputs=["caption", "detailed_description", "data"],
        ),
    )),
)
```

Conventions worth knowing:
- `vector_name` cannot start with `item_` or `chunk_` — those prefixes are reserved for internal fields. The name you pick is what you reference later as `source` in a `FieldMapping` when loading into a vector store, so keep it stable across runs of the same project.
- For external providers add `secret_id=...` on `ModelRef` — see the [Bringing your own keys (BYOK)](#bringing-your-own-keys-byok) section. **Currently supported external embedding providers**: **Voyage** and **Jina**.

## Vector Store

Bring your own cluster — the SDK upserts your embeddings into a collection on the vector database you specify in `VectorDBConfig`.

**Currently supported vector databases:**

- Milvus / Zilliz
- Qdrant
- Pinecone

You don't pass a `provider` field — the SDK figures it out from the URI of your cluster. Just supply the URI and a `secret_id` referencing the cluster's connection token (uploaded once via `secrets.create`, see [BYOK](#bringing-your-own-keys-byok)).

- `client.vector_store.collections.create(collection={...}, vector_db_config={...}, database="")`
Create a vector-store collection. Idempotent — returns `already_existed=true` if it already exists. `collection` accepts a `CollectionSchema` (or dict). `vector_db_config` is a `VectorDBConfig` (or dict) selecting the backend and its connection details.

- `client.vector_store.jobs.create(bucket_uid, collection_name, field_mappings=[...], vector_db_config=..., database="")`
Submit a vector-load job — reads the embedding output for `bucket_uid` and writes it into `collection_name`. `field_mappings` describes how chunk fields map to collection fields.

- `client.vector_store.jobs.get(job_uid)`
Retrieve the current state of a vector-load job.

- `client.vector_store.jobs.wait(job_uid, timeout_s=None, poll_interval_s=None, poll_max_interval_s=None)`
Poll until terminal status.

Loading embeddings into a vector database needs three pieces: a `CollectionSchema` (the target collection's structure, made of `FieldDef` columns), a `VectorDBConfig` (cluster connection details), and a list of `FieldMapping`s (how to populate the collection columns from the embedded records).

The `source` of a `FieldMapping` references one of three namespaces. The data has two levels:

- **Parent chunk** — produced by the chunking step. Carries the full multimodal content of a section of the document (text plus inline figure/table descriptions). Typically what you feed to the LLM at retrieval time.
- **Embedding items** — derived from the parent, one per modality present in the chunk: a text item with the chunk's text content, one image item per figure (with its caption, image bytes, OCR text…), one table item per table (with its data and description). The vector embeddings live on these items.

For example, a chunk containing 2 figures and 1 table produces 4 items (1 text + 2 image + 1 table). At query time you match against the items' vectors but typically retrieve the parent's `chunk_content` to give the LLM the surrounding context.

| Namespace | When to use as `source` | Examples |
|---|---|---|
| `chunk_*` | Per-chunk fields — typically the **context you feed to the LLM** at retrieval time. | `chunk_id`, `chunk_source_file`, `chunk_content` (full chunk, multimodal), `chunk_header_path`, `chunk_pages` |
| `item_*` | Per-item fields — the row you upsert. | `item_id` (primary key), `item_element_type` (`text` / `image` / `table`) |
| `<vector_name>` | The dense or sparse vector itself. | `text_dense`, `text_sparse` (the name you picked in `EmbeddingModalities`) |

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
| `item_content` | ✓ | | | Text content of the item |
| `item_caption` | | ✓ | ✓ | Caption of the figure or table |
| `item_detailed_description` | | ✓ | ✓ | LLM-generated semantic description |
| `item_extracted_text` | | ✓ | | OCR text from the figure |
| `item_data` | | | ✓ | Table data in key:value format |
| `item_aliases` | | ✓ | ✓ | Symbol/abbreviation mappings |
| `item_url` | | ✓ | | URL of the figure |
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
    FieldMapping(name="text_dense", source="text_dense"),  # matches vector_name above
]

# Vector-DB connection — supply your cluster URI and the managed secret id
# returned by management.secrets.create(...).
vdb = VectorDBConfig(
    uri="https://your-cluster-uri",
    secret_id="<secret_id from secrets.create>",
)

client.vector_store.collections.create(collection=collection, vector_db_config=vdb)
load_job = client.vector_store.jobs.create(
    bucket_uid="<your-bucket-uid>",
    collection_name="my_collection",
    field_mappings=field_mappings,
    vector_db_config=vdb,
)
client.vector_store.jobs.wait(load_job["job_uid"])
```

Supported `dtype` values: `text`, `int`, `float`, `bool`, `json`, `dense_vector` (requires `dim`), `sparse_vector`. Supported `distance` for vectors: `cosine` (default), `dot`, `euclidean`. A collection can have at most one field with `is_primary=True`.

## End-to-end pipeline

The five modules are designed to compose. The client manually sequences each step — there is no automatic orchestrator.

```python
from neurolinker_sdk import NeuroLinker, extract_request_uid, extract_document_ids
from neurolinker_sdk.chunking import SectionGreedyConfig
from neurolinker_sdk.embedding import (
    EmbeddingModalities, ModalityVectors, ModelRef, TextModality, VectorConfig,
)
from neurolinker_sdk.vector_store import CollectionSchema, FieldDef, FieldMapping, VectorDBConfig

with NeuroLinker.from_env() as client:
    # 0. Store the vector-DB credential as a managed secret (see BYOK section above)
    secret_id = client.management.secrets.create(
        name="my_vdb_token", value="<your-vdb-token>"
    )["secret_id"]

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
    client.chunking.jobs.wait(chunk_job["job_uid"])

    # 4. Embed with an internal model (no key required)
    models = client.embedding.list_models()
    model = next(m for m in models["models"] if "dense" in (m.get("vector_types") or []))
    embed_job = client.embedding.jobs.create(
        bucket_uid=bucket_uid,
        modalities=EmbeddingModalities(
            text=TextModality(vectors=ModalityVectors(
                dense=VectorConfig(
                    vector_name="text_dense",
                    model=ModelRef(endpoint=model["endpoint"], model_name=model["name"]),
                    inputs=["content"],
                ),
            )),
        ),
    )
    client.embedding.jobs.wait(embed_job["job_uid"])

    # 5. Create a collection and load the embeddings
    vdb = VectorDBConfig(uri="https://your-cluster-uri", secret_id=secret_id)
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
    client.vector_store.jobs.wait(load_job["job_uid"])
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

