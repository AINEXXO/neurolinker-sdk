from __future__ import annotations

import json
from typing import Any, Dict, Optional, Tuple

import httpx

from .errors import NeuroLinkerAPIError


def _raise_for_status(resp: httpx.Response) -> None:
    if 200 <= resp.status_code < 300:
        return

    text = resp.text
    parsed: Optional[object] = None
    try:
        parsed = resp.json()
    except Exception:
        parsed = None

    raise NeuroLinkerAPIError(
        status_code=resp.status_code,
        method=resp.request.method,
        url=str(resp.request.url),
        response_text=text,
        response_json=parsed,
    )


def _json_headers(token: str) -> Dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
    }


def _build_url(base_url: str, path: str) -> str:
    # base_url should already be stripped of trailing slash.
    if not path.startswith("/"):
        path = "/" + path
    return base_url + path


def _coerce_files(
    documents: Optional[list[tuple[str, bytes]]],
) -> Optional[list[Tuple[str, Tuple[str, bytes, str]]]]:
    """
    Convert input documents into httpx 'files' format:
      files=[("documents", ("file0.pdf", b"...", "application/pdf")), ...]
    """
    if not documents:
        return None

    files: list[Tuple[str, Tuple[str, bytes, str]]] = []
    for idx, (filename, content) in enumerate(documents):
        safe_name = filename or f"document_{idx}.pdf"
        files.append(("documents", (safe_name, content, "application/pdf")))
    return files


def _encode_form_payload(
    urls: Optional[list[str]],
    alias: Optional[str],
    description: Optional[str] = None,
) -> str:
    """
    Build the JSON payload sent in the `form` field for URL-based extraction.

    The backend expects:
      - `documents_url`: list of URLs to download documents from
      - `alias`: optional alias for the request
      - `description`: optional description for the request
    """
    payload: Dict[str, Any] = {}

    if urls:
        payload["documents_url"] = urls
    if alias:
        payload["alias"] = alias
    if description:
        payload["description"] = description

    return json.dumps(payload)