from __future__ import annotations

import warnings

import pytest

from neurolinker_sdk import NeuroLinkerConfigError, instrument, record_query

# These tests exercise the OpenTelemetry emit path; skip cleanly if the tracking
# extra is not installed in the environment.
pytest.importorskip("opentelemetry")
pytest.importorskip("openinference.semconv")


@pytest.fixture()
def exporter():
    """A fresh in-memory span exporter installed as THE process tracer provider.

    Sets ``_TRACER_PROVIDER`` directly (bypassing OTel's set-once guard) so each
    test gets a clean provider regardless of what other tests configured."""
    import opentelemetry.trace as trace_api
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import SimpleSpanProcessor
    from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

    exp = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exp))
    trace_api._TRACER_PROVIDER = provider
    return exp


def _by_kind(exp):
    return {s.attributes.get("openinference.span.kind"): s for s in exp.get_finished_spans()}


def test_record_query_emits_root_with_input_output(exporter) -> None:
    with record_query(user_input="Where is the Eiffel Tower?") as q:
        q.set_response("In Paris.")

    spans = exporter.get_finished_spans()
    root = [s for s in spans if s.parent is None][0]
    assert root.attributes["openinference.span.kind"] == "CHAIN"
    assert root.attributes["input.value"] == "Where is the Eiffel Tower?"
    assert root.attributes["output.value"] == "In Paris."


def test_set_contexts_emits_retriever_span(exporter) -> None:
    with record_query(user_input="Q?") as q:
        q.set_contexts(["chunk one", "chunk two"])
        q.set_response("A.")

    retr = _by_kind(exporter)["RETRIEVER"]
    assert retr.attributes["retrieval.documents.0.document.content"] == "chunk one"
    assert retr.attributes["retrieval.documents.1.document.content"] == "chunk two"
    # the retriever span nests under the query (root) span
    root = [s for s in exporter.get_finished_spans() if s.parent is None][0]
    assert retr.parent.span_id == root.context.span_id


def test_set_llm_emits_llm_span_with_total(exporter) -> None:
    with record_query(user_input="Q?") as q:
        q.set_response("A.")
        q.set_llm(model="gpt-4o", input_tokens=1200, output_tokens=180)

    llm = _by_kind(exporter)["LLM"]
    assert llm.attributes["llm.model_name"] == "gpt-4o"
    assert llm.attributes["llm.token_count.prompt"] == 1200
    assert llm.attributes["llm.token_count.completion"] == 180
    assert llm.attributes["llm.token_count.total"] == 1380  # auto-computed


def test_record_query_rejects_empty_user_input() -> None:
    with pytest.raises(NeuroLinkerConfigError):
        with record_query(user_input=""):
            pass


def test_instrument_attaches_to_existing_provider_and_is_idempotent(exporter) -> None:
    import opentelemetry.trace as trace_api

    # `_instrumented` is a module global; reach it via the function's globals
    # (the submodule name is shadowed by the re-exported `instrument` function).
    instrument.__globals__["_instrumented"] = False
    existing = trace_api.get_tracer_provider()

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")  # ignore the "no instrumentor" notice
        provider = instrument(track_uid="t", api_key="k", base_url="http://dummy.invalid")

    # Coexistence: we attach to the already-installed provider, never replace it.
    assert provider is existing

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        again = instrument(track_uid="t", api_key="k", base_url="http://dummy.invalid")
    assert again is provider
    assert any("already called" in str(w.message) for w in caught)


def test_manual_flag_silences_no_instrumentor_warning(exporter) -> None:
    """``frameworks=[]`` forces "nothing activated" regardless of what's installed,
    so we can assert the manual flag's effect on the warning deterministically."""
    # manual=True → no "no instrumentor" warning
    instrument.__globals__["_instrumented"] = False
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        instrument(track_uid="t", api_key="k", base_url="http://x", frameworks=[], manual=True)
    assert not any("no OpenInference instrumentor" in str(w.message) for w in caught)

    # manual=False (default) → it DOES warn when nothing is activated
    instrument.__globals__["_instrumented"] = False
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        instrument(track_uid="t", api_key="k", base_url="http://x", frameworks=[], manual=False)
    assert any("no OpenInference instrumentor" in str(w.message) for w in caught)
