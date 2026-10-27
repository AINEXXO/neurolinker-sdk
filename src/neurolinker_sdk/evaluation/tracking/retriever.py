from __future__ import annotations

import functools
import inspect
import warnings
from dataclasses import dataclass
from typing import Any, Callable, Iterable, Optional, TypeVar, Union

from ...errors import NeuroLinkerConfigError

_TRACER_NAME = "neurolinker_sdk"

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


def retriever(
    func: Optional[F] = None,
    *,
    to_documents: Optional[Callable[[Any], Iterable[DocumentLike]]] = None,
    query_arg: Optional[str] = None,
    name: Optional[str] = None,
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
    given), in the order returned. The function's return value is passed through
    unchanged. Tracing never breaks the search: if ``to_documents`` raises, the
    span is sent without documents and a warning is emitted. Works on sync and
    async functions, standalone or inside :func:`record_query` (the span then
    also counts as that query's context).

    Args:
        func: The search function (when used as a bare ``@retriever``).
        to_documents: Maps the function's return value to the documents, as
            strings or :class:`RetrievedDocument`. Default: the return value
            must already be an iterable of those.
        query_arg: Name of the parameter holding the query. Default: the
            parameter named ``query``, else the first parameter (after
            ``self`` / ``cls``).
        name: Span name. Default: the function's qualified name.

    Returns:
        The decorated function, or a decorator when called with options only.

    Raises:
        NeuroLinkerConfigError: ``query_arg`` does not name a parameter of the
            decorated function, or the function takes no parameters.
    """

    def decorate(fn: F) -> F:
        query_param = _resolve_query_param(fn, query_arg)
        signature = inspect.signature(fn)
        span_name = name or fn.__qualname__
        convert = to_documents or _identity

        if inspect.iscoroutinefunction(fn):

            @functools.wraps(fn)
            async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                query = _bound_query(signature, query_param, args, kwargs)
                with _RetrieverSpan(span_name, query) as record:
                    result = await fn(*args, **kwargs)
                    record(result, convert)
                    return result

            return async_wrapper  # type: ignore[return-value]

        @functools.wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            query = _bound_query(signature, query_param, args, kwargs)
            with _RetrieverSpan(span_name, query) as record:
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


def _bound_query(
    signature: inspect.Signature, query_param: str, args: tuple, kwargs: dict
) -> Optional[str]:
    """Read the query from one call's arguments.

    Args:
        signature: The decorated function's signature.
        query_param: The parameter that holds the query.
        args: Positional arguments of the call.
        kwargs: Keyword arguments of the call.

    Returns:
        The query as a string, or ``None`` when it was not passed (or the call
        does not bind; the function itself then raises as usual).
    """
    try:
        bound = signature.bind(*args, **kwargs)
    except TypeError:
        return None
    bound.apply_defaults()
    value = bound.arguments.get(query_param)
    return None if value is None else str(value)


class _RetrieverSpan:
    """Context manager around one search: opens the RETRIEVER span and yields a
    callback that records the documents from the function's result."""

    _warned_no_provider = False

    def __init__(self, span_name: str, query: Optional[str]) -> None:
        """Prepare the span.

        Args:
            span_name: Span name.
            query: The search query, if known.
        """
        self._span_name = span_name
        self._query = query
        self._cm: Any = None

    def __enter__(self) -> Callable[[Any, Callable[[Any], Iterable[DocumentLike]]], None]:
        """Start the span.

        Returns:
            ``record(result, to_documents)``, which sets the document attributes.

        Raises:
            NeuroLinkerConfigError: The tracking extra is not installed.
        """
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
        if not isinstance(trace.get_tracer_provider(), TracerProvider) and not (
            _RetrieverSpan._warned_no_provider
        ):
            _RetrieverSpan._warned_no_provider = True
            warnings.warn(
                "neurolinker: @retriever used but no tracer provider is configured: "
                "call instrument(...) at startup in this process, otherwise these "
                "spans are dropped.",
                stacklevel=4,
            )
        self._cm = trace.get_tracer(_TRACER_NAME).start_as_current_span(self._span_name)
        span = self._cm.__enter__()
        span.set_attribute(
            SpanAttributes.OPENINFERENCE_SPAN_KIND, OpenInferenceSpanKindValues.RETRIEVER.value
        )
        if self._query is not None:
            span.set_attribute(SpanAttributes.INPUT_VALUE, self._query)

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
            for i, doc in enumerate(documents):
                span.set_attribute(keys["content"].format(i=i), doc.content)
                if doc.id is not None:
                    span.set_attribute(keys["id"].format(i=i), doc.id)
                if doc.score is not None:
                    span.set_attribute(keys["score"].format(i=i), doc.score)

        return record

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
