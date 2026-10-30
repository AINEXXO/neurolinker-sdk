from __future__ import annotations

import os
import warnings
from importlib.metadata import entry_points
from typing import Any, Optional, Sequence

from ...config import DEFAULT_BASE_URL
from ...errors import NeuroLinkerConfigError
from . import _tracing

_TRACK_UID_HEADER = "neurolinker-track-uid"
_INGEST_PATH = "/v1/eval/ingest/v1/traces"


def instrument(
    track_uid: str,
    *,
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
    frameworks: Optional[Sequence[str]] = None,
    manual: bool = False,
) -> Any:
    """Attach NeuroLinker tracking — call once at app startup.

    Activates every installed OpenInference instrumentor, so your RAG framework's
    calls are traced automatically (no code changes). ``track_uid`` comes from
    ``client.evaluation.tracking.tracks.create``; ``api_key`` / ``base_url``
    default to ``NEUROLINKER_API_KEY`` / ``NEUROLINKER_BASE_URL``. Pass
    ``manual=True`` if you'll instead trace a custom RAG via :func:`record_query`
    (silences the "no instrumentor found" warning); ``frameworks`` restricts which
    instrumentors to activate.

    NeuroLinker gets a tracer provider of its own: only the OpenInference
    instrumentors' spans and the SDK's own (:func:`record_query`,
    :func:`retriever`) are sent to NeuroLinker. The process-wide provider, and
    with it any OpenTelemetry setup the app already has, is left untouched, so
    the app's own spans (HTTP, database) never reach NeuroLinker.

    Requires the tracking extra + your framework's OpenInference instrumentor
    (e.g. ``pip install neurolinker-sdk[tracking] openinference-instrumentation-langchain``;
    any OpenInference instrumentor is auto-discovered).

    Args:
        track_uid: The track that receives the traces.
        api_key: NeuroLinker API key. Default: ``NEUROLINKER_API_KEY``.
        base_url: NeuroLinker API base URL. Default: ``NEUROLINKER_BASE_URL``,
            else the public API.
        frameworks: Entry-point names of the instrumentors to activate. Default:
            every installed one; ``[]`` activates none.
        manual: The app traces itself with :func:`record_query` /
            :func:`retriever`; silences the "no instrumentor found" warning.

    Returns:
        NeuroLinker's OpenTelemetry ``TracerProvider``: call
        ``provider.force_flush()`` before a short-lived script exits. A repeat
        call returns the same provider and changes nothing.

    Raises:
        NeuroLinkerConfigError: ``track_uid`` or the API key is missing, or the
            tracking extra is not installed.
    """
    if not track_uid:
        raise NeuroLinkerConfigError("track_uid must be a non-empty string.")

    token = api_key or os.getenv("NEUROLINKER_API_KEY", "").strip()
    if not token:
        raise NeuroLinkerConfigError(
            "No API key: pass api_key=... or set NEUROLINKER_API_KEY."
        )
    url = (base_url or os.getenv("NEUROLINKER_BASE_URL") or DEFAULT_BASE_URL).rstrip("/")

    try:
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
    except ImportError as exc:
        raise NeuroLinkerConfigError(
            "Tracking dependencies are not installed. Install the tracking extra "
            "(plus your framework's OpenInference instrumentor), e.g. "
            "`pip install neurolinker-sdk[tracking] openinference-instrumentation-langchain`."
        ) from exc

    existing = _tracing.provider()
    if existing is not None:
        warnings.warn(
            "neurolinker: instrument() was already called in this process — "
            "ignoring the repeat call.",
            stacklevel=2,
        )
        return existing

    if os.getenv("OTEL_SDK_DISABLED", "").strip().lower() in ("1", "true", "yes"):
        warnings.warn(
            "neurolinker: OTEL_SDK_DISABLED is set, so OpenTelemetry records "
            "nothing and no trace reaches NeuroLinker. Unset it in this process "
            "to track.",
            stacklevel=2,
        )

    exporter = OTLPSpanExporter(
        endpoint=f"{url}{_INGEST_PATH}",
        headers={"authorization": f"Bearer {token}", _TRACK_UID_HEADER: track_uid},
    )
    provider = _tracing.new_provider()
    provider.add_span_processor(BatchSpanProcessor(exporter))
    _tracing.swap_provider(provider)

    activated = _activate_instrumentors(provider, frameworks)
    if not activated and not manual:
        warnings.warn(
            "neurolinker: no OpenInference instrumentor found — auto-tracing is "
            "off. Install your framework's instrumentor (e.g. "
            "`pip install openinference-instrumentation-langchain`) for automatic "
            "tracing, or use `record_query(...)` to trace a custom RAG manually.",
            stacklevel=2,
        )
    elif len(activated) > 1:
        warnings.warn(
            "neurolinker: multiple instrumentors active ("
            + ", ".join(activated)
            + "). If you see duplicate spans or doubled token counts, restrict "
            "them with instrument(..., frameworks=[...]).",
            stacklevel=2,
        )
    return provider


def _activate_instrumentors(provider: Any, frameworks: Optional[Sequence[str]]) -> list[str]:
    """Discover every installed OpenInference/OTel instrumentor via the standard
    ``opentelemetry_instrumentor`` entry-point group and activate it on our
    provider. No framework is hardcoded — the user's installed instrumentor
    self-registers the entry point; we just activate what's present."""
    activated: list[str] = []
    for ep in entry_points(group="opentelemetry_instrumentor"):
        if frameworks is not None and ep.name not in frameworks:
            continue
        try:
            ep.load()().instrument(tracer_provider=provider)
            activated.append(ep.name)
        except Exception as exc:  # noqa: BLE001 — one bad instrumentor must not abort the rest
            warnings.warn(
                f"neurolinker: failed to activate instrumentor {ep.name!r}: {exc}",
                stacklevel=2,
            )
    return activated
