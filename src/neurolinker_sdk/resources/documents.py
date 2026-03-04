from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional, Sequence, Union

import httpx

from ..http import _build_url, _json_headers, _raise_for_status


class ContentType(str, Enum):
    TEXT = "text"
    FORMULA = "formula"
    TABLES = "tables"
    IMAGES = "images"


class SummaryType(str, Enum):
    """Matches backend SummaryType enum for /documents/document-summary."""
    PAGE = "page"
    SECTION = "section"


def _normalize_content_types(
    content_types: Optional[Sequence[Union[ContentType, str]]],
) -> Optional[List[str]]:
    if not content_types:
        return None
    out: List[str] = []
    for ct in content_types:
        out.append(ct.value if isinstance(ct, ContentType) else str(ct))
    return out


class DocumentsResource:
    def __init__(self, base_url: str, token: str, client: httpx.Client):
        self._base_url = base_url
        self._token = token
        self._client = client

    def _post(
        self,
        path: str,
        payload: Dict[str, Any],
    ) -> Dict[str, Any]:
        url = _build_url(self._base_url, path)
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
        payload: Dict[str, Any] = {"document_ids": document_ids}
        normalized = _normalize_content_types(content_types)
        if normalized is not None:
            payload["content_types"] = normalized
        return self._post("/v1/documents/markdown", payload)

    def json(
        self,
        document_ids: List[str],
        *,
        content_types: Optional[Sequence[Union[ContentType, str]]] = None,
    ) -> Dict[str, Any]:
        payload: Dict[str, Any] = {"document_ids": document_ids}
        normalized = _normalize_content_types(content_types)
        if normalized is not None:
            payload["content_types"] = normalized
        return self._post("/v1/documents/json", payload)

    def images(self, document_ids: List[str]) -> Dict[str, Any]:
        return self._post("/v1/documents/images", {"document_ids": document_ids})

    def page_summaries(self, document_ids: List[str]) -> Dict[str, Any]:
        return self._post("/v1/documents/page-summaries", {"document_ids": document_ids})

    def section_summaries(self, document_ids: List[str]) -> Dict[str, Any]:
        return self._post("/v1/documents/section-summaries", {"document_ids": document_ids})

    def document_summary(
        self,
        document_ids: List[str],
        *,
        summary_type: Union[SummaryType, str],
    ) -> Dict[str, Any]:
        """
        POST /v1/documents/document-summary

        Backend requires:
          - document_ids: List[str]
          - summary_type: "page" or "section"
        """
        st = summary_type.value if isinstance(summary_type, SummaryType) else str(summary_type)
        return self._post(
            "/v1/documents/document-summary",
            {"document_ids": document_ids, "summary_type": st},
        )


class AsyncDocumentsResource:
    def __init__(self, base_url: str, token: str, client: httpx.AsyncClient):
        self._base_url = base_url
        self._token = token
        self._client = client

    async def _post(
        self,
        path: str,
        payload: Dict[str, Any],
    ) -> Dict[str, Any]:
        url = _build_url(self._base_url, path)
        resp = await self._client.post(url, json=payload, headers=_json_headers(self._token))
        _raise_for_status(resp)
        return resp.json()

    # ----- Async endpoints -----

    async def markdown(
        self,
        document_ids: List[str],
        *,
        content_types: Optional[Sequence[Union[ContentType, str]]] = None,
    ) -> Dict[str, Any]:
        payload: Dict[str, Any] = {"document_ids": document_ids}
        normalized = _normalize_content_types(content_types)
        if normalized is not None:
            payload["content_types"] = normalized
        return await self._post("/v1/documents/markdown", payload)

    async def json(
        self,
        document_ids: List[str],
        *,
        content_types: Optional[Sequence[Union[ContentType, str]]] = None,
    ) -> Dict[str, Any]:
        payload: Dict[str, Any] = {"document_ids": document_ids}
        normalized = _normalize_content_types(content_types)
        if normalized is not None:
            payload["content_types"] = normalized
        return await self._post("/v1/documents/json", payload)

    async def images(self, document_ids: List[str]) -> Dict[str, Any]:
        return await self._post("/v1/documents/images", {"document_ids": document_ids})

    async def page_summaries(self, document_ids: List[str]) -> Dict[str, Any]:
        return await self._post("/v1/documents/page-summaries", {"document_ids": document_ids})

    async def section_summaries(self, document_ids: List[str]) -> Dict[str, Any]:
        return await self._post("/v1/documents/section-summaries", {"document_ids": document_ids})

    async def document_summary(
        self,
        document_ids: List[str],
        *,
        summary_type: Union[SummaryType, str],
    ) -> Dict[str, Any]:
        st = summary_type.value if isinstance(summary_type, SummaryType) else str(summary_type)
        return await self._post(
            "/v1/documents/document-summary",
            {"document_ids": document_ids, "summary_type": st},
        )