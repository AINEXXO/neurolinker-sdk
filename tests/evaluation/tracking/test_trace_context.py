from __future__ import annotations

import warnings

import pytest

from neurolinker_sdk import continue_trace, record_query, retriever
from neurolinker_sdk.evaluation.tracking import _tracing

pytest.importorskip("opentelemetry.sdk")
pytest.importorskip("openinference.semconv")


@pytest.fixture()
def app_tracer():
    """A tracer of the application's own provider (e.g. its APM), with its exporter."""
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import SimpleSpanProcessor
    from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

    exp = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exp))
    return provider.get_tracer("app"), exp


@retriever
def search(query):
    return ["doc"]


@retriever
def embedding_search(query):
    _instrumentor().start_span("embed").end()
    return ["doc"]


def _instrumentor():
    """A tracer as an OpenInference instrumentor activated by instrument() gets it."""
    return _tracing.provider().get_tracer("openinference.instrumentation.x")


def _by_name(exp):
    return {s.name: s for s in exp.get_finished_spans()}


def test_query_under_an_app_span_starts_its_own_trace(exporter, app_tracer) -> None:
    tracer, app_exporter = app_tracer
    with tracer.start_as_current_span("http.request") as request_span:
        with record_query(user_input="Q?") as q:
            search("Q?")
            q.set_response("A.")

    spans = _by_name(exporter)
    query = spans["rag.query"]
    assert query.parent is None
    assert query.context.trace_id != request_span.get_span_context().trace_id
    assert spans["search"].parent.span_id == query.context.span_id
    # Each side only gets its own spans.
    assert "http.request" not in spans
    assert [s.name for s in app_exporter.get_finished_spans()] == ["http.request"]


def test_search_under_an_app_span_starts_its_own_trace(exporter, app_tracer) -> None:
    tracer, _ = app_tracer
    with tracer.start_as_current_span("http.request"):
        search("q")

    assert _by_name(exporter)["search"].parent is None


def test_app_spans_inside_a_query_keep_their_own_parent(exporter, app_tracer) -> None:
    tracer, app_exporter = app_tracer
    with tracer.start_as_current_span("http.request") as request_span:
        with record_query(user_input="Q?") as q:
            with tracer.start_as_current_span("redis.get"):
                search("Q?")
            q.set_response("A.")

    redis_get = _by_name(app_exporter)["redis.get"]
    assert redis_get.parent.span_id == request_span.get_span_context().span_id
    assert redis_get.context.trace_id == request_span.get_span_context().trace_id
    spans = _by_name(exporter)
    assert spans["search"].parent.span_id == spans["rag.query"].context.span_id


def test_search_nests_under_an_instrumentor_span(exporter) -> None:
    with _instrumentor().start_as_current_span("chain") as chain:
        search("q")

    assert _by_name(exporter)["search"].parent.span_id == chain.get_span_context().span_id


def test_instrumentor_spans_under_an_app_span_start_their_own_trace(exporter, app_tracer) -> None:
    tracer, _ = app_tracer
    with tracer.start_as_current_span("http.request"):
        with _instrumentor().start_as_current_span("chain"):
            pass
        _instrumentor().start_span("llm").end()

    spans = _by_name(exporter)
    assert spans["chain"].parent is None
    assert spans["llm"].parent is None


def test_instrumentor_spans_nest_under_the_query_and_app_spans_skip_them(
    exporter, app_tracer
) -> None:
    tracer, app_exporter = app_tracer
    with tracer.start_as_current_span("http.request") as request_span:
        with record_query(user_input="Q?"):
            with _instrumentor().start_as_current_span("llm"):
                with tracer.start_as_current_span("httpx.post"):
                    pass

    spans = _by_name(exporter)
    assert spans["llm"].parent.span_id == spans["rag.query"].context.span_id
    httpx_post = _by_name(app_exporter)["httpx.post"]
    assert httpx_post.parent.span_id == request_span.get_span_context().span_id


def test_spans_nest_under_the_innermost_neurolinker_span(exporter) -> None:
    """Also when an instrumentor makes its span OpenTelemetry's current span itself,
    as OpenInference's OITracer does."""
    from opentelemetry import trace

    with record_query(user_input="Q?"):
        with trace.use_span(_instrumentor().start_span("agent"), end_on_exit=True):
            embedding_search("q")

    spans = _by_name(exporter)
    assert spans["agent"].parent.span_id == spans["rag.query"].context.span_id
    assert spans["embedding_search"].parent.span_id == spans["agent"].context.span_id
    assert spans["embed"].parent.span_id == spans["embedding_search"].context.span_id


def test_continue_trace_joins_the_callers_query(exporter, app_tracer) -> None:
    tracer, _ = app_tracer
    with record_query(user_input="Q?") as q:
        headers = q.trace_headers()
        q.set_response("A.")

    # The called service: its own request span is current, the header carries the query.
    incoming = {"Neurolinker-Traceparent": headers["neurolinker-traceparent"], "Accept": "*/*"}
    with tracer.start_as_current_span("mcp.request"):
        with continue_trace(incoming):
            search("sub-question")

    spans = _by_name(exporter)
    query, child = spans["rag.query"], spans["search"]
    assert child.context.trace_id == query.context.trace_id
    assert child.parent.span_id == query.context.span_id
    assert child.parent.is_remote


def test_app_spans_inside_a_continued_trace_keep_their_own_parent(exporter, app_tracer) -> None:
    tracer, app_exporter = app_tracer
    with record_query(user_input="Q?") as q:
        headers = q.trace_headers()
    with tracer.start_as_current_span("mcp.request") as request_span:
        with continue_trace(headers):
            with tracer.start_as_current_span("milvus.call"):
                search("q")

    milvus_call = _by_name(app_exporter)["milvus.call"]
    assert milvus_call.parent.span_id == request_span.get_span_context().span_id
    spans = _by_name(exporter)
    assert spans["search"].context.trace_id == spans["rag.query"].context.trace_id


@pytest.mark.parametrize("headers", [None, {}, {"neurolinker-traceparent": "garbage"}])
def test_continue_trace_without_a_valid_header_changes_nothing(exporter, headers) -> None:
    with continue_trace(headers):
        search("q")

    assert _by_name(exporter)["search"].parent is None


def test_continue_trace_ignores_the_w3c_traceparent(exporter, app_tracer) -> None:
    tracer, _ = app_tracer
    with tracer.start_as_current_span("caller") as caller:
        traceparent = "00-{:032x}-{:016x}-01".format(
            caller.get_span_context().trace_id, caller.get_span_context().span_id
        )
    with continue_trace({"traceparent": traceparent}):
        search("q")

    assert _by_name(exporter)["search"].parent is None


def test_continue_trace_ends_with_its_block(exporter) -> None:
    with record_query(user_input="Q?") as q:
        headers = q.trace_headers()
    with continue_trace(headers):
        pass
    search("q")

    assert _by_name(exporter)["search"].parent is None


def test_without_instrument_spans_are_dropped_with_one_warning() -> None:
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        with record_query(user_input="Q?") as q:
            assert q.trace_headers() == {}
            search("q")
            search("q")
    assert sum("instrument(...) was not called" in str(w.message) for w in caught) == 1
