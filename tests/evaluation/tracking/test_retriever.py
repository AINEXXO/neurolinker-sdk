from __future__ import annotations

import asyncio
import warnings

import pytest

from neurolinker_sdk import (
    NeuroLinkerConfigError,
    RetrievedDocument,
    record_query,
    retriever,
)

pytest.importorskip("opentelemetry")
pytest.importorskip("openinference.semconv")


@pytest.fixture()
def exporter():
    """A fresh in-memory span exporter installed as THE process tracer provider."""
    import opentelemetry.trace as trace_api
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import SimpleSpanProcessor
    from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

    exp = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exp))
    trace_api._TRACER_PROVIDER = provider
    return exp


def _only_span(exp):
    spans = exp.get_finished_spans()
    assert len(spans) == 1
    return spans[0]


def test_emits_retriever_span_with_query_and_documents(exporter) -> None:
    @retriever(to_documents=lambda hits: [h["text"] for h in hits])
    def search(query: str, top_k: int = 2):
        return [{"text": "chunk one"}, {"text": "chunk two"}][:top_k]

    result = search("calibration interval")

    assert result == [{"text": "chunk one"}, {"text": "chunk two"}]  # passed through
    span = _only_span(exporter)
    assert span.name.endswith("search")
    assert span.parent is None                    # standalone: its own trace
    assert span.attributes["openinference.span.kind"] == "RETRIEVER"
    assert span.attributes["input.value"] == "calibration interval"
    assert span.attributes["retrieval.documents.0.document.content"] == "chunk one"
    assert span.attributes["retrieval.documents.1.document.content"] == "chunk two"


def test_documents_carry_id_and_score(exporter) -> None:
    @retriever(to_documents=lambda hits: [
        RetrievedDocument(content=h["text"], id=h["pk"], score=h["distance"]) for h in hits])
    def search(query):
        return [{"text": "a", "pk": 42, "distance": 0.93}]

    search("q")
    attrs = _only_span(exporter).attributes
    assert attrs["retrieval.documents.0.document.id"] == "42"
    assert attrs["retrieval.documents.0.document.score"] == pytest.approx(0.93)


def test_default_returns_strings_directly(exporter) -> None:
    @retriever
    def search(query):
        return ["a", "b"]

    assert search("q") == ["a", "b"]
    attrs = _only_span(exporter).attributes
    assert attrs["retrieval.documents.1.document.content"] == "b"


def test_query_found_by_name_keyword_and_explicit_arg(exporter) -> None:
    class Store:
        @retriever(to_documents=lambda r: [])
        def search(self, collection, query, limit=5):
            return []

    @retriever(query_arg="text", to_documents=lambda r: [])
    def by_text(collection, text):
        return []

    @retriever(to_documents=lambda r: [])
    def first_param(q, limit=5):
        return []

    Store().search("manuals", query="by keyword")
    by_text("manuals", "explicit")
    first_param("first")
    queries = [s.attributes["input.value"] for s in exporter.get_finished_spans()]
    assert queries == ["by keyword", "explicit", "first"]


def test_unknown_query_arg_fails_at_decoration() -> None:
    with pytest.raises(NeuroLinkerConfigError):
        @retriever(query_arg="nope")
        def search(query):
            return []


def test_async_function(exporter) -> None:
    @retriever(to_documents=lambda r: r)
    async def search(query):
        await asyncio.sleep(0)
        return ["async doc"]

    assert asyncio.run(search("q")) == ["async doc"]
    attrs = _only_span(exporter).attributes
    assert attrs["retrieval.documents.0.document.content"] == "async doc"


def test_bad_to_documents_never_breaks_the_search(exporter) -> None:
    @retriever(to_documents=lambda r: r["missing"])
    def search(query):
        return {"hits": []}

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        assert search("q") == {"hits": []}
    assert any("could not read documents" in str(w.message) for w in caught)
    attrs = _only_span(exporter).attributes
    assert attrs["input.value"] == "q"
    assert not any(k.startswith("retrieval.documents") for k in attrs)


def test_search_exception_is_recorded_and_reraised(exporter) -> None:
    @retriever
    def search(query):
        raise RuntimeError("milvus down")

    with pytest.raises(RuntimeError):
        search("q")
    span = _only_span(exporter)
    assert span.status.status_code.name == "ERROR"


def test_nested_in_record_query_counts_as_its_context(exporter) -> None:
    @retriever
    def search(query):
        return ["ctx"]

    with record_query(user_input="Q?") as q:
        search("Q?")
        q.set_response("A.")

    spans = {s.attributes["openinference.span.kind"]: s for s in exporter.get_finished_spans()}
    assert spans["RETRIEVER"].parent.span_id == spans["CHAIN"].context.span_id
