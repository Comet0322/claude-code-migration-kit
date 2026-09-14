"""CacheClient stub. See boogie-sdk-api.md (this skill's library doc) section 5.2 (infra).

Plain in-memory dict keyed by string, storing bytes values with per-key
expiry tracked via a monotonic clock (see
tests/infra/test_cache_client.py module docstring for the
pinned-down convention).
"""

from __future__ import annotations

import time
from datetime import timedelta
from typing import Callable


class CacheClient:
    def __init__(self) -> None:
        # key -> (value, expires_at_monotonic)
        self._store: dict[str, tuple[bytes, float]] = {}

    def get(self, key: str) -> bytes | None:
        entry = self._store.get(key)
        if entry is None:
            return None
        value, expires_at = entry
        if time.monotonic() >= expires_at:
            self._store.pop(key, None)
            return None
        return value

    def set(self, key: str, value: bytes, ttl: timedelta) -> None:
        expires_at = time.monotonic() + ttl.total_seconds()
        self._store[key] = (value, expires_at)

    def delete(self, key: str) -> None:
        self._store.pop(key, None)

    def get_or_compute(
        self, key: str, ttl: timedelta, loader: Callable[[], bytes]
    ) -> bytes:
        cached = self.get(key)
        if cached is not None:
            return cached
        value = loader()
        self.set(key, value, ttl)
        return value
