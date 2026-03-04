import os
import pytest

from neurolinker_sdk import AsyncNeuroLinker, NeuroLinker

from test_e2e_api_async import (
    _extract_request_uid as _extract_request_uid_async,
    _extract_document_ids_from_request_status,
    _wait_for_request_completion as _wait_for_request_completion_async,
)
from test_e2e_api_sync_local import (
    _extract_request_uid as _extract_request_uid_sync,
    _wait_for_request_completion as _wait_for_request_completion_sync,
)

TOKEN = os.getenv("NEUROLINKER_API_KEY")
PDF_URL = os.getenv("NEUROLINKER_TEST_PDF_URL")
NEUROLINKER_BASE_URL = os.getenv("NEUROLINKER_BASE_URL")
E2E_TIMEOUT_S = float(os.getenv("NEUROLINKER_E2E_TIMEOUT_S", "600"))

pytestmark = pytest.mark.skipif(
    not TOKEN or not PDF_URL,
    reason="Set NEUROLINKER_API_KEY and NEUROLINKER_TEST_PDF_URL to run URL E2E tests.",
)


@pytest.mark.asyncio
async def test_make_zip_async() -> None:
    """End-to-end test for the make-zip endpoint using the async SDK client.

    Flow:
      1) submit an extract request for a remote PDF URL
      2) wait for the request to complete
      3) call make-zip for the whole job
      4) call make-zip for a single document
    """
    async with AsyncNeuroLinker(token=TOKEN, base_url=NEUROLINKER_BASE_URL).from_env(timeout_s=E2E_TIMEOUT_S) as client:
        # 1) Submit extract request
        extract_resp = await client.extract.extract(
            urls=[PDF_URL],
            alias="sdk-e2e-makezip-async",
        )
        request_uid = _extract_request_uid_async(extract_resp)

        # 2) Wait until the request reaches a terminal state
        status_resp = await _wait_for_request_completion_async(client, request_uid)
        doc_ids = _extract_document_ids_from_request_status(status_resp)
        assert doc_ids, f"No document ids found in request-status: {status_resp}"

        # 3) make-zip for the entire job
        job_zip = await client.zip.make_zip(
            job_uid=request_uid,
            local_images=True,
        )
        assert isinstance(job_zip, dict)
        assert job_zip.get("success") is True
        assert isinstance(job_zip.get("url"), str)
        assert job_zip["url"].startswith("http")

        # Print URL so it is easy to manually download the archive
        print(f"[ASYNC] Job ZIP URL: {job_zip['url']}")

        # 4) make-zip for a single document
        doc_zip = await client.zip.make_zip(
            job_uid=request_uid,
            document_uid=doc_ids[0],
            content_types=["text"],
        )
        assert isinstance(doc_zip, dict)
        assert doc_zip.get("success") is True
        assert isinstance(doc_zip.get("url"), str)
        assert doc_zip["url"].startswith("http")

        print(f"[ASYNC] Document ZIP URL (document_id={doc_ids[0]}): {doc_zip['url']}")


def test_make_zip_sync() -> None:
    """End-to-end test for the make-zip endpoint using the sync SDK client.

    This mirrors the async test but uses the synchronous NeuroLinker client.
    """
    with NeuroLinker.from_env(timeout_s=E2E_TIMEOUT_S) as client:
        # 1) Submit extract request
        extract_resp = client.extract.extract(
            urls=[PDF_URL],
            alias="sdk-e2e-makezip-sync",
        )
        request_uid = _extract_request_uid_sync(extract_resp)

        # 2) Wait until the request reaches a terminal state
        status_resp = _wait_for_request_completion_sync(client, request_uid)
        doc_ids = _extract_document_ids_from_request_status(status_resp)
        assert doc_ids, f"No document ids found in request-status: {status_resp}"

        # 3) make-zip for the entire job
        job_zip = client.zip.make_zip(
            job_uid=request_uid,
            # New endpoint capability: filter JSON/MD output by content type
            content_types=["text"],
        )
        assert isinstance(job_zip, dict)
        assert job_zip.get("success") is True
        assert isinstance(job_zip.get("url"), str)
        assert job_zip["url"].startswith("http")

        print(f"[SYNC] Job ZIP URL: {job_zip['url']}")

        # 4) make-zip for a single document
        doc_zip = client.zip.make_zip(
            job_uid=request_uid,
            document_uid=doc_ids[0],
            content_types=["text"],
        )
        assert isinstance(doc_zip, dict)
        assert doc_zip.get("success") is True
        assert isinstance(doc_zip.get("url"), str)
        assert doc_zip["url"].startswith("http")

        print(f"[SYNC] Document ZIP URL (document_id={doc_ids[0]}): {doc_zip['url']}")