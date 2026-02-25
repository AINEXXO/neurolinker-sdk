from __future__ import annotations

from typing import Any, Dict, Optional

import httpx

from ..http import _build_url, _json_headers, _raise_for_status


class ZipResource:
    """
    Synchronous helper around the make-zip endpoint.

    This is a thin convenience wrapper over:
        POST /api/v1/mcp/make-zip

    The endpoint returns a short-lived signed URL that can be used to download
    the generated ZIP file directly from storage.
    """

    def __init__(self, base_url: str, token: str, client: httpx.Client):
        self._base_url = base_url
        self._token = token
        self._client = client

    def make_zip(
        self,
        *,
        job_uid: str,
        document_uid: Optional[str] = None,
        local_images: bool = False,
    ) -> Dict[str, Any]:
        """
        Request a ZIP archive for a completed extraction job.

        Parameters
        ----------
        job_uid:
            The request UID of the extraction job. This is mapped directly
            to the `request_id` field of the backend MakeZipRequest model.
        document_uid:
            Optional single document UID. If omitted, the ZIP will contain
            data for the entire job.
        local_images:
            When True, JSON/Markdown files will be rewritten to reference
            images using local relative paths instead of full URLs.

        Returns
        -------
        Dict[str, Any]
            JSON payload returned by the API, typically:
            {"success": true, "url": "...", "message": "..."}.
        """
        url = _build_url(self._base_url, "/api/v1/mcp/make-zip")

        # IMPORTANT:
        # The backend MakeZipRequest model expects:
        #   request_id, document_id, local_images
        # so we map our SDK parameter names accordingly.
        body: Dict[str, Any] = {
            "request_id": job_uid,
            "local_images": local_images,
        }
        if document_uid is not None:
            body["document_id"] = document_uid

        resp = self._client.post(url, json=body, headers=_json_headers(self._token))
        _raise_for_status(resp)
        return resp.json()


class AsyncZipResource:
    """
    Async helper around the make-zip endpoint.
    """

    def __init__(self, base_url: str, token: str, client: httpx.AsyncClient):
        self._base_url = base_url
        self._token = token
        self._client = client

    async def make_zip(
        self,
        *,
        job_uid: str,
        document_uid: Optional[str] = None,
        local_images: bool = False,
    ) -> Dict[str, Any]:
        """
        Async variant of ZipResource.make_zip.
        """
        url = _build_url(self._base_url, "/api/v1/mcp/make-zip")

        body: Dict[str, Any] = {
            "request_id": job_uid,
            "local_images": local_images,
        }
        if document_uid is not None:
            body["document_id"] = document_uid

        resp = await self._client.post(
            url,
            json=body,
            headers=_json_headers(self._token),
        )
        _raise_for_status(resp)
        return resp.json()