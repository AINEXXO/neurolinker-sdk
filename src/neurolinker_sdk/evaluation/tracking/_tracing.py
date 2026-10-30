"""The SDK's own OpenTelemetry pipeline and how its spans join a trace.

NeuroLinker spans go through a private ``TracerProvider`` owned by the SDK, never
through the process-wide one, so an application's own telemetry (HTTP, database,
APM spans) is never sent to NeuroLinker and NeuroLinker spans never land in the
application's backend.

The two never parent each other either:

- A NeuroLinker span (the SDK's own, or an OpenInference instrumentor's) nests
  only under a NeuroLinker span, or under the remote parent passed to
  :func:`continue_trace`. Under anything else, such as a web framework's request
  span, it starts a new trace: NeuroLinker scores each trace from its root span,
  so a query or a search must never hang under a parent NeuroLinker never receives.
- The SDK keeps its current span under a context key of its own, not as
  OpenTelemetry's current span, so the application's spans opened inside
  :func:`record_query`, :func:`continue_trace` or a ``@retriever`` search keep
  their own parent. OpenInference instrumentors make their spans OpenTelemetry's
  current span themselves (``OITracer`` uses ``trace.use_span``), so an
  application span inside one of those parents on it; :func:`parent_context`
  reads both places, so NeuroLinker spans still nest under the innermost one.
"""

from __future__ import annotations

import itertools
import warnings
from contextlib import contextmanager
from typing import Any, Iterator, Mapping, Optional

from ...errors import NeuroLinkerConfigError

TRACER_NAME = "neurolinker_sdk"

# Carries a NeuroLinker trace from one process to another (for example from an
# agent to the MCP server that runs its searches). A header of its own, not the
# W3C ``traceparent``: the application's own tracing reads and rewrites that one
# for its own traces, which are not NeuroLinker's.
TRACE_HEADER = "neurolinker-traceparent"
_W3C_HEADER = "traceparent"

_provider: Any = None
_warned_not_instrumented = False

# The SDK provider's open spans: span id -> start order. A span that started
# later is nested deeper, which tells the innermost of two open spans.
_active_spans: dict[int, int] = {}
_start_order = itertools.count()

# Context key of the SDK's current span (created on first use, so importing
# this module needs no OpenTelemetry).
_current_span_key: Any = None
_provider_class: Any = None


def require_otel() -> None:
    """Fail clearly when the tracking extra is missing.

    Raises:
        NeuroLinkerConfigError: OpenTelemetry or the OpenInference conventions
            are not installed.
    """
    try:
        import openinference.semconv.trace  # noqa: F401
        import opentelemetry.sdk.trace  # noqa: F401
    except ImportError as exc:
        raise NeuroLinkerConfigError(
            "Tracking dependencies are not installed. Install the tracking extra: "
            "`pip install neurolinker-sdk[tracking]`."
        ) from exc


def new_provider(**kwargs: Any) -> Any:
    """Build a tracer provider for NeuroLinker spans.

    Its tracers, the ones OpenInference instrumentors get from :func:`instrument`
    included, start spans with :func:`parent_context` and make them current
    with :func:`use_span`, so they follow the rules of this module.

    Args:
        **kwargs: ``TracerProvider`` arguments (``span_limits``, ...).

    Returns:
        The provider, not yet in use (see :func:`swap_provider`).
    """
    provider = _neurolinker_provider_class()(**kwargs)
    provider.add_span_processor(_active_spans_processor())
    return provider


def swap_provider(provider: Any) -> Any:
    """Make ``provider`` the SDK's tracer provider.

    Called by :func:`instrument`, and by :func:`capture_spans` to record spans
    in memory.

    Args:
        provider: A provider from :func:`new_provider`, or ``None`` for none
            (spans are dropped).

    Returns:
        The provider used until now, or ``None``.
    """
    global _provider, _warned_not_instrumented
    previous, _provider = _provider, provider
    _warned_not_instrumented = False
    return previous


def provider() -> Any:
    """The SDK's tracer provider.

    Returns:
        The provider set by :func:`instrument`, or ``None`` before it ran.
    """
    return _provider


def tracer(caller: str) -> Any:
    """The tracer NeuroLinker spans are created with.

    Args:
        caller: What creates the span (``"@retriever"``, ``"record_query()"``),
            for the warning.

    Returns:
        The SDK provider's tracer, or a no-op tracer (with a one-time warning)
        when :func:`instrument` has not run in this process.
    """
    global _warned_not_instrumented
    from opentelemetry import trace

    if _provider is not None:
        return _provider.get_tracer(TRACER_NAME)
    if not _warned_not_instrumented:
        _warned_not_instrumented = True
        warnings.warn(
            f"neurolinker: {caller} used but instrument(...) was not called in this "
            "process, so its spans are dropped. Call instrument(...) once at startup.",
            stacklevel=4,
        )
    return trace.NoOpTracer()


def parent_context(ctx: Any = None) -> Any:
    """The context a new NeuroLinker span starts in.

    Args:
        ctx: The context the span was asked to start in; ``None`` for the
            current one.

    Returns:
        ``ctx`` parented on its innermost NeuroLinker span (the open span of
        OpenTelemetry's, if it is a NeuroLinker span, or the SDK's current
        span); an empty context when it has none, so the new span is the root
        of a new trace.
    """
    from opentelemetry import context, trace

    if ctx is None:
        ctx = context.get_current()
    current = trace.get_current_span(ctx)
    parent, depth = None, -1
    if current.get_span_context().span_id in _active_spans:
        parent, depth = current, _active_spans[current.get_span_context().span_id]
    own = context.get_value(_span_key(), ctx)
    # A remote parent (continue_trace) is outside the process: the outermost.
    own_depth = -1 if own is None else _active_spans.get(own.get_span_context().span_id, -1)
    if own is not None and (parent is None or own_depth > depth):
        parent = own
    if parent is None:
        return context.Context()
    if parent is current:
        return ctx
    return trace.set_span_in_context(parent, ctx)


@contextmanager
def use_span(
    span: Any,
    *,
    end_on_exit: bool = False,
    record_exception: bool = True,
    set_status_on_exception: bool = True,
) -> Iterator[Any]:
    """Make ``span`` the SDK's current span inside the block.

    OpenTelemetry's ``use_span`` with the SDK's context key: the span becomes
    the parent of NeuroLinker spans started inside, while OpenTelemetry's
    current span, the parent of the application's spans, stays as it was.

    Args:
        span: The span.
        end_on_exit: End the span when the block exits.
        record_exception: Record an exception raised in the block on the span.
        set_status_on_exception: Set the span's status to ERROR on an exception.

    Yields:
        The span.
    """
    from opentelemetry import context
    from opentelemetry.trace import Status, StatusCode

    try:
        token = context.attach(context.set_value(_span_key(), span))
        try:
            yield span
        finally:
            context.detach(token)
    # Like OpenTelemetry: a BaseException (GeneratorExit, ...) is not an error.
    except Exception as exc:
        if span.is_recording():
            if record_exception:
                span.record_exception(exc)
            if set_status_on_exception:
                span.set_status(Status(StatusCode.ERROR, f"{type(exc).__name__}: {exc}"))
        raise
    finally:
        if end_on_exit:
            span.end()


def trace_headers(span: Any) -> dict[str, str]:
    """Headers that let another process continue ``span``'s trace.

    Args:
        span: A NeuroLinker span.

    Returns:
        ``{"neurolinker-traceparent": ...}``, or an empty dict when the span is
        not recorded (tracking off).
    """
    from opentelemetry import trace
    from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator

    if not span.get_span_context().is_valid:
        return {}
    carrier: dict[str, str] = {}
    TraceContextTextMapPropagator().inject(carrier, context=trace.set_span_in_context(span))
    value = carrier.get(_W3C_HEADER)
    return {TRACE_HEADER: value} if value else {}


@contextmanager
def continue_trace(headers: Optional[Mapping[str, Any]]) -> Iterator[None]:
    """Continue, in this process, the NeuroLinker trace another process started.

    Wrap the work done for one incoming request with it, passing the request's
    headers. NeuroLinker spans created inside (``@retriever``, OpenInference
    instrumentors) then join the caller's trace, so NeuroLinker scores them
    with the caller's query and answer. Without the header (or with a malformed
    one) it does nothing and those spans form traces of their own::

        with continue_trace(request.headers):
            results = search(query)

    The caller gets the header from :meth:`QueryRecorder.trace_headers`. Both
    processes must send to the same track.

    Args:
        headers: The incoming request's headers (any mapping; the header name is
            matched case-insensitively). ``None`` is accepted and ignored.

    Yields:
        Nothing.
    """
    value = _header(headers, TRACE_HEADER)
    if not value:
        yield
        return
    from opentelemetry import trace
    from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator

    remote = trace.get_current_span(TraceContextTextMapPropagator().extract({_W3C_HEADER: value}))
    if not remote.get_span_context().is_valid:
        yield
        return
    with use_span(remote, record_exception=False, set_status_on_exception=False):
        yield


def _header(headers: Optional[Mapping[str, Any]], name: str) -> Optional[str]:
    """Read one header from any mapping, ignoring the name's case.

    Args:
        headers: The headers, or ``None``.
        name: Lower-case header name.

    Returns:
        The value as a string, or ``None`` when absent.
    """
    if not headers:
        return None
    value = headers.get(name)
    if value is None:
        value = next((v for k, v in headers.items() if str(k).lower() == name), None)
    return None if value is None else str(value)


def _span_key() -> Any:
    """The context key of the SDK's current span.

    Returns:
        The key.
    """
    global _current_span_key
    if _current_span_key is None:
        from opentelemetry import context

        _current_span_key = context.create_key("neurolinker-current-span")
    return _current_span_key


def _neurolinker_provider_class() -> Any:
    """Build (once) the ``TracerProvider`` subclass of :func:`new_provider`.

    Returns:
        The class (built here so importing this module needs no OpenTelemetry).
    """
    global _provider_class
    if _provider_class is not None:
        return _provider_class
    from opentelemetry.sdk.trace import Tracer, TracerProvider
    from opentelemetry.trace import SpanKind

    try:
        from opentelemetry.util._decorator import _agnosticcontextmanager as span_context_manager
    except ImportError:  # OpenTelemetry < 1.24
        span_context_manager = contextmanager

    class NeuroLinkerTracer(Tracer):
        """An SDK tracer whose spans follow the parenting rules of this module."""

        def start_span(self, name: str, context: Any = None, *args: Any, **kwargs: Any) -> Any:
            """Start a span in :func:`parent_context` of ``context``.

            Called unbound with an OpenInference ``OITracer`` proxy as ``self``,
            so it only reaches the tracer through ``self``.

            Args:
                name: The span name.
                context: The context it was asked to start in.
                *args: The other ``Tracer.start_span`` arguments.
                **kwargs: The other ``Tracer.start_span`` arguments.

            Returns:
                The span.
            """
            return Tracer.start_span(self, name, parent_context(context), *args, **kwargs)

        @span_context_manager
        def start_as_current_span(
            self,
            name: str,
            context: Any = None,
            kind: Any = SpanKind.INTERNAL,
            attributes: Any = None,
            links: Any = (),
            start_time: Optional[int] = None,
            record_exception: bool = True,
            set_status_on_exception: bool = True,
            end_on_exit: bool = True,
        ) -> Iterator[Any]:
            """Start a span and make it the SDK's current span (:func:`use_span`).

            Args:
                name: The span name.
                context: The context it was asked to start in.
                kind: The span kind.
                attributes: The span attributes.
                links: The span links.
                start_time: The start time, in nanoseconds.
                record_exception: Record an exception raised in the block.
                set_status_on_exception: Set ERROR on an exception.
                end_on_exit: End the span when the block exits.

            Yields:
                The span.
            """
            span = self.start_span(
                name,
                context,
                kind=kind,
                attributes=attributes,
                links=links,
                start_time=start_time,
                record_exception=record_exception,
                set_status_on_exception=set_status_on_exception,
            )
            with use_span(
                span,
                end_on_exit=end_on_exit,
                record_exception=record_exception,
                set_status_on_exception=set_status_on_exception,
            ) as current:
                yield current

    class NeuroLinkerTracerProvider(TracerProvider):
        """A ``TracerProvider`` whose tracers are :class:`NeuroLinkerTracer`."""

        def get_tracer(self, *args: Any, **kwargs: Any) -> Any:
            """Get a tracer, as ``TracerProvider.get_tracer``.

            Args:
                *args: ``TracerProvider.get_tracer`` arguments.
                **kwargs: ``TracerProvider.get_tracer`` arguments.

            Returns:
                A :class:`NeuroLinkerTracer` (a no-op tracer when
                OpenTelemetry is disabled).
            """
            tracer = super().get_tracer(*args, **kwargs)
            # Re-classed rather than rebuilt: the Tracer constructor changes
            # between OpenTelemetry versions, and the subclass adds no state.
            if type(tracer) is Tracer:
                tracer.__class__ = NeuroLinkerTracer
            return tracer

    _provider_class = NeuroLinkerTracerProvider
    return _provider_class


def _active_spans_processor() -> Any:
    """Build the span processor that keeps the SDK provider's open spans, so
    :func:`parent_context` can tell a NeuroLinker span from any other.

    Returns:
        The processor (built here so importing this module needs no OpenTelemetry).
    """
    from opentelemetry.sdk.trace import SpanProcessor

    class _ActiveSpans(SpanProcessor):
        def on_start(self, span: Any, parent_context: Any = None) -> None:
            """Remember the span while it is open.

            Args:
                span: The span that started.
                parent_context: Unused.
            """
            _active_spans[span.get_span_context().span_id] = next(_start_order)

        def on_end(self, span: Any) -> None:
            """Forget the span.

            Args:
                span: The span that ended.
            """
            _active_spans.pop(span.get_span_context().span_id, None)

    return _ActiveSpans()
