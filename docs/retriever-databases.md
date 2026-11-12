# Retriever integrations: Qdrant, Pinecone and Milvus/Zilliz

`@retriever` belongs in the client process that performs the search. It records
the human-readable query and maps the database's response to `RetrievedDocument`.
It does not run inside NeuroLinker's vector-load service or depend on a database
field called `query`. The backend evaluates the same OpenInference contract for
all three databases.

```mermaid
sequenceDiagram
    participant App as Customer application
    participant Wrapper as @retriever search wrapper
    participant DB as Qdrant / Pinecone / Milvus
    participant Adapter as to_documents
    participant OTel as NeuroLinker tracer
    participant Eval as NeuroLinker ingest and evaluation
    App->>Wrapper: query text + matching precomputed vector
    Wrapper->>OTel: Start RETRIEVER span (query, type, ranked, metadata)
    Wrapper->>DB: Search vector, request payload/metadata text
    DB-->>Wrapper: Native response (ranked hits)
    Wrapper->>Adapter: Native response
    Adapter-->>Wrapper: RetrievedDocument(content, id, score) list
    Wrapper->>OTel: Record documents and true count; end span
    Wrapper-->>App: Original response unchanged
    alt instrument(track_uid=...) configured
        OTel->>Eval: Export OpenInference span
        Eval->>Eval: Score query against documents
    else offline capture_spans()
        OTel-->>App: In-memory spans for assertions
    end
```

## Executable examples

[`examples/retriever_databases.py`](../examples/retriever_databases.py) provides
`qdrant_search` and `pinecone_search` factories. These are source-checkout examples,
not installed SDK exports. Copy the wrapper into your application or run from
the repository root. The SDK's core remains provider-independent.

| Database | Search API | Conversion | Text must be returned |
| --- | --- | --- | --- |
| Qdrant | `QdrantClient.query_points` | `response.points`: `payload[text_field]`, `id`, `score` | `with_payload=True` |
| Pinecone | synchronous `Index.query` | `response.matches`: `metadata[text_field]`, `id`, `score` | `include_metadata=True` |
| Milvus/Zilliz | `MilvusClient.search` | `hits[0]`: `entity[text_field]`, `id`, `distance` | `output_fields=[text_field]` |

The [README Milvus example](../README.md#tracking-continuous) shows
the reference mapping. DaVinci's Milvus MCP applies the same decorator before
serializing search results; its own record-to-text conversion is application-specific.

These wrappers perform dense vector searches, optionally constrained by metadata.
A vector query with a metadata filter is still `search_type="vector"`,
`ranked=True`. Filter-only Qdrant scrolls or Pinecone id fetches are different
operations: decorate those separately with `search_type="filter"`, `ranked=False`
and, for scoring, run them under `record_query(user_input=...)`. Do not substitute
a zero vector to simulate a filter-only search.

`query_arg="query"` explicitly selects the wrapper's text argument. The database
receives `vector`, not that text. Use the same embedding model, dimension and
normalization as the stored vectors. Choose `text_field` from your actual load
mapping, and Qdrant's `vector_name` from its collection schema. No embedding model
is loaded or called by these examples.

### Setup and offline verification

```bash
uv sync --locked --dev --group retriever-examples
uv run --no-sync python -m pytest tests/evaluation/tracking -q
```

The dependency group installs Qdrant and Pinecone only for examples/tests, not as
runtime SDK dependencies. CI installs this group too. Tests use actual SDK response
models and signature-checked client doubles, with in-memory OpenTelemetry spans.
An additional Qdrant test uses `QdrantClient(":memory:")`: it creates an ephemeral
named-vector collection, inserts three fixed-vector text records, executes real
filtered `query_points` through the wrapper, and verifies ranking, returned text,
ids/scores and parent-linked OTel spans. The closest record is excluded by its
metadata, so the test also verifies actual filter execution. Pinecone search is
mocked; Qdrant's embedded search is real, but its hosted transport is not tested.
Tests perform no network requests, local server startup or inference. Without the group,
the provider tests skip. Tested lockfile versions: Qdrant client 1.20.0 and Pinecone
7.3.0, Python 3.11.

Coverage includes text versus vector binding, ordered content/id/score mapping,
custom text fields, named vectors, namespaces, metadata filters, empty results,
malformed/missing text, unchanged return identity, database exceptions and nesting
under `record_query`. A mapping error warns and leaves the native result intact;
it does not invent blank document text or send partially converted documents.

### Live validation (explicit, potentially billable)

Live database queries and NeuroLinker judge calls require approval before running.
The offline tests prove client-to-span contracts, not hosted connectivity or judge
scores. Live validation (2026-11-12, NeuroLinker dev track, 1,212 GMI product
chunks with their stored BGE-M3 vectors): Qdrant in embedded on-disk mode
(`QdrantClient(path=...)`) and a Pinecone Starter serverless index. Both
wrappers' searches were exported, judged and read back through
`client.evaluation.tracking.retrievals`. A hosted Qdrant server was not tested;
its client API is the same.

Provide an existing non-production collection/index with known text records,
authorized credentials, a query and its matching precomputed embedding. No
collection creation or data writes are needed. Read values from environment
variables; never put keys in source or test output. `query-vector.json` below is
a JSON array of floats generated with the collection's embedding model.

Run either snippet from the checkout root after setup. To inspect spans offline
instead of exporting, replace `instrument(...)` with a `capture_spans()` context
around the search. A real database query still occurs in that case.

Qdrant:

```python
import json
import os
from pathlib import Path

from qdrant_client import QdrantClient
from neurolinker_sdk import instrument
from examples.retriever_databases import qdrant_search

# Also export NEUROLINKER_API_KEY and NEUROLINKER_BASE_URL for the target environment.
provider = instrument(track_uid=os.environ["NEUROLINKER_TRACK_UID"], manual=True)
client = QdrantClient(url=os.environ["QDRANT_URL"], api_key=os.environ["QDRANT_API_KEY"])
try:
    search = qdrant_search(
        client, os.environ["QDRANT_COLLECTION"],
        text_field=os.environ["DOCUMENT_TEXT_FIELD"],
        vector_name=os.environ.get("QDRANT_VECTOR_NAME") or None,
    )
    response = search(
        os.environ["SEARCH_QUERY"], json.loads(Path("query-vector.json").read_text()), top_k=3,
    )
    print(f"Returned {len(response.points)} points")
finally:
    client.close()
    provider.force_flush()
    provider.shutdown()
```

Pinecone:

```python
import json
import os
from pathlib import Path

from pinecone import Pinecone
from neurolinker_sdk import instrument
from examples.retriever_databases import pinecone_search

provider = instrument(track_uid=os.environ["NEUROLINKER_TRACK_UID"], manual=True)
# Explicit index host avoids a control-plane index discovery request.
pc = Pinecone(api_key=os.environ["PINECONE_API_KEY"])
try:
    with pc.Index(host=os.environ["PINECONE_INDEX_HOST"]) as index:
        search = pinecone_search(
            index, namespace=os.environ.get("PINECONE_NAMESPACE", ""),
            text_field=os.environ["DOCUMENT_TEXT_FIELD"],
        )
        response = search(
            os.environ["SEARCH_QUERY"],
            json.loads(Path("query-vector.json").read_text()), top_k=3,
        )
        print(f"Returned {len(response.matches)} matches")
finally:
    provider.force_flush()
    provider.shutdown()
```

Use an active track owned by the configured API identity, with
`scope="retrievals_only"` for standalone searches. After export and async scoring,
inspect `client.evaluation.tracking.retrievals(track_uid)` and the retrieval detail
or the dashboard. Confirm the provider span name, text query, `vector` search type,
ranking, document count and text, then completed relevance metrics. A local span
alone is not evidence that the ingest or judge completed.

## Deployment requirements

The application needs SDK 0.5.0 or later with `[tracking]`, its selected database
client, and the wrapper. Configure `instrument` once in the search process and
flush with `provider.force_flush()` for short-lived scripts. Existing backend retrieval scoring
and a configured judge must be deployed and reachable. These examples introduce
no backend schema or API changes and require no backend deployment themselves.
Publishing the examples requires merging this SDK branch; adopting them in a
customer service requires deploying that service's wrapper/configuration.
