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
from neurolinker_sdk.evaluation.tracking import capture_spans

pytest.importorskip("opentelemetry")
pytest.importorskip("openinference.semconv")


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


def _recorded_contents(attrs) -> list[str]:
    i, contents = 0, []
    while f"retrieval.documents.{i}.document.content" in attrs:
        contents.append(attrs[f"retrieval.documents.{i}.document.content"])
        i += 1
    return contents


def test_ranked_is_recorded_only_when_given(exporter) -> None:
    @retriever(ranked=True)
    def vector(query):
        return ["a"]

    @retriever(ranked=False)
    def lookup(query):
        return ["a"]

    @retriever
    def unknown(query):
        return ["a"]

    vector("q")
    lookup("q")
    unknown("q")
    spans = exporter.get_finished_spans()
    ranked = [s.attributes.get("neurolinker.retrieval.ranked") for s in spans]
    assert ranked == [True, False, None]


def test_metadata_from_mapping_and_from_call_arguments(exporter) -> None:
    import json

    @retriever(metadata={"collection": "manuals"})
    def fixed(query):
        return []

    @retriever(metadata=lambda a: {"filter_expression": a["filter_expression"],
                                    "top_k": a["top_k"]})
    def per_call(query, filter_expression=None, top_k=10):
        return []

    fixed("q")
    per_call("q", filter_expression="product_name LIKE 'PSD%'")
    first, second = exporter.get_finished_spans()
    assert json.loads(first.attributes["metadata"]) == {"collection": "manuals"}
    assert json.loads(second.attributes["metadata"]) == {
        "filter_expression": "product_name LIKE 'PSD%'", "top_k": 10,
    }


def test_bad_metadata_never_breaks_the_search(exporter) -> None:
    @retriever(metadata=lambda a: a["missing"])
    def search(query):
        return ["a"]

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        assert search("q") == ["a"]
    assert any("could not build the metadata" in str(w.message) for w in caught)
    attrs = _only_span(exporter).attributes
    assert "metadata" not in attrs
    assert attrs["retrieval.documents.0.document.content"] == "a"


def test_document_count_is_the_true_total_and_max_documents_caps_recording(exporter) -> None:
    @retriever(max_documents=3)
    def search(query):
        return [f"doc {i}" for i in range(7)]

    assert len(search("q")) == 7                                  # result untouched
    attrs = _only_span(exporter).attributes
    assert attrs["neurolinker.retrieval.document_count"] == 7
    assert _recorded_contents(attrs) == ["doc 0", "doc 1", "doc 2"]


def test_documents_never_evict_the_span_kind_or_query() -> None:
    from opentelemetry.sdk.trace import SpanLimits


    @retriever(ranked=True, to_documents=lambda hits: [
        RetrievedDocument(content=f"doc {i}", id=str(i), score=1.0 - i / 100) for i in hits])
    def limited_search(query):
        return list(range(30))

    with capture_spans(span_limits=SpanLimits(max_span_attributes=20)) as exporter:
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            limited_search("q")
    attrs = _only_span(exporter).attributes
    # kind + input + ranked + count = 4 attributes; 16 left = 5 documents of 3 attributes each
    assert attrs["openinference.span.kind"] == "RETRIEVER"
    assert attrs["input.value"] == "q"
    assert attrs["neurolinker.retrieval.document_count"] == 30
    assert _recorded_contents(attrs) == [f"doc {i}" for i in range(5)]
    assert len(attrs) <= 20
    assert any("fit in the span's attribute limit (20)" in str(w.message) for w in caught)


def test_search_without_a_query_is_still_recorded(exporter) -> None:
    @retriever(ranked=False)
    def lookup(query=None, filter_expression=""):
        return ["row"]

    lookup(filter_expression="document_type == 'datasheet'")
    attrs = _only_span(exporter).attributes
    assert "input.value" not in attrs
    assert attrs["openinference.span.kind"] == "RETRIEVER"
    assert attrs["neurolinker.retrieval.document_count"] == 1


@pytest.mark.parametrize("bad", [-1, 1.5, True, "10"])
def test_invalid_max_documents_fails_at_decoration(bad) -> None:
    with pytest.raises(NeuroLinkerConfigError):
        retriever(max_documents=bad)
