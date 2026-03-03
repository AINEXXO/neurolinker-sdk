import os

import pytest

from neurolinker_sdk import AsyncNeuroLinker

TOKEN = os.getenv("NEUROLINKER_API_KEY")
PDF_URL = os.getenv("NEUROLINKER_TEST_PDF_URL")

pytestmark = pytest.mark.skipif(
    not TOKEN or not PDF_URL,
    reason="Set NEUROLINKER_API_KEY and NEUROLINKER_TEST_PDF_URL to run this E2E test.",
)


@pytest.mark.asyncio
async def test_e2e_minimal_sdk_usage() -> None:
    """
    Minimal end-to-end SDK flow using the new client helpers.

    Steps:
      1) submit extract request from URL
      2) wait for completion with built-in polling helper
      3) get document ids with built-in parser helper
      4) fetch JSON result for extracted documents
    """
    async with AsyncNeuroLinker.from_env() as client:
        extract_resp = await client.extract.extract(urls=[PDF_URL], alias="sdk-minimal-e2e")
        request_uid = client.extract_request_uid(extract_resp)

        status_resp = await client.wait_for_request_completion(request_uid)
        document_ids = client.extract_document_ids(status_resp)
        assert document_ids, f"No document IDs found in request status: {status_resp}"

        docs_json = await client.documents.json(document_ids)
        assert isinstance(docs_json, dict)
        assert docs_json.get("success") is True
        assert isinstance(docs_json.get("results"), list)
