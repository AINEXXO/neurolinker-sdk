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
async def test_e2e_without_from_env() -> None:
    """
    E2E flow without using from_env().

    This test demonstrates that the SDK can be used with only a token,
    while base_url is automatically resolved to the default deployment URL.
    """
    # Build the client directly (no from_env).
    async with AsyncNeuroLinker(token=TOKEN) as client:
        # Submit extraction from URL and obtain the request UID.
        extract_resp = await client.extract.extract(
            urls=[PDF_URL],
            alias="sdk-no-from-env",
        )
        request_uid = client.extract_request_uid(extract_resp)

        # Wait for request completion using the built-in polling helper.
        status_resp = await client.wait_for_request_completion(request_uid)
        document_ids = client.extract_document_ids(status_resp)
        assert document_ids, f"No document IDs found in status response: {status_resp}"

        # Fetch one endpoint to validate the end-to-end flow.
        result = await client.documents.document_summary(document_ids)
        assert result.get("success") is True
        assert isinstance(result.get("results"), list)
