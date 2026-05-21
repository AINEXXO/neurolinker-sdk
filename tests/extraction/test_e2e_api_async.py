import os
import time
import asyncio
import pytest

from neurolinker_sdk import AsyncNeuroLinker
from neurolinker_sdk.errors import NeuroLinkerAPIError


TOKEN = os.getenv("NEUROLINKER_API_KEY")
PDF_URL = os.getenv("NEUROLINKER_TEST_PDF_URL")

E2E_TIMEOUT_S = float(os.getenv("NEUROLINKER_E2E_TIMEOUT_S", "600"))
POLL_INTERVAL_S = float(os.getenv("NEUROLINKER_E2E_POLL_INTERVAL_S", "2"))
POLL_MAX_INTERVAL_S = float(os.getenv("NEUROLINKER_E2E_POLL_MAX_INTERVAL_S", "10"))

pytestmark = pytest.mark.skipif(
    not TOKEN or not PDF_URL,
    reason="Set NEUROLINKER_API_KEY and NEUROLINKER_TEST_PDF_URL to run URL E2E tests.",
)


def _extract_request_uid(extract_response: dict) -> str:
    if isinstance(extract_response.get("request_uid"), str):
        return extract_response["request_uid"]
    data = extract_response.get("data")
    if isinstance(data, dict) and isinstance(data.get("request_uid"), str):
        return data["request_uid"]
    raise AssertionError(f"Could not find request_uid in extract response: {extract_response}")


def _extract_document_ids_from_request_status(status_response: dict) -> list[str]:
    documents = status_response.get("documents")
    if documents is None and isinstance(status_response.get("data"), dict):
        documents = status_response["data"].get("documents")

    if not isinstance(documents, list):
        return []

    out: list[str] = []
    for d in documents:
        if not isinstance(d, dict):
            continue
        if isinstance(d.get("document_id"), str):
            out.append(d["document_id"])
        elif isinstance(d.get("id"), str):
            out.append(d["id"])
    return out


async def _wait_for_request_completion(client: AsyncNeuroLinker, request_uid: str) -> dict:
    deadline = time.time() + E2E_TIMEOUT_S
    last = None
    interval = POLL_INTERVAL_S

    while time.time() < deadline:
        try:
            last = await client.extraction.status.request(request_uid)
        except NeuroLinkerAPIError as e:
            if e.status_code == 404:
                await asyncio.sleep(interval)
                interval = min(POLL_MAX_INTERVAL_S, interval * 1.5)
                continue
            raise

        status = last.get("status")
        if status is None and isinstance(last.get("data"), dict):
            status = last["data"].get("status")

        if status in ("completed", "failed", "pending"):
            return last

        await asyncio.sleep(interval)
        interval = min(POLL_MAX_INTERVAL_S, interval * 1.2)

    job_url = None
    if isinstance(last, dict):
        job_url = last.get("job_page_url") or (last.get("data", {}) or {}).get("job_page_url")

    raise AssertionError(
        f"Timeout waiting for request {request_uid} after {E2E_TIMEOUT_S}s. "
        f"Last status: {last}. Job URL: {job_url}"
    )


def _assert_documents_results_schema(payload: dict) -> None:
    assert isinstance(payload, dict)
    assert "success" in payload
    assert "results" in payload
    assert isinstance(payload["results"], list)


@pytest.mark.asyncio
async def test_e2e_all_public_endpoints_async():
    """
    URL-mode E2E (async).
    """
    async with AsyncNeuroLinker.from_env() as client:
        tasks = await client.extraction.list_tasks()
        assert isinstance(tasks, dict)
        assert "success" in tasks

        extract_resp = await client.extraction.extract(
            urls=[PDF_URL],
            alias="sdk-e2e-test-async",
            description="Description for sdk-e2e-test-async",
        )
        request_uid = _extract_request_uid(extract_resp)

        status_resp = await _wait_for_request_completion(client, request_uid)
        doc_ids = _extract_document_ids_from_request_status(status_resp)
        assert doc_ids, f"No document ids found in request-status: {status_resp}"

        doc_status = await client.extraction.status.document(doc_ids[0])
        assert isinstance(doc_status, dict)
        assert "success" in doc_status

        res_json = await client.extraction.documents.json(doc_ids)
        _assert_documents_results_schema(res_json)

        res_md = await client.extraction.documents.markdown(doc_ids)
        _assert_documents_results_schema(res_md)

        res_sum = await client.extraction.documents.document_summary(doc_ids, summary_type="page")
        _assert_documents_results_schema(res_sum)

        res_pages = await client.extraction.documents.page_summaries(doc_ids)
        _assert_documents_results_schema(res_pages)

        res_images = await client.extraction.documents.images(doc_ids)
        _assert_documents_results_schema(res_images)
