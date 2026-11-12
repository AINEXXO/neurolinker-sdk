"""Trace Qdrant and Pinecone searches using caller-supplied query embeddings.

Clients are injected: importing this module never connects to a database or
initializes tracing. See docs/retriever-databases.md for live setup.
"""

from collections.abc import Callable, Mapping, Sequence
from typing import Any

from neurolinker_sdk import RetrievedDocument, retriever


def _text(fields: Mapping[str, Any] | None, text_field: str) -> str:
    """Read stored text without silently substituting ids or empty strings.

    Args:
        fields: Payload or metadata returned by the database.
        text_field: Field containing the original document text.

    Returns:
        The stored text, including an intentionally empty string.

    Raises:
        ValueError: The text field is absent or is not a string.
    """
    value = (fields or {}).get(text_field)
    if not isinstance(value, str):
        raise ValueError(f"Expected a string in document field {text_field!r}")
    return value


def qdrant_search(
    client: Any,
    collection: str,
    *,
    text_field: str = "text",
    vector_name: str | None = None,
) -> Callable[..., Any]:
    """Build a traced Qdrant query_points search.

    Args:
        client: An initialized synchronous QdrantClient.
        collection: Existing collection to query.
        text_field: Payload field containing document text.
        vector_name: Named dense vector, or None for an unnamed vector.

    Returns:
        A search callable accepting query text and its precomputed vector.
    """

    def to_documents(response: Any) -> list[RetrievedDocument]:
        """Convert QueryResponse points in their returned relevance order."""
        return [
            RetrievedDocument(_text(point.payload, text_field), str(point.id), point.score)
            for point in response.points
        ]

    @retriever(
        name="qdrant.vector_search",
        query_arg="query",
        search_type="vector",
        ranked=True,
        to_documents=to_documents,
        metadata=lambda args: {
            "database": "qdrant",
            "collection": collection,
            "vector_name": vector_name,
            "top_k": args["top_k"],
            "filter": (
                args["query_filter"].model_dump(mode="json", exclude_none=True)
                if args["query_filter"] is not None
                else None
            ),
        },
    )
    def search(
        query: str,
        vector: Sequence[float],
        *,
        top_k: int = 10,
        query_filter: Any = None,
    ) -> Any:
        """Search with a precomputed vector and preserve the QueryResponse.

        Args:
            query: Human-readable question recorded for evaluation.
            vector: Embedding of query, matching the collection's model.
            top_k: Maximum number of returned points.
            query_filter: Optional qdrant_client.models.Filter.

        Returns:
            The unmodified Qdrant QueryResponse.
        """
        return client.query_points(
            collection_name=collection,
            query=list(vector),
            using=vector_name,
            query_filter=query_filter,
            limit=top_k,
            with_payload=True,
            with_vectors=False,
        )

    return search


def pinecone_search(
    index: Any,
    *,
    namespace: str = "",
    text_field: str = "text",
) -> Callable[..., Any]:
    """Build a traced Pinecone dense-vector Index.query search.

    Args:
        index: An initialized synchronous Pinecone Index.
        namespace: Namespace containing the existing documents.
        text_field: Metadata field containing document text.

    Returns:
        A search callable accepting query text and its precomputed vector.
    """

    def to_documents(response: Any) -> list[RetrievedDocument]:
        """Convert QueryResponse matches in their returned relevance order."""
        return [
            RetrievedDocument(_text(match.metadata, text_field), match.id, match.score)
            for match in response.matches
        ]

    @retriever(
        name="pinecone.vector_search",
        query_arg="query",
        search_type="vector",
        ranked=True,
        to_documents=to_documents,
        metadata=lambda args: {
            "database": "pinecone",
            "namespace": namespace,
            "top_k": args["top_k"],
            "filter": args["metadata_filter"],
        },
    )
    def search(
        query: str,
        vector: Sequence[float],
        *,
        top_k: int = 10,
        metadata_filter: dict[str, Any] | None = None,
    ) -> Any:
        """Search with a precomputed vector and preserve the QueryResponse.

        Args:
            query: Human-readable question recorded for evaluation.
            vector: Embedding of query, matching the index's model.
            top_k: Maximum number of returned matches.
            metadata_filter: Optional Pinecone metadata filter expression.

        Returns:
            The unmodified Pinecone QueryResponse.
        """
        return index.query(
            vector=list(vector),
            top_k=top_k,
            namespace=namespace,
            filter=metadata_filter,
            include_metadata=True,
            include_values=False,
        )

    return search
