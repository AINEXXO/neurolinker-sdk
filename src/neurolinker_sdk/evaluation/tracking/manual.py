from __future__ import annotations

from contextlib import contextmanager
from typing import Any, Iterator, Sequence

from ...errors import NeuroLinkerConfigError
from . import _tracing


class QueryRecorder:
    """Handle yielded by :func:`record_query`. Attach the retrieved contexts, the
    final response and (optionally) LLM observability to the current query so the
    backend can score it."""

    def __init__(self, span: Any, tracer: Any, span_attrs: Any, doc_attrs: Any, kinds: Any):
        self._span = span
        self._tracer = tracer
        self._S = span_attrs
        self._D = doc_attrs
        self._K = kinds

    def _child_context(self) -> Any:
        """Context that parents a child span on the query span.

        Returns:
            The context.
        """
        from opentelemetry import trace

        return trace.set_span_in_context(self._span)

    def set_contexts(self, contexts: Sequence[str]) -> None:
        """Record the retrieved chunks as a RETRIEVER child span — this is what
        unlocks the context metrics (faithfulness, context precision/recall)."""
        S, D, K = self._S, self._D, self._K
        content_key = S.RETRIEVAL_DOCUMENTS + ".{i}." + D.DOCUMENT_CONTENT
        with self._tracer.start_as_current_span("retrieval", context=self._child_context()) as span:
            span.set_attribute(S.OPENINFERENCE_SPAN_KIND, K.RETRIEVER.value)
            for i, content in enumerate(contexts):
                span.set_attribute(content_key.format(i=i), content)

    def set_response(self, response: str) -> None:
        """Record the RAG's final answer (the query span's output)."""
        self._span.set_attribute(self._S.OUTPUT_VALUE, response)

    def set_llm(
        self,
        *,
        model: str | None = None,
        input_tokens: int | None = None,
        output_tokens: int | None = None,
        total_tokens: int | None = None,
    ) -> None:
        """Record LLM observability (model name + token counts) as an LLM child
        span. Optional — it feeds the dashboard's cost view, not the Ragas scores.
        Pass whatever you have; ``total_tokens`` defaults to ``input + output``
        when both are given."""
        if total_tokens is None and input_tokens is not None and output_tokens is not None:
            total_tokens = input_tokens + output_tokens
        S, K = self._S, self._K
        with self._tracer.start_as_current_span("llm", context=self._child_context()) as span:
            span.set_attribute(S.OPENINFERENCE_SPAN_KIND, K.LLM.value)
            if model is not None:
                span.set_attribute(S.LLM_MODEL_NAME, model)
            if input_tokens is not None:
                span.set_attribute(S.LLM_TOKEN_COUNT_PROMPT, input_tokens)
            if output_tokens is not None:
                span.set_attribute(S.LLM_TOKEN_COUNT_COMPLETION, output_tokens)
            if total_tokens is not None:
                span.set_attribute(S.LLM_TOKEN_COUNT_TOTAL, total_tokens)

    def trace_headers(self) -> dict[str, str]:
        """Headers that carry this query's trace to another service.

        Send them with every call to a service that runs part of the query, such
        as an MCP server whose searches use :func:`retriever`; that service wraps
        its work in :func:`continue_trace`. Its searches then count as this
        query's contexts. Both sides must send to the same track.

        Returns:
            ``{"neurolinker-traceparent": ...}``, or an empty dict when tracking
            is off (nothing to continue).
        """
        return _tracing.trace_headers(self._span)


@contextmanager
def record_query(*, user_input: str) -> Iterator[QueryRecorder]:
    """Trace one query: the user's input, the final output, and what was
    retrieved in between.

    Call :func:`instrument` once at startup, then wrap each request::

        with record_query(user_input=question) as q:
            docs = my_retriever(question)
            q.set_contexts([d.text for d in docs])
            resp = my_llm(question, docs)
            q.set_response(resp.text)
            q.set_llm(model="gpt-4o", input_tokens=1200, output_tokens=180)  # optional

    It marks where the query starts and ends, which only the application knows,
    so it works for an agent as well as a plain RAG: wrap one user turn, pass
    the user's own words (not the prompt built around them) and record the
    final output, whatever runs in between. Searches traced with
    :func:`retriever` inside it, in this process or in a service called with
    :meth:`QueryRecorder.trace_headers`, count as its contexts.

    NeuroLinker scores a query from the root span of its trace, so the query
    span never nests under the application's own spans (a request span, for
    example): there it starts a new trace. Spans of OpenInference
    instrumentors activated by :func:`instrument` nest under it; the
    application's own spans opened inside keep their own parent. The same
    context manager works in sync and async code (OpenTelemetry propagates
    context across ``await``).

    Args:
        user_input: The user's question or request, as they wrote it.

    Yields:
        The :class:`QueryRecorder` for the query.

    Raises:
        NeuroLinkerConfigError: ``user_input`` is empty, or the tracking extra is
            not installed.
    """
    if not user_input:
        raise NeuroLinkerConfigError("user_input must be a non-empty string.")
    _tracing.require_otel()
    from openinference.semconv.trace import (
        DocumentAttributes,
        OpenInferenceSpanKindValues,
        SpanAttributes,
    )

    span_attrs, doc_attrs, kinds = SpanAttributes, DocumentAttributes, OpenInferenceSpanKindValues
    tracer = _tracing.tracer("record_query()")
    with tracer.start_as_current_span("rag.query") as span:
        span.set_attribute(span_attrs.OPENINFERENCE_SPAN_KIND, kinds.CHAIN.value)
        span.set_attribute(span_attrs.INPUT_VALUE, user_input)
        yield QueryRecorder(span, tracer, span_attrs, doc_attrs, kinds)
