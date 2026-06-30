from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

import httpx

from ..polling import wait_for_terminal_status, wait_for_terminal_status_async
from .documents import AsyncDocumentsResource, DocumentsResource
from .extract import AsyncExtractResource, EnrichmentMode, ExtractResource
from .helpers import (
    extract_document_ids as _extract_document_ids,
)
from .helpers import (
    extract_markdown_document_ids as _extract_markdown_document_ids,
)
from .helpers import (
    extract_request_uid as _extract_request_uid,
)
from .helpers import (
    extract_status,
)
from .status import AsyncStatusResource, StatusResource
from .tasks import AsyncTasksResource, TasksResource
from .zip import AsyncZipResource, ZipResource


def _extraction_timeout_suffix(last: Optional[Dict[str, Any]]) -> str:
    """Return ``" Job URL: <url>"`` from a request-status payload, or ``""``."""
    if not isinstance(last, dict):
        return ""
    url = last.get("job_page_url")
    if not url:
        data = last.get("data")
        if isinstance(data, dict):
            url = data.get("job_page_url")
    return f" Job URL: {url}" if url else ""


class ExtractionModule:
    """Extraction module — full and field extraction."""

    def __init__(
        self,
        *,
        base_url: str,
        token: str,
        client: httpx.Client,
        timeout_s: float,
        poll_interval_s: float,
        poll_max_interval_s: float,
    ):
        self._extract = ExtractResource(base_url, token, client)
        self._tasks = TasksResource(base_url, token, client)
        self._zip = ZipResource(base_url, token, client)
        self.status = StatusResource(base_url, token, client)
        self.documents = DocumentsResource(base_url, token, client)

        self._timeout_s = timeout_s
        self._poll_interval_s = poll_interval_s
        self._poll_max_interval_s = poll_max_interval_s

    def extract(
        self,
        *,
        documents: Optional[List[Tuple[str, bytes]]] = None,
        urls: Optional[List[str]] = None,
        alias: Optional[str] = None,
        description: Optional[str] = None,
        enrichment_mode: Optional[EnrichmentMode] = None,
    ) -> Dict[str, Any]:
        return self._extract.extract(
            documents=documents,
            urls=urls,
            alias=alias,
            description=description,
            enrichment_mode=enrichment_mode,
        )

    def extract_fields(
        self,
        *,
        json_schema: Dict[str, Any],
        documents: Optional[List[Tuple[str, bytes]]] = None,
        urls: Optional[List[str]] = None,
        alias: Optional[str] = None,
        description: Optional[str] = None,
    ) -> Dict[str, Any]:
        return self._extract.extract_fields(
            json_schema=json_schema,
            documents=documents,
            urls=urls,
            alias=alias,
            description=description,
        )

    def extract_fields_from_markdown(
        self,
        *,
        json_schema: Dict[str, Any],
        document_ids: List[str],
        alias: Optional[str] = None,
        description: Optional[str] = None,
    ) -> Dict[str, Any]:
        return self._extract.extract_fields_from_markdown(
            json_schema=json_schema,
            document_ids=document_ids,
            alias=alias,
            description=description,
        )

    def generate_schema(self, *, description: str) -> Dict[str, Any]:
        return self._extract.generate_schema(description=description)

    def list_tasks(self) -> Dict[str, Any]:
        return self._tasks.list()

    def make_zip(
        self,
        *,
        job_uid: str,
        document_uid: Optional[str] = None,
        local_images: bool = False,
        content_types: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        return self._zip.make_zip(
            job_uid=job_uid,
            document_uid=document_uid,
            local_images=local_images,
            content_types=content_types,
        )

    @staticmethod
    def extract_request_uid(extract_response: Dict[str, Any]) -> str:
        """Return ``request_uid`` from an extract endpoint payload."""
        return _extract_request_uid(extract_response)

    @staticmethod
    def extract_document_ids(status_response: Dict[str, Any]) -> List[str]:
        """Return document IDs from a request-status payload."""
        return _extract_document_ids(status_response)

    @staticmethod
    def extract_markdown_document_ids(submit_response: Dict[str, Any]) -> List[str]:
        """Return the new ``document_uid``s from an extract-fields-from-markdown
        submit response's ``document_map`` (used for polling and scalar retrieval)."""
        return _extract_markdown_document_ids(submit_response)

    def wait_for_request(
        self,
        request_uid: str,
        *,
        timeout_s: Optional[float] = None,
        poll_interval_s: Optional[float] = None,
        poll_max_interval_s: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Poll ``/request-status/{request_uid}`` until a terminal state or timeout."""
        return wait_for_terminal_status(
            fetch_status=lambda: self.status.request(request_uid),
            extract_status=extract_status,
            timeout_s=self._timeout_s if timeout_s is None else timeout_s,
            poll_interval_s=(
                self._poll_interval_s if poll_interval_s is None else poll_interval_s
            ),
            poll_max_interval_s=(
                self._poll_max_interval_s
                if poll_max_interval_s is None
                else poll_max_interval_s
            ),
            identifier=f"request {request_uid}",
            timeout_context=_extraction_timeout_suffix,
        )


class AsyncExtractionModule:
    def __init__(
        self,
        *,
        base_url: str,
        token: str,
        client: httpx.AsyncClient,
        timeout_s: float,
        poll_interval_s: float,
        poll_max_interval_s: float,
    ):
        self._extract = AsyncExtractResource(base_url, token, client)
        self._tasks = AsyncTasksResource(base_url, token, client)
        self._zip = AsyncZipResource(base_url, token, client)
        self.status = AsyncStatusResource(base_url, token, client)
        self.documents = AsyncDocumentsResource(base_url, token, client)

        self._timeout_s = timeout_s
        self._poll_interval_s = poll_interval_s
        self._poll_max_interval_s = poll_max_interval_s

    async def extract(
        self,
        *,
        documents: Optional[List[Tuple[str, bytes]]] = None,
        urls: Optional[List[str]] = None,
        alias: Optional[str] = None,
        description: Optional[str] = None,
        enrichment_mode: Optional[EnrichmentMode] = None,
    ) -> Dict[str, Any]:
        return await self._extract.extract(
            documents=documents,
            urls=urls,
            alias=alias,
            description=description,
            enrichment_mode=enrichment_mode,
        )

    async def extract_fields(
        self,
        *,
        json_schema: Dict[str, Any],
        documents: Optional[List[Tuple[str, bytes]]] = None,
        urls: Optional[List[str]] = None,
        alias: Optional[str] = None,
        description: Optional[str] = None,
    ) -> Dict[str, Any]:
        return await self._extract.extract_fields(
            json_schema=json_schema,
            documents=documents,
            urls=urls,
            alias=alias,
            description=description,
        )

    async def extract_fields_from_markdown(
        self,
        *,
        json_schema: Dict[str, Any],
        document_ids: List[str],
        alias: Optional[str] = None,
        description: Optional[str] = None,
    ) -> Dict[str, Any]:
        return await self._extract.extract_fields_from_markdown(
            json_schema=json_schema,
            document_ids=document_ids,
            alias=alias,
            description=description,
        )

    async def generate_schema(self, *, description: str) -> Dict[str, Any]:
        return await self._extract.generate_schema(description=description)

    async def list_tasks(self) -> Dict[str, Any]:
        return await self._tasks.list()

    async def make_zip(
        self,
        *,
        job_uid: str,
        document_uid: Optional[str] = None,
        local_images: bool = False,
        content_types: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        return await self._zip.make_zip(
            job_uid=job_uid,
            document_uid=document_uid,
            local_images=local_images,
            content_types=content_types,
        )

    @staticmethod
    def extract_request_uid(extract_response: Dict[str, Any]) -> str:
        """Return ``request_uid`` from an extract endpoint payload."""
        return _extract_request_uid(extract_response)

    @staticmethod
    def extract_document_ids(status_response: Dict[str, Any]) -> List[str]:
        """Return document IDs from a request-status payload."""
        return _extract_document_ids(status_response)

    @staticmethod
    def extract_markdown_document_ids(submit_response: Dict[str, Any]) -> List[str]:
        """Return the new ``document_uid``s from an extract-fields-from-markdown
        submit response's ``document_map`` (used for polling and scalar retrieval)."""
        return _extract_markdown_document_ids(submit_response)

    async def wait_for_request(
        self,
        request_uid: str,
        *,
        timeout_s: Optional[float] = None,
        poll_interval_s: Optional[float] = None,
        poll_max_interval_s: Optional[float] = None,
    ) -> Dict[str, Any]:
        async def _fetch() -> Dict[str, Any]:
            return await self.status.request(request_uid)

        return await wait_for_terminal_status_async(
            fetch_status=_fetch,
            extract_status=extract_status,
            timeout_s=self._timeout_s if timeout_s is None else timeout_s,
            poll_interval_s=(
                self._poll_interval_s if poll_interval_s is None else poll_interval_s
            ),
            poll_max_interval_s=(
                self._poll_max_interval_s
                if poll_max_interval_s is None
                else poll_max_interval_s
            ),
            identifier=f"request {request_uid}",
            timeout_context=_extraction_timeout_suffix,
        )
