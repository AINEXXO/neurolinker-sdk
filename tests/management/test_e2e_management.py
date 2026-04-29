import os
import uuid

import pytest

from neurolinker_sdk import AsyncNeuroLinker, NeuroLinker

TOKEN = os.getenv("NEUROLINKER_API_KEY")

pytestmark = pytest.mark.skipif(
    not TOKEN,
    reason="Set NEUROLINKER_API_KEY to run this E2E test.",
)


def _unique_name(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


# ---------------------------------------------------------------------------
# Buckets — sync + async
# ---------------------------------------------------------------------------


def test_e2e_management_buckets_crud_sync() -> None:
    name = _unique_name("sdk-e2e-bucket")
    bucket_uid = None

    with NeuroLinker.from_env() as client:
        try:
            # create
            created = client.management.buckets.create(name=name)
            bucket_uid = created.get("bucket_uid")
            assert isinstance(bucket_uid, str) and bucket_uid, f"Missing bucket_uid: {created}"

            # get
            got = client.management.buckets.get(bucket_uid)
            assert got.get("bucket_uid") == bucket_uid
            assert got.get("name") == name

            # list — must include the new bucket
            listed = client.management.buckets.list()
            buckets = listed.get("buckets") if isinstance(listed, dict) else None
            assert isinstance(buckets, list)
            assert any(
                isinstance(b, dict) and b.get("bucket_uid") == bucket_uid for b in buckets
            ), f"Created bucket {bucket_uid} not found in list response."
        finally:
            if bucket_uid:
                client.management.buckets.delete(bucket_uid)


@pytest.mark.asyncio
async def test_e2e_management_buckets_crud_async() -> None:
    name = _unique_name("sdk-e2e-bucket")
    bucket_uid = None

    async with AsyncNeuroLinker.from_env() as client:
        try:
            created = await client.management.buckets.create(name=name)
            bucket_uid = created.get("bucket_uid")
            assert isinstance(bucket_uid, str) and bucket_uid

            got = await client.management.buckets.get(bucket_uid)
            assert got.get("bucket_uid") == bucket_uid
            assert got.get("name") == name

            listed = await client.management.buckets.list()
            buckets = listed.get("buckets") if isinstance(listed, dict) else None
            assert isinstance(buckets, list)
            assert any(
                isinstance(b, dict) and b.get("bucket_uid") == bucket_uid for b in buckets
            )
        finally:
            if bucket_uid:
                await client.management.buckets.delete(bucket_uid)


# ---------------------------------------------------------------------------
# Secrets — sync + async
# ---------------------------------------------------------------------------


def test_e2e_management_secrets_crud_sync() -> None:
    name = _unique_name("sdk_e2e_secret")
    secret_id = None

    with NeuroLinker.from_env() as client:
        try:
            created = client.management.secrets.create(name=name, value="initial-value")
            secret_id = created.get("secret_id") or created.get("id")
            assert isinstance(secret_id, str) and secret_id, f"Missing secret_id: {created}"

            listed = client.management.secrets.list()
            assert isinstance(listed, dict)

            # update
            client.management.secrets.update(secret_id, value="rotated-value")
        finally:
            if secret_id:
                client.management.secrets.delete(secret_id)


@pytest.mark.asyncio
async def test_e2e_management_secrets_crud_async() -> None:
    name = _unique_name("sdk_e2e_secret")
    secret_id = None

    async with AsyncNeuroLinker.from_env() as client:
        try:
            created = await client.management.secrets.create(name=name, value="initial-value")
            secret_id = created.get("secret_id") or created.get("id")
            assert isinstance(secret_id, str) and secret_id

            listed = await client.management.secrets.list()
            assert isinstance(listed, dict)

            await client.management.secrets.update(secret_id, value="rotated-value")
        finally:
            if secret_id:
                await client.management.secrets.delete(secret_id)
