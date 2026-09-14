"""Tests for ObjectStorageClient. See boogie-sdk-api.md (this skill's library doc)
section 5.2.

Convention pinned down by this test file: `ObjectStorageClient` is backed
by an in-memory `dict[(bucket, key), bytes]`. `download` on a bucket/key
pair that was never `upload`-ed raises `NotFoundError` (per the shared
exception hierarchy in `boogie_sdk.core.errors`). `presign_url` returns a
non-empty deterministic string containing both the bucket and key — this
test file documents (but does not lock down byte-for-byte) the suggested
scheme `boogie-fake://<bucket>/<key>?...`; tests only assert the string is
non-empty and contains the bucket and key, not the exact query-string
format, so the implementer has room to add ttl/signature-looking params.
"""

from __future__ import annotations

from datetime import timedelta

import pytest

from boogie_sdk.core.errors import NotFoundError
from boogie_sdk.infra.object_storage_client import ObjectStorageClient


@pytest.fixture
def client() -> ObjectStorageClient:
    return ObjectStorageClient()


# -- upload / download --------------------------------------------------------


def test_upload_then_download_round_trips_bytes(client: ObjectStorageClient) -> None:
    client.upload("my-bucket", "path/to/file.txt", b"file contents")

    assert client.download("my-bucket", "path/to/file.txt") == b"file contents"


def test_download_missing_key_raises_not_found_error(
    client: ObjectStorageClient,
) -> None:
    with pytest.raises(NotFoundError):
        client.download("my-bucket", "never-uploaded.txt")


def test_upload_overwrites_previous_value_for_same_bucket_and_key(
    client: ObjectStorageClient,
) -> None:
    client.upload("my-bucket", "k", b"first")
    client.upload("my-bucket", "k", b"second")

    assert client.download("my-bucket", "k") == b"second"


def test_same_key_in_different_buckets_is_isolated(
    client: ObjectStorageClient,
) -> None:
    client.upload("bucket-a", "k", b"from-a")
    client.upload("bucket-b", "k", b"from-b")

    assert client.download("bucket-a", "k") == b"from-a"
    assert client.download("bucket-b", "k") == b"from-b"


def test_download_missing_key_in_bucket_that_has_other_keys_raises(
    client: ObjectStorageClient,
) -> None:
    client.upload("my-bucket", "existing-key", b"data")

    with pytest.raises(NotFoundError):
        client.download("my-bucket", "other-key")


# -- presign_url ---------------------------------------------------------------


def test_presign_url_returns_non_empty_string_containing_bucket_and_key(
    client: ObjectStorageClient,
) -> None:
    url = client.presign_url("my-bucket", "path/to/file.txt", ttl=timedelta(minutes=5))

    assert isinstance(url, str)
    assert url
    assert "my-bucket" in url
    assert "path/to/file.txt" in url


def test_presign_url_does_not_require_the_object_to_exist(
    client: ObjectStorageClient,
) -> None:
    # Presigning is just URL generation, not an existence check.
    url = client.presign_url("my-bucket", "not-uploaded-yet", ttl=timedelta(minutes=5))
    assert url
