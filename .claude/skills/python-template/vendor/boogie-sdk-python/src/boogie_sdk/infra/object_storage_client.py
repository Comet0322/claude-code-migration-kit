"""ObjectStorageClient stub. See boogie-sdk-api.md (this skill's library doc) section 5.2 (infra).

Backed by an in-memory `dict[(bucket, key), bytes]` (see
tests/infra/test_object_storage_client.py module
docstring for the pinned-down convention).
"""

from __future__ import annotations

from datetime import timedelta

from boogie_sdk.core.errors import NotFoundError


class ObjectStorageClient:
    def __init__(self) -> None:
        self._objects: dict[tuple[str, str], bytes] = {}

    def upload(self, bucket: str, key: str, data: bytes) -> None:
        self._objects[(bucket, key)] = data

    def download(self, bucket: str, key: str) -> bytes:
        try:
            return self._objects[(bucket, key)]
        except KeyError:
            raise NotFoundError(f"object not found: bucket={bucket!r} key={key!r}") from None

    def presign_url(self, bucket: str, key: str, ttl: timedelta) -> str:
        return f"boogie-fake://{bucket}/{key}?ttl={int(ttl.total_seconds())}&sig=fake"
