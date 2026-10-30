from __future__ import annotations

import functools
import inspect
import json
import warnings
from dataclasses import dataclass
from typing import Any, Callable, Iterable, Mapping, Optional, TypeVar, Union

from ...errors import NeuroLinkerConfigError
from . import _tracing

# NeuroLinker's own retrieval attributes. OpenInference has no attribute for
# "does the order mean relevance" or for the result size before truncation.
RANKED_ATTR = "neurolinker.retrieval.ranked"
DOCUMENT_COUNT_ATTR = "neurolinker.retrieval.document_count"

# Default cap on the documents recorded per span. Each document costs up to
# three span attributes (content, id, score), so this also bounds span size.
DEFAULT_MAX_DOCUMENTS = 50

F = TypeVar("F", bound=Callable[..., Any])


@dataclass(frozen=True)
class RetrievedDocument:
    """One document returned by a search, for :func:`retriever`'s ``to_documents``.

    Return plain strings from ``to_documents`` when you only have the text; use
    this to also send the document's id and the search engine's own score.

    Attributes:
        content: The document text the judge reads.
        id: Optional document id (e.g. the vector DB primary key).
        score: Optional similarity / relevance score from the search engine.
    """

    content: str
    id: Optional[str] = None
    score: Optional[float] = None


DocumentLike = Union[str, RetrievedDocument]
MetadataLike = Union[Mapping[str, Any], Callable[[Mapping[str, Any]], Mapping[str, Any]]]


def retriever(
    func: Optional[F] = None,
    *,
    to_documents: Optional[Callable[[Any], Iterable[DocumentLike]]] = None,
    query_arg: Optional[str] = None,
    name: Optional[str] = None,
    ranked: Optional[bool] = None,
    metadata: Optional[MetadataLike] = None,
    max_documents: int = DEFAULT_MAX_DOCUMENTS,
) -> Any:
    """Trace a search function as an OpenInference RETRIEVER span.

    Put it on the function that runs your search, whatever the vector DB or
    query engine. Each call becomes one search that NeuroLinker scores at
    retrieval level: the query against the returned documents. Call
    :func:`instrument` once at startup in the same process, otherwise the span
    is dropped::

        @retriever(to_documents=lambda hits: [h["entity"]["text"] for h in hits[0]])
        def search(query: str, top_k: int = 10):
            return milvus.search("manuals", data=[embed(query)], limit=top_k,
                                 output_fields=["text"])

    The span carries ``input.value`` (the query) and
    ``retrieval.documents.{i}.document.content`` (plus ``.id`` / ``.score`` when
    given), in the order returned, plus ``neurolinker.retrieval.document_count``
    (how many documents the search returned, before any cut). The function's
    return value is passed through unchanged. Tracing never breaks the search:
    if ``to_documents`` or ``metadata`` raises, the span is sent without that
    part and a warning is emitted. Works on sync and async functions, standalone
    (each call is a trace of its own) or inside :func:`record_query`, or inside
    :func:`continue_trace` in a service the query called: the span then also
    counts as that query's context.

    Ranked or not: a vector, keyword or hybrid search returns documents in
    relevance order, so NeuroLinker can score the ranking (hit at 1, MRR,
    nDCG). A filter-only lookup (a SQL ``WHERE``, a scalar filter, or results
    ordered by date or price) has no relevance order; pass ``ranked=False`` and
    NeuroLinker scores it as a set. A lookup with no natural-language query can
    pass ``query_arg`` pointing to a parameter that is ``None``: the span is
    then recorded (count, latency, metadata) but not judged.

    Span size: at most ``max_documents`` documents are recorded, and never more
    than fit in the span's attribute limit (OpenTelemetry's
    ``OTEL_SPAN_ATTRIBUTE_COUNT_LIMIT``, 128 by default). Over the limit
    OpenTelemetry evicts the span's oldest attributes, which are its kind and
    query, so the span would silently stop being a RETRIEVER. When the limit
    forces a cut a warning is emitted once per span name.

    Args:
        func: The search function (when used as a bare ``@retriever``).
        to_documents: Maps the function's return value to the documents, as
            strings or :class:`RetrievedDocument`. Default: the return value
            must already be an iterable of those.
        query_arg: Name of the parameter holding the query. Default: the
            parameter named ``query``, else the first parameter (after
            ``self`` / ``cls``).
        name: Span name. Default: the function's qualified name.
        ranked: Whether the order of the returned documents reflects relevance
            to the query. ``True`` for vector, keyword, hybrid or reranked
            search; ``False`` for filter-only lookups or results ordered by
            anything else. Default ``None``: not sent, NeuroLinker infers it
            from the document scores.
        metadata: Extra context recorded on the span as OpenInference
            ``metadata`` (JSON), such as the filter expression or the
            collection. Either a mapping, or a function that receives the
            call's arguments by parameter name and returns one (for per-call
            values). Values that are not JSON types are recorded as strings.
        max_documents: The most documents recorded on the span (the true
            count is always recorded). Must be at least 0.

    Returns:
        The decorated function, or a decorator when called with options only.

    Raises:
        NeuroLinkerConfigError: ``query_arg`` does not name a parameter of the
            decorated function, the function takes no parameters, or
            ``max_documents`` is negative or not an int.
    """
    if isinstance(max_documents, bool) or not isinstance(max_documents, int) or max_documents < 0:
        raise NeuroLinkerConfigError(
            f"retriever: max_documents must be an int >= 0, got {max_documents!r}."
        )

    def decorate(fn: F) -> F:
        query_param = _resolve_query_param(fn, query_arg)
        signature = inspect.signature(fn)
        span_name = name or fn.__qualname__
        convert = to_documents or _identity

        def open_span(args: tuple, kwargs: dict) -> _RetrieverSpan:
            """Build the span context for one call.

            Args:
                args: Positional arguments of the call.
                kwargs: Keyword arguments of the call.

            Returns:
                The span context manager.
            """
            arguments = _bound_arguments(signature, args, kwargs)
            query = None if arguments is None else arguments.get(query_param)
            return _RetrieverSpan(
                span_name,
                None if query is None else str(query),
                ranked=ranked,
                metadata=_resolve_metadata(metadata, arguments, span_name),
                max_documents=max_documents,
            )

        if inspect.iscoroutinefunction(fn):

            @functools.wraps(fn)
            async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                with open_span(args, kwargs) as record:
                    result = await fn(*args, **kwargs)
                    record(result, convert)
                    return result

            return async_wrapper  # type: ignore[return-value]

        @functools.wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            with open_span(args, kwargs) as record:
                result = fn(*args, **kwargs)
                record(result, convert)
                return result

        return wrapper  # type: ignore[return-value]

    if func is not None:
        return decorate(func)
    return decorate


def _identity(result: Any) -> Any:
    """Default ``to_documents``: the result is already the documents.

    Args:
        result: The search function's return value.

    Returns:
        ``result`` unchanged.
    """
    return result


def _resolve_query_param(fn: Callable[..., Any], query_arg: Optional[str]) -> str:
    """Pick the parameter that holds the query, at decoration time.

    Args:
        fn: The decorated function.
        query_arg: Explicit parameter name, if given.

    Returns:
        The parameter name.

    Raises:
        NeuroLinkerConfigError: ``query_arg`` is not a parameter, or there is
            no parameter to use.
    """
    params = [p for p in inspect.signature(fn).parameters if p not in ("self", "cls")]
    if query_arg is not None:
        if query_arg not in params:
            raise NeuroLinkerConfigError(
                f"retriever: {fn.__qualname__} has no parameter {query_arg!r}."
            )
        return query_arg
    if "query" in params:
        return "query"
    if not params:
        raise NeuroLinkerConfigError(
            f"retriever: {fn.__qualname__} takes no parameters, so there is no query "
            "to record. Decorate the function that receives the query."
        )
    return params[0]


def _bound_arguments(
    signature: inspect.Signature, args: tuple, kwargs: dict
) -> Optional[dict[str, Any]]:
    """Bind one call's arguments to parameter names, defaults applied.

    Args:
        signature: The decorated function's signature.
        args: Positional arguments of the call.
        kwargs: Keyword arguments of the call.

    Returns:
        The arguments by parameter name, or ``None`` when the call does not
        bind (the function itself then raises as usual).
    """
    try:
        bound = signature.bind(*args, **kwargs)
    except TypeError:
        return None
    bound.apply_defaults()
    return dict(bound.arguments)


def _resolve_metadata(
    metadata: Optional[MetadataLike],
    arguments: Optional[Mapping[str, Any]],
    span_name: str,
) -> Optional[str]:
    """Turn ``metadata`` into the JSON recorded on the span.

    Args:
        metadata: A mapping, a function of the call's arguments, or ``None``.
        arguments: The call's arguments by parameter name (``None`` when the
            call does not bind).
        span_name: Span name, for the warning.

    Returns:
        The metadata as a JSON object string, or ``None`` when there is none
        or it could not be built (a warning is emitted; the search still runs).
    """
    if metadata is None:
        return None
    try:
        values = metadata(dict(arguments or {})) if callable(metadata) else metadata
        if values is None:
            return None
        return json.dumps(dict(values), default=str, ensure_ascii=False)
    except Exception as exc:  # noqa: BLE001 (tracing must never break the search)
        warnings.warn(
            f"neurolinker: @retriever could not build the metadata of {span_name}: "
            f"{exc!r}. The span is sent without metadata.",
            stacklevel=4,
        )
        return None


def _attribute_limit(span: Any) -> Optional[int]:
    """The span's attribute count limit, if it has one.

    Read from the OpenTelemetry SDK span (``SpanLimits.max_span_attributes``).
    A non-recording span (no SDK provider, or ``OTEL_SDK_DISABLED``) has none.

    Args:
        span: The current span.

    Returns:
        The limit, or ``None`` when unlimited or unknown.
    """
    limit = getattr(getattr(span, "_limits", None), "max_span_attributes", None)
    return limit if isinstance(limit, int) and limit >= 0 else None


def _attribute_count(span: Any) -> int:
    """How many attributes the span holds now.

    Args:
        span: The current span.

    Returns:
        The attribute count (0 for a span that does not expose them).
    """
    attributes = getattr(span, "attributes", None)
    return len(attributes) if attributes is not None else 0


def _attributes_per_document(doc: RetrievedDocument) -> int:
    """Span attributes one document needs.

    Args:
        doc: The document.

    Returns:
        1 for the content, plus 1 each for an id and a score.
    """
    return 1 + (doc.id is not None) + (doc.score is not None)


class _RetrieverSpan:
    """Context manager around one search: opens the RETRIEVER span and yields a
    callback that records the documents from the function's result."""

    _warned_attribute_limit: set[str] = set()

    def __init__(
        self,
        span_name: str,
        query: Optional[str],
        *,
        ranked: Optional[bool] = None,
        metadata: Optional[str] = None,
        max_documents: int = DEFAULT_MAX_DOCUMENTS,
    ) -> None:
        """Prepare the span.

        Args:
            span_name: Span name.
            query: The search query, if known.
            ranked: Whether the document order reflects relevance (``None``:
                not recorded).
            metadata: Metadata as a JSON object string, if any.
            max_documents: The most documents to record.
        """
        self._span_name = span_name
        self._query = query
        self._ranked = ranked
        self._metadata = metadata
        self._max_documents = max_documents
        self._cm: Any = None

    def __enter__(self) -> Callable[[Any, Callable[[Any], Iterable[DocumentLike]]], None]:
        """Start the span.

        Returns:
            ``record(result, to_documents)``, which sets the document attributes.

        Raises:
            NeuroLinkerConfigError: The tracking extra is not installed.
        """
        _tracing.require_otel()
        from openinference.semconv.trace import (
            DocumentAttributes,
            OpenInferenceSpanKindValues,
            SpanAttributes,
        )

        self._cm = _tracing.tracer("@retriever").start_as_current_span(self._span_name)
        span = self._cm.__enter__()
        span.set_attribute(
            SpanAttributes.OPENINFERENCE_SPAN_KIND, OpenInferenceSpanKindValues.RETRIEVER.value
        )
        if self._query is not None:
            span.set_attribute(SpanAttributes.INPUT_VALUE, self._query)
        if self._ranked is not None:
            span.set_attribute(RANKED_ATTR, bool(self._ranked))
        if self._metadata is not None:
            span.set_attribute(SpanAttributes.METADATA, self._metadata)

        prefix = SpanAttributes.RETRIEVAL_DOCUMENTS + ".{i}."
        keys = {
            "content": prefix + DocumentAttributes.DOCUMENT_CONTENT,
            "id": prefix + DocumentAttributes.DOCUMENT_ID,
            "score": prefix + DocumentAttributes.DOCUMENT_SCORE,
        }

        def record(result: Any, to_documents: Callable[[Any], Iterable[DocumentLike]]) -> None:
            """Set the document attributes from the search result.

            Args:
                result: The search function's return value.
                to_documents: Maps it to the documents.
            """
            try:
                documents = [_as_document(d) for d in to_documents(result)]
            except Exception as exc:  # noqa: BLE001 (tracing must never break the search)
                warnings.warn(
                    f"neurolinker: @retriever could not read documents from the result "
                    f"of {self._span_name}: {exc!r}. The span is sent without documents.",
                    stacklevel=2,
                )
                return
            span.set_attribute(DOCUMENT_COUNT_ATTR, len(documents))
            for i, doc in enumerate(self._documents_that_fit(span, documents)):
                span.set_attribute(keys["content"].format(i=i), doc.content)
                if doc.id is not None:
                    span.set_attribute(keys["id"].format(i=i), doc.id)
                if doc.score is not None:
                    span.set_attribute(keys["score"].format(i=i), doc.score)

        return record

    def _documents_that_fit(
        self, span: Any, documents: list[RetrievedDocument]
    ) -> list[RetrievedDocument]:
        """The leading documents that can be recorded without evicting anything.

        Capped by ``max_documents`` and by the attributes left under the span's
        limit. Warns once per span name when the limit, not ``max_documents``,
        forced the cut.

        Args:
            span: The current span (its other attributes already set).
            documents: All documents, in the order returned.

        Returns:
            The documents to record, a prefix of ``documents``.
        """
        wanted = documents[: self._max_documents]
        limit = _attribute_limit(span)
        if limit is None:
            return wanted
        room = limit - _attribute_count(span)
        fitting: list[RetrievedDocument] = []
        for doc in wanted:
            room -= _attributes_per_document(doc)
            if room < 0:
                break
            fitting.append(doc)
        if len(fitting) < len(wanted) and self._span_name not in self._warned_attribute_limit:
            _RetrieverSpan._warned_attribute_limit.add(self._span_name)
            warnings.warn(
                f"neurolinker: {self._span_name} returned {len(documents)} documents but "
                f"only {len(fitting)} fit in the span's attribute limit ({limit}); the "
                "rest are not recorded. Raise OTEL_SPAN_ATTRIBUTE_COUNT_LIMIT, or lower "
                "max_documents, to record them all.",
                stacklevel=3,
            )
        return fitting

    def __exit__(self, *exc_info: Any) -> Any:
        """End the span; an exception from the search is recorded on it and re-raised.

        Args:
            *exc_info: The exception triple, if the search raised.

        Returns:
            The underlying span context manager's result (never suppresses).
        """
        return self._cm.__exit__(*exc_info)


def _as_document(item: DocumentLike) -> RetrievedDocument:
    """Normalize one ``to_documents`` item.

    Args:
        item: A string or a :class:`RetrievedDocument`.

    Returns:
        The document, with ``id`` as a string and ``score`` as a float.

    Raises:
        TypeError: The item is neither a string nor a :class:`RetrievedDocument`.
    """
    if isinstance(item, str):
        return RetrievedDocument(content=item)
    if isinstance(item, RetrievedDocument):
        return RetrievedDocument(
            content=str(item.content),
            id=None if item.id is None else str(item.id),
            score=None if item.score is None else float(item.score),
        )
    raise TypeError(
        f"expected str or RetrievedDocument, got {type(item).__name__}; "
        "pass to_documents=... to map your search result"
    )
