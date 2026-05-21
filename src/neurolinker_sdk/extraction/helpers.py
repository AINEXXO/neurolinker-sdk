from __future__ import annotations

from typing import Any, Dict, List, Optional


def extract_request_uid(extract_response: Dict[str, Any]) -> str:
    """Extract request UID from an extract endpoint payload."""
    if isinstance(extract_response.get("request_uid"), str):
        return extract_response["request_uid"]

    data = extract_response.get("data")
    if isinstance(data, dict) and isinstance(data.get("request_uid"), str):
        return data["request_uid"]

    raise ValueError(f"Could not find request_uid in extract response: {extract_response}")


def extract_document_ids(status_response: Dict[str, Any]) -> List[str]:
    """Extract document IDs from request-status payload with minimal shape assumptions."""
    documents = status_response.get("documents")
    if documents is None and isinstance(status_response.get("data"), dict):
        documents = status_response["data"].get("documents")

    if not isinstance(documents, list):
        return []

    out: List[str] = []
    for item in documents:
        if not isinstance(item, dict):
            continue
        if isinstance(item.get("document_id"), str):
            out.append(item["document_id"])
        elif isinstance(item.get("id"), str):
            out.append(item["id"])
    return out


def extract_status(response: Dict[str, Any]) -> Optional[str]:
    """Extract status from a request-status payload."""
    status = response.get("status")
    if status is None and isinstance(response.get("data"), dict):
        status = response["data"].get("status")
    return status if isinstance(status, str) else None
