from __future__ import annotations

import warnings
from contextlib import contextmanager
from typing import Any, Iterator, Sequence

from ...errors import NeuroLinkerConfigError

_TRACER_NAME = "neurolinker_sdk"


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

    def set_contexts(self, contexts: Sequence[str]) -> None:
        """Record the retrieved chunks as a RETRIEVER child span — this is what
        unlocks the context metrics (faithfulness, context precision/recall)."""
        S, D, K = self._S, self._D, self._K
        content_key = S.RETRIEVAL_DOCUMENTS + ".{i}." + D.DOCUMENT_CONTENT
        with self._tracer.start_as_current_span("retrieval") as span:
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
        with self._tracer.start_as_current_span("llm") as span:
            span.set_attribute(S.OPENINFERENCE_SPAN_KIND, K.LLM.value)
            if model is not None:
                span.set_attribute(S.LLM_MODEL_NAME, model)
            if input_tokens is not None:
                span.set_attribute(S.LLM_TOKEN_COUNT_PROMPT, input_tokens)
            if output_tokens is not None:
                span.set_attribute(S.LLM_TOKEN_COUNT_COMPLETION, output_tokens)
            if total_tokens is not None:
                span.set_attribute(S.LLM_TOKEN_COUNT_TOTAL, total_tokens)


@contextmanager
def record_query(*, user_input: str) -> Iterator[QueryRecorder]:
    """Manually trace one RAG query when your stack has no auto-instrumentor.

    Call :func:`instrument` once at startup, then wrap each request::

        with record_query(user_input=question) as q:
            docs = my_retriever(question)
            q.set_contexts([d.text for d in docs])
            resp = my_llm(question, docs)
            q.set_response(resp.text)
            q.set_llm(model="gpt-4o", input_tokens=1200, output_tokens=180)  # optional

    Produces exactly the span shape the backend scores: a root query span
    carrying input/output, a RETRIEVER child carrying the contexts, and
    (optionally) an LLM child carrying model/token observability. The same
    context manager works in sync and async code (OpenTelemetry propagates
    context across ``await``).
    """
    if not user_input:
        raise NeuroLinkerConfigError("user_input must be a non-empty string.")
    try:
        from openinference.semconv.trace import (
            DocumentAttributes,
            OpenInferenceSpanKindValues,
            SpanAttributes,
        )
        from opentelemetry import trace
        from opentelemetry.sdk.trace import TracerProvider
    except ImportError as exc:
        raise NeuroLinkerConfigError(
            "Tracking dependencies are not installed. Install the tracking extra: "
            "`pip install neurolinker-sdk[tracking]`."
        ) from exc
    if not isinstance(trace.get_tracer_provider(), TracerProvider):
        warnings.warn(
            "neurolinker: record_query() used but no tracer provider is "
            "configured — call instrument(...) at startup, otherwise this span "
            "is dropped.",
            stacklevel=3,
        )
    span_attrs, doc_attrs, kinds = SpanAttributes, DocumentAttributes, OpenInferenceSpanKindValues
    tracer = trace.get_tracer(_TRACER_NAME)
    with tracer.start_as_current_span("rag.query") as span:
        span.set_attribute(span_attrs.OPENINFERENCE_SPAN_KIND, kinds.CHAIN.value)
        span.set_attribute(span_attrs.INPUT_VALUE, user_input)
        yield QueryRecorder(span, tracer, span_attrs, doc_attrs, kinds)
