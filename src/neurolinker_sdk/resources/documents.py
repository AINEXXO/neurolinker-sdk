from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional, Sequence, Union

import httpx

from ..http import _build_url, _json_headers, _raise_for_status


class ContentType(str, Enum):
    """Content types that can be requested from markdown / json endpoints.

    This mirrors the backend enum used to filter which pieces of content
    are included in the response.
    """

    TEXT = "text"
    FORMULA = "formula"
    TABLES = "tables"
    IMAGES = "images"


def _normalize_content_types(
    content_types: Optional[Sequence[Union[ContentType, str]]],
) -> Optional[List[str]]:
    """Normalize content_types to a list of plain strings.

    The backend only cares about the string values (e.g. "text", "images").
    This helper lets the SDK accept either the ContentType enum or raw strings.
    """
    if not content_types:
        return None
    normalized: List[str] = []
    for ct in content_types:
        if isinstance(ct, ContentType):
            normalized.append(ct.value)
        else:
            normalized.append(str(ct))
    return normalized


class DocumentsResource:
    def __init__(self, base_url: str, token: str, client: httpx.Client):
        self._base_url = base_url
        self._token = token
        self._client = client

    def _post_ids(
        self,
        path: str,
        document_ids: List[str],
        *,
        content_types: Optional[Sequence[Union[ContentType, str]]] = None,
    ) -> Dict[str, Any]:
        """Helper used by all document result endpoints.

        The API expects a JSON body of the form:
            {"document_ids": ["doc-1", "doc-2", ...], "content_types": ["text", ...]?}
        For endpoints that do not support content_types, the field is simply ignored by the backend.
        """
        url = _build_url(self._base_url, path)
        payload: Dict[str, Any] = {"document_ids": document_ids}
        normalized = _normalize_content_types(content_types)
        if normalized is not None:
            payload["content_types"] = normalized

        resp = self._client.post(url, json=payload, headers=_json_headers(self._token))
        _raise_for_status(resp)
        return resp.json()

    # ----- Synchronous endpoints -----

    def markdown(
        self,
        document_ids: List[str],
        *,
        content_types: Optional[Sequence[Union[ContentType, str]]] = None,
    ) -> Dict[str, Any]:
        """Get markdown for the given documents.

        When content_types is provided, the backend will filter or structure
        the markdown output according to the requested content classes.
        """
        return self._post_ids("/v1/documents/markdown", document_ids, content_types=content_types)

    def json(
        self,
        document_ids: List[str],
        *,
        content_types: Optional[Sequence[Union[ContentType, str]]] = None,
    ) -> Dict[str, Any]:
        """Get JSON for the given documents.

        When content_types is provided, the backend will filter or structure
        the JSON output according to the requested content classes.
        """
        return self._post_ids("/v1/documents/json", document_ids, content_types=content_types)

    def images(self, document_ids: List[str]) -> Dict[str, Any]:
        return self._post_ids("/v1/documents/images", document_ids)

    def page_summaries(self, document_ids: List[str]) -> Dict[str, Any]:
        return self._post_ids("/v1/documents/page-summaries", document_ids)

    def summary(self, document_ids: List[str]) -> Dict[str, Any]:
        return self._post_ids("/v1/documents/summary", document_ids)

    def section_summaries(self, document_ids: List[str]) -> Dict[str, Any]:
        return self._post_ids("/v1/documents/section-summaries", document_ids)

    def section_summary(self, document_ids: List[str]) -> Dict[str, Any]:
        return self._post_ids("/v1/documents/section-summary", document_ids)


class AsyncDocumentsResource:
    def __init__(self, base_url: str, token: str, client: httpx.AsyncClient):
        self._base_url = base_url
        self._token = token
        self._client = client

    async def _post_ids(
        self,
        path: str,
        document_ids: List[str],
        *,
        content_types: Optional[Sequence[Union[ContentType, str]]] = None,
    ) -> Dict[str, Any]:
        """Async helper used by all document result endpoints."""
        url = _build_url(self._base_url, path)
        payload: Dict[str, Any] = {"document_ids": document_ids}
        normalized = _normalize_content_types(content_types)
        if normalized is not None:
            payload["content_types"] = normalized

        resp = await self._client.post(
            url,
            json=payload,
            headers=_json_headers(self._token),
        )
        _raise_for_status(resp)
        return resp.json()

    # ----- Async endpoints -----

    async def markdown(
        self,
        document_ids: List[str],
        *,
        content_types: Optional[Sequence[Union[ContentType, str]]] = None,
    ) -> Dict[str, Any]:
        return await self._post_ids(
            "/v1/documents/markdown", document_ids, content_types=content_types
        )

    async def json(
        self,
        document_ids: List[str],
        *,
        content_types: Optional[Sequence[Union[ContentType, str]]] = None,
    ) -> Dict[str, Any]:
        return await self._post_ids("/v1/documents/json", document_ids, content_types=content_types)

    async def images(self, document_ids: List[str]) -> Dict[str, Any]:
        return await self._post_ids("/v1/documents/images", document_ids)

    async def page_summaries(self, document_ids: List[str]) -> Dict[str, Any]:
        return await self._post_ids("/v1/documents/page-summaries", document_ids)

    async def summary(self, document_ids: List[str]) -> Dict[str, Any]:
        return await self._post_ids("/v1/documents/summary", document_ids)

    async def section_summaries(self, document_ids: List[str]) -> Dict[str, Any]:
        return await self._post_ids("/v1/documents/section-summaries", document_ids)

    async def section_summary(self, document_ids: List[str]) -> Dict[str, Any]:
        return await self._post_ids("/v1/documents/section-summary", document_ids)
