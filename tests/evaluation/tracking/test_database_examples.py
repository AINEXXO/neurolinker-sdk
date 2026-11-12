"""Offline response contracts and a real embedded Qdrant search-to-span test."""

import json
from contextlib import closing
from unittest.mock import create_autospec

import pytest

from examples.retriever_databases import pinecone_search, qdrant_search
from neurolinker_sdk import record_query

qdrant = pytest.importorskip("qdrant_client")
pinecone = pytest.importorskip("pinecone")
from pinecone.db_data import Index  # noqa: E402

# qdrant_client.models.QueryResponse is the FastEmbed response, not query_points'.
from qdrant_client.http.models import (  # noqa: E402
    Distance,
    FieldCondition,
    Filter,
    MatchValue,
    PointStruct,
    QueryResponse,
    ScoredPoint,
    VectorParams,
)


@pytest.fixture(params=["qdrant", "pinecone"])
def database(request):
    """Build real provider responses and signature-checked client doubles."""
    provider = request.param
    if provider == "qdrant":
        client = create_autospec(qdrant.QdrantClient, instance=True)
        call = client.query_points
        search = qdrant_search(client, "manuals", text_field="body", vector_name="dense")
        response = QueryResponse(points=[
            ScoredPoint(id=1, version=1, score=0.9, payload={"body": "calibrate yearly"}),
            ScoredPoint(id=2, version=1, score=0.4, payload={"body": "other text"}),
        ])
    else:
        client = create_autospec(Index, instance=True)
        call = client.query
        search = pinecone_search(client, namespace="manuals", text_field="body")
        response = pinecone.QueryResponse(matches=[
            pinecone.ScoredVector(id="1", score=0.9, metadata={"body": "calibrate yearly"}),
            pinecone.ScoredVector(id="2", score=0.4, metadata={"body": "other text"}),
        ], namespace="manuals")
    call.return_value = response
    return provider, call, search, response


def test_provider_contract_and_query_text(database, exporter):
    """Trace text, ids, scores and order while returning the original response."""
    provider, call, search, response = database
    result = search(query="calibration interval?", vector=[0.1, 0.2], top_k=2)
    assert result is response
    if provider == "qdrant":
        call.assert_called_once_with(
            collection_name="manuals", query=[0.1, 0.2], using="dense",
            query_filter=None, limit=2, with_payload=True, with_vectors=False,
        )
    else:
        call.assert_called_once_with(
            vector=[0.1, 0.2], top_k=2, namespace="manuals", filter=None,
            include_metadata=True, include_values=False,
        )
    span, = exporter.get_finished_spans()
    attrs = span.attributes
    assert span.name == f"{provider}.vector_search"
    assert attrs["openinference.span.kind"] == "RETRIEVER"
    assert attrs["input.value"] == "calibration interval?"
    assert attrs["neurolinker.retrieval.search_type"] == "vector"
    assert attrs["neurolinker.retrieval.ranked"] is True
    assert attrs["neurolinker.retrieval.document_count"] == 2
    for i, text in enumerate(["calibrate yearly", "other text"]):
        assert attrs[f"retrieval.documents.{i}.document.content"] == text
        assert attrs[f"retrieval.documents.{i}.document.id"] == str(i + 1)
        assert attrs[f"retrieval.documents.{i}.document.score"] == [0.9, 0.4][i]
    assert json.loads(attrs["metadata"])["database"] == provider


def test_metadata_filtered_vector_search_is_still_ranked(database, exporter):
    """A scalar constraint on a vector query does not make it filter-only."""
    provider, call, search, _ = database
    if provider == "qdrant":
        constraint = Filter(must=[FieldCondition(key="kind", match=MatchValue(value="manual"))])
        kwargs = {"query_filter": constraint}
        wire_key = "query_filter"
    else:
        constraint = {"kind": {"$eq": "manual"}}
        kwargs = {"metadata_filter": constraint}
        wire_key = "filter"
    search("interval?", [0.1, 0.2], **kwargs)
    assert call.call_args.kwargs[wire_key] is constraint
    attrs = exporter.get_finished_spans()[0].attributes
    assert attrs["neurolinker.retrieval.search_type"] == "vector"
    assert attrs["neurolinker.retrieval.ranked"] is True
    assert json.loads(attrs["metadata"])["filter"]


def test_empty_response(database, exporter):
    """An empty search is recorded with zero documents, not lost."""
    provider, call, search, _ = database
    response = (
        QueryResponse(points=[]) if provider == "qdrant"
        else pinecone.QueryResponse(matches=[], namespace="manuals")
    )
    call.return_value = response
    assert search("unknown", [0.1, 0.2]) is response
    attrs = exporter.get_finished_spans()[0].attributes
    assert attrs["neurolinker.retrieval.document_count"] == 0
    assert not any(key.startswith("retrieval.documents.") for key in attrs)


@pytest.mark.parametrize("fields", [None, {}, {"body": 123}])
def test_missing_text_warns_without_breaking_search(database, exporter, fields):
    """Bad payload mappings remain observable rather than inventing text."""
    provider, _, search, response = database
    if provider == "qdrant":
        response.points[0].payload = fields
    elif fields is None:
        response.matches[0] = pinecone.ScoredVector(id="1", score=0.9)
    else:
        response.matches[0].metadata = fields
    with pytest.warns(UserWarning, match="could not read documents"):
        assert search("interval?", [0.1, 0.2]) is response
    attrs = exporter.get_finished_spans()[0].attributes
    assert attrs["openinference.span.kind"] == "RETRIEVER"
    assert not any(key.startswith("retrieval.documents.") for key in attrs)


def test_database_failure_is_reraised_and_traced(database, exporter):
    """The wrapper preserves database failure semantics."""
    _, call, search, _ = database
    call.side_effect = TimeoutError("database unavailable")
    with pytest.raises(TimeoutError, match="database unavailable"):
        search("interval?", [0.1, 0.2])
    span, = exporter.get_finished_spans()
    assert span.status.status_code.name == "ERROR"


def test_search_joins_record_query(database, exporter):
    """The real decorator links database evidence to its parent turn."""
    _, _, search, _ = database
    with record_query(user_input="How often should I calibrate?") as turn:
        search("calibration interval?", [0.1, 0.2])
        turn.set_response("Yearly")
    child, root = exporter.get_finished_spans()
    assert child.parent.span_id == root.context.span_id
    assert child.context.trace_id == root.context.trace_id


def test_embedded_qdrant_search_to_spans(exporter):
    """Execute real filtered similarity search and trace the returned evidence.

    Fixed vectors make ranking deterministic without an embedding model. A
    closer excluded record ensures the filter is applied by Qdrant itself.
    """
    with closing(qdrant.QdrantClient(":memory:")) as client:
        client.create_collection(
            collection_name="retriever_contract",
            vectors_config={"dense": VectorParams(size=2, distance=Distance.COSINE)},
        )
        client.upsert(
            collection_name="retriever_contract",
            points=[
                PointStruct(id=1, vector={"dense": [0.8, 0.6]}, payload={
                    "body": "Calibrate the sensor yearly.", "kind": "manual",
                }),
                PointStruct(id=2, vector={"dense": [0.0, 1.0]}, payload={
                    "body": "Store the sensor in a dry place.", "kind": "manual",
                }),
                PointStruct(id=3, vector={"dense": [1.0, 0.0]}, payload={
                    "body": "Internal calibration draft.", "kind": "draft",
                }),
            ],
            wait=True,
        )
        search = qdrant_search(
            client, "retriever_contract", text_field="body", vector_name="dense",
        )
        constraint = Filter(must=[
            FieldCondition(key="kind", match=MatchValue(value="manual")),
        ])
        with record_query(user_input="How often should I calibrate the sensor?") as turn:
            response = search("sensor calibration interval", [1.0, 0.0],
                              top_k=3, query_filter=constraint)
            turn.set_response("Yearly.")

    assert isinstance(response, QueryResponse)
    assert [point.id for point in response.points] == [1, 2]
    assert [point.score for point in response.points] == pytest.approx([0.8, 0.0])
    child, root = exporter.get_finished_spans()
    assert child.parent.span_id == root.context.span_id
    assert child.context.trace_id == root.context.trace_id
    attrs = child.attributes
    assert attrs["openinference.span.kind"] == "RETRIEVER"
    assert attrs["input.value"] == "sensor calibration interval"
    assert attrs["neurolinker.retrieval.search_type"] == "vector"
    assert attrs["neurolinker.retrieval.ranked"] is True
    assert attrs["neurolinker.retrieval.document_count"] == 2
    for i, point in enumerate(response.points):
        assert attrs[f"retrieval.documents.{i}.document.content"] == point.payload["body"]
        assert attrs[f"retrieval.documents.{i}.document.id"] == str(point.id)
        assert attrs[f"retrieval.documents.{i}.document.score"] == point.score
    assert json.loads(attrs["metadata"])["filter"] == constraint.model_dump(
        mode="json", exclude_none=True,
    )
