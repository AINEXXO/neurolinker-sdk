"""Test helpers for code instrumented with NeuroLinker tracking."""

from __future__ import annotations

from contextlib import contextmanager
from typing import Any, Iterator

from . import _tracing


@contextmanager
def capture_spans(*, span_limits: Any = None) -> Iterator[Any]:
    """Record NeuroLinker spans in memory instead of sending them.

    For tests of your instrumentation: inside the block, spans from
    :func:`record_query`, :func:`retriever` and instrumentors activated by
    :func:`instrument` go to the returned exporter; afterwards the previous
    setup is back::

        with capture_spans() as spans:
            search("calibration interval")
        (span,) = spans.get_finished_spans()
        assert span.attributes["input.value"] == "calibration interval"

    Args:
        span_limits: Optional OpenTelemetry ``SpanLimits`` for the recording
            provider (e.g. to test the attribute limit).

    Yields:
        An OpenTelemetry ``InMemorySpanExporter`` holding the finished spans.

    Raises:
        NeuroLinkerConfigError: The tracking extra is not installed.
    """
    _tracing.require_otel()
    from opentelemetry.sdk.trace.export import SimpleSpanProcessor
    from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

    exporter = InMemorySpanExporter()
    provider = _tracing.new_provider(span_limits=span_limits)
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    previous = _tracing.swap_provider(provider)
    try:
        yield exporter
    finally:
        _tracing.swap_provider(previous)
        provider.shutdown()
