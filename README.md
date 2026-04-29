# neurolinker-sdk

NeuroLinker is a document intelligence API by Ainexxo S.R.L. that automates the full ingestion pipeline for RAG applications — from PDF extraction to vector-store loading. This SDK provides sync and async Python clients for the complete pipeline: extraction (full and field-based), bucket management, chunking, embedding, and vector-store loading.

## Table of contents

- [Installation](#installation)
- [Quick start](#quick-start)
- [Client](#client)
- [Extraction](#extraction)
- [Management](#management)
- [Bringing your own keys (BYOK)](#bringing-your-own-keys-byok)
- [Chunking](#chunking)
- [Embedding](#embedding)
- [Vector Store](#vector-store)
- [End-to-end pipeline](#end-to-end-pipeline)
- [Error handling](#error-handling)

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

Or store it in a `.env` file — `NeuroLinker.from_env()` picks it up automatically.

**Sync**

```python
from neurolinker_sdk import NeuroLinker

with NeuroLinker(token="nl_****") as client:
    tasks = client.extraction.list_tasks()

# with .env
with NeuroLinker.from_env() as client:
    tasks = client.extraction.list_tasks()
```

**Async**

```python
from neurolinker_sdk import AsyncNeuroLinker

async with AsyncNeuroLinker(token="nl_****") as client:
    tasks = await client.extraction.list_tasks()

# with .env
async with AsyncNeuroLinker.from_env() as client:
    tasks = await client.extraction.list_tasks()
```

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

Async equivalents exist for every method — same parameters, prefix calls with `await`.

> Every long-running operation exposes a polling helper (`wait_for_request` for extraction, `jobs.wait` for chunking / embedding / vector_store) so you don't have to roll your own poll loop. Polling tolerates transient `404` responses during early job creation.

## Extraction

PDF processing — full extraction or schema-based field extraction.

- `client.extraction.extract(documents=[("file.pdf", b"...")], urls=None, alias=None, description=None)`
Submit a full-extraction job from local PDFs. `documents` and `urls` are mutually exclusive.

- `client.extraction.extract(documents=None, urls=["https://..."], alias="optional", description="optional")`
Submit a full-extraction job from PDF URLs.

- `client.extraction.extract_fields(json_schema={...}, documents=None, urls=[...], alias=None, description=None)`
Submit a field-extraction job. `json_schema` is required and must follow JSON Schema Draft 7 (supported subset). Same documents-or-urls rule as `extract`. Example:

```python
client.extraction.extract_fields(
    json_schema={
        "type": "object",
        "properties": {
            "invoice_number": {"type": "string"},
            "issue_date":     {"type": "string", "format": "date"},
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

- `from neurolinker_sdk import ContentType, SummaryType`
Enums for content-type filtering (`TEXT`, `FORMULA`, `TABLES`, `IMAGES`) and summary type (`PAGE`, `SECTION`).

### Extraction helpers

Two convenience functions are exported from the top-level package to extract UIDs from API responses without inspecting the response shape manually:

- `extract_request_uid(extract_response)` — returns the `request_uid` string from the response returned by `extract()` or `extract_fields()`.
- `extract_document_ids(status_response)` — returns the list of `document_id` strings from the response returned by `wait_for_request()`.

```python
from neurolinker_sdk import NeuroLinker, extract_request_uid, extract_document_ids

with NeuroLinker.from_env() as client:
    submit = client.extraction.extract(urls=["https://arxiv.org/pdf/2301.07041"])
    request_uid = extract_request_uid(submit)
    status = client.extraction.wait_for_request(request_uid)
    doc_uids = extract_document_ids(status)
```

## Management

Bucket and secret CRUD. Buckets are the only entry point for the post-extraction modules — chunking, embedding and vector-store jobs all read from a `bucket_uid`, never from raw extraction request UIDs.

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

> Secret values are redacted from any error response before being raised, so the value never appears in `NeuroLinkerAPIError` text or JSON.

## Bringing your own keys (BYOK)

Some modules call **third-party services on your behalf** and need the corresponding credential:

| Module | When you need a credential |
|---|---|
| `embedding` | Only if you target an **external provider** (Voyage, Jina, Cohere, …). Internal models returned by `embedding.list_models()` are hosted by Ainexxo and need no key. |
| `vector_store` | Always — the cluster (Milvus, Qdrant, Pinecone) is yours, you supply its connection token. |

Pass the credential via `secret_id`: upload the value once with `secrets.create(...)`, get an opaque id back, and reference it in every job. The actual value never leaves Google Secret Manager; only the id flows through the API. Rotation, audit log and per-tenant isolation come for free.

```python
from neurolinker_sdk import NeuroLinker

with NeuroLinker.from_env() as client:
    # Store each third-party credential once — do this once, then reuse the returned secret_id
    milvus_sid = client.management.secrets.create(
        name="my_milvus_token", value="<your-milvus-token>"
    )["secret_id"]
    voyage_sid = client.management.secrets.create(
        name="my_voyage_key", value="<your-voyage-key>"
    )["secret_id"]
```

Then pass the returned `secret_id` when constructing `VectorDBConfig` (vector store) or `ModelRef` (external embedding provider) — see those sections below.

Internal embedding models need no credential at all.

## Chunking

Async chunking jobs over a bucket.

- `client.chunking.jobs.create(bucket_uid, chunking=...)`
Submit a chunking job. `chunking` accepts a Pydantic config (`SectionGreedyConfig`, `MdHeaderLevelConfig`, `BlockWindowConfig`) or a dict matching the same shape.

- `client.chunking.jobs.get(job_uid)`
Retrieve the current state of a chunking job.

- `client.chunking.jobs.wait(job_uid, timeout_s=None, poll_interval_s=None, poll_max_interval_s=None)`
Poll until terminal status, with the same overrides as `wait_for_request`.

- `client.chunking.analyze(bucket_uid)`
Run statistical analysis on a bucket — returns chunk-size distribution and a base64-encoded plot. Useful for sizing a chunking strategy before running a full job.

- `client.chunking.results(bucket_uid)`
Fetch the chunking output files for a bucket. Returns a `dict[filename, bytes]`. File content transits directly between the client and storage, not through the API server.

- `from neurolinker_sdk.chunking import SectionGreedyConfig, MdHeaderLevelConfig, BlockWindowConfig`
Pydantic configs for the three supported chunking strategies — pick the one that matches your document structure:

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

# (2) Markdown-header-aware: splits at headings up to a given level (1..6).
MdHeaderLevelConfig(chunk_at_level=2)

# (3) Sliding window over blocks with configurable overlap.
BlockWindowConfig(
    t_max=1000,
    overlap_blocks=2,
    overlap_mode="within_budget",  # or "extra_budget"
)
```

Each config is mutually exclusive — `chunk_at_level` only exists on `MdHeaderLevelConfig`, `overlap_*` only on `BlockWindowConfig`. Use `client.chunking.analyze(bucket_uid)` first if unsure: it returns a chunk-size distribution that helps pick `t_min`/`t_max`.

## Embedding

Async embedding jobs over a chunked bucket.

- `client.embedding.jobs.create(bucket_uid, modalities=...)`
Submit an embedding job. `modalities` accepts an `EmbeddingModalities` instance or a dict — selects which modalities to embed (text / image / table) and which dense / sparse vectors to compute per modality.

- `client.embedding.jobs.get(job_uid)`
Retrieve the current state of an embedding job.

- `client.embedding.jobs.wait(job_uid, timeout_s=None, poll_interval_s=None, poll_max_interval_s=None)`
Poll until terminal status.

- `client.embedding.list_models()`
List the embedding models available on the backend.

- `client.embedding.results(bucket_uid)`
Fetch the embedding output files for a bucket. Same shape as `chunking.results`.

- `from neurolinker_sdk.embedding import EmbeddingModalities, TextModality, ImageModality, TableModality, ModalityVectors, VectorConfig, ModelRef`
Pydantic types for the embedding configuration. A job has up to three modalities (`text` / `image` / `table`), each with `dense` and/or `sparse` vectors, each referencing a model and the chunk fields to use as input.

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
- `vector_name` cannot start with `item_` or `chunk_` — those prefixes are reserved for internal fields. The name you pick here is what you reference later as `source` in a `FieldMapping` when loading into a vector store.
- `inputs` is the list of chunk fields to concatenate before embedding. Empty list = backend default for that modality. Available fields per modality:

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

- For external providers (Voyage, Jina, Cohere) add `secret_id=...` on `ModelRef` — see the **Bringing your own keys (BYOK)** section above.

## Vector Store

Vector-database collections and async vector-load jobs. Plug-in architecture supporting Milvus / Qdrant / Pinecone via `VectorDBConfig`.

- `client.vector_store.collections.create(collection={...}, vector_db_config={...}, database="")`
Create a vector-store collection. Idempotent — returns `already_existed=true` if it already exists. `collection` accepts a `CollectionSchema` (or dict). `vector_db_config` is a `VectorDBConfig` (or dict) selecting the backend and its connection details.

- `client.vector_store.jobs.create(bucket_uid, collection_name, field_mappings=[...], vector_db_config=..., database="")`
Submit a vector-load job — reads the embedding output for `bucket_uid` and writes it into `collection_name`. `field_mappings` describes how chunk fields map to collection fields.

- `client.vector_store.jobs.get(job_uid)`
Retrieve the current state of a vector-load job.

- `client.vector_store.jobs.wait(job_uid, timeout_s=None, poll_interval_s=None, poll_max_interval_s=None)`
Poll until terminal status.

- `from neurolinker_sdk.vector_store import FieldDef, CollectionSchema, VectorDBConfig, FieldMapping`
Pydantic types for collection schemas, field definitions and vector-DB config.

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

# How to fill each collection field from the embedded data — three source namespaces:
#   item_*        → fields on each embedding item (item_id, item_content, ...)
#   chunk_*       → fields on the parent chunk (chunk_id, chunk_source_file, ...)
#   <vector_name> → the free name you picked in EmbeddingModalities (e.g. "text_dense")
field_mappings = [
    FieldMapping(name="chunk_id",   source="item_id"),
    FieldMapping(name="content",    source="item_content"),
    FieldMapping(name="text_dense", source="text_dense"),  # matches vector_name above
]

# Vector-DB connection — provider auto-detected from the URI domain.
# secret_id is the value returned by management.secrets.create(...).
vdb = VectorDBConfig(
    uri="https://your-cluster.zilliz.com",  # *.zilliz.com → Milvus, *.qdrant.io → Qdrant, *.pinecone.io → Pinecone
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
    vdb = VectorDBConfig(uri="https://your-cluster.zilliz.com", secret_id=secret_id)
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

The same flow with the async client (e.g. inside a FastAPI endpoint or an async worker):

```python
from neurolinker_sdk import AsyncNeuroLinker, extract_request_uid, extract_document_ids
from neurolinker_sdk.chunking import SectionGreedyConfig
from neurolinker_sdk.embedding import (
    EmbeddingModalities, ModalityVectors, ModelRef, TextModality, VectorConfig,
)
from neurolinker_sdk.vector_store import CollectionSchema, FieldDef, FieldMapping, VectorDBConfig

async def run_pipeline() -> None:
    async with AsyncNeuroLinker.from_env() as client:
        secret_id = (await client.management.secrets.create(
            name="my_vdb_token", value="<your-vdb-token>"
        ))["secret_id"]

        submit = await client.extraction.extract(urls=["https://arxiv.org/pdf/2301.07041"])
        request_uid = extract_request_uid(submit)
        status = await client.extraction.wait_for_request(request_uid)
        doc_uids = extract_document_ids(status)

        bucket_uid = (await client.management.buckets.create(name="my-bucket"))["bucket_uid"]
        await client.management.buckets.add_sources(
            bucket_uid,
            sources=[{"request_uid": request_uid, "doc_uids": doc_uids}],
        )

        chunk_job = await client.chunking.jobs.create(
            bucket_uid=bucket_uid,
            chunking=SectionGreedyConfig(t_min=100, t_max=512),
        )
        await client.chunking.jobs.wait(chunk_job["job_uid"])

        models = await client.embedding.list_models()
        model = next(m for m in models["models"] if "dense" in (m.get("vector_types") or []))
        embed_job = await client.embedding.jobs.create(
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
        await client.embedding.jobs.wait(embed_job["job_uid"])

        vdb = VectorDBConfig(uri="https://your-cluster.zilliz.com", secret_id=secret_id)
        await client.vector_store.collections.create(
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
        load_job = await client.vector_store.jobs.create(
            bucket_uid=bucket_uid,
            collection_name="my_collection",
            field_mappings=[
                FieldMapping(name="chunk_id",   source="item_id"),
                FieldMapping(name="content",    source="item_content"),
                FieldMapping(name="text_dense", source="text_dense"),
            ],
            vector_db_config=vdb,
        )
        await client.vector_store.jobs.wait(load_job["job_uid"])
```

## Error handling

The SDK raises two exception types, both importable from `neurolinker_sdk`:

- `NeuroLinkerAPIError` — raised on any non-2xx response from the API. Carries `status_code`, `method`, `url`, `response_text`, and `response_json` (populated when the response body is valid JSON).

```python
from neurolinker_sdk import NeuroLinker, NeuroLinkerAPIError

with NeuroLinker.from_env() as client:
    try:
        result = client.extraction.extract(urls=["https://example.com/doc.pdf"])
    except NeuroLinkerAPIError as e:
        print(e.status_code)    # e.g. 401
        print(e.method)         # e.g. "POST"
        print(e.url)            # full request URL
        print(e.response_text)  # raw response body
        print(e.response_json)  # parsed JSON or None
```

- `NeuroLinkerConfigError` — raised on misconfiguration (missing token, invalid base URL).

