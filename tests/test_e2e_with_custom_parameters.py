import os

import pytest

from neurolinker_sdk import AsyncNeuroLinker
from neurolinker_sdk.resources.documents import ContentType

TOKEN = os.getenv("NEUROLINKER_API_KEY")
PDF_URL = os.getenv("NEUROLINKER_TEST_PDF_URL")

pytestmark = pytest.mark.skipif(
    not TOKEN or not PDF_URL,
    reason="Set NEUROLINKER_API_KEY and NEUROLINKER_TEST_PDF_URL to run this E2E test.",
)


@pytest.mark.asyncio
async def test_e2e_with_explicit_client_parameters() -> None:
    """
    E2E flow using explicit client parameters.

    This test demonstrates how to override timeout and polling behavior,
    and how to pass optional extract/documents parameters.
    """
    # Build the client with explicit timeout and polling parameters.
    async with AsyncNeuroLinker(
        token=TOKEN,
        timeout_s=900.0,
        poll_interval_s=1.0,
        poll_max_interval_s=6.0,
    ) as client:
        # Submit extraction with optional metadata parameters.
        extract_resp = await client.extract.extract(
            urls=[PDF_URL],
            alias="sdk-custom-params",
            description="E2E test for explicit client parameters",
        )
        request_uid = client.extract_request_uid(extract_resp)

        # Override polling settings at call-time to show per-call control.
        status_resp = await client.wait_for_request_completion(
            request_uid,
            timeout_s=600.0,
            poll_interval_s=1.5,
            poll_max_interval_s=8.0,
        )
        document_ids = client.extract_document_ids(status_resp)
        assert document_ids, f"No document IDs found in status response: {status_resp}"

        # Use content_types to fetch a filtered markdown response.
        markdown = await client.documents.markdown(
            document_ids,
            content_types=[ContentType.TEXT],
        )
        assert markdown.get("success") is True
        assert isinstance(markdown.get("results"), list)
