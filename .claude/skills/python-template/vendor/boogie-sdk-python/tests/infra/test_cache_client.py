"""Tests for CacheClient. See boogie-sdk-api.md (this skill's library doc) section 5.2.

Convention pinned down by this test file: `CacheClient` is a plain
in-memory `dict` keyed by string, storing `bytes` values with per-key
expiry tracked via a monotonic clock. A missing or expired key returns
`None` from `get` (never raises, matching the `bytes | None` design-doc
return type). TTL expiry is exercised with a very short TTL
(`timedelta(milliseconds=1)`) plus a small sleep, keeping the whole file
well under a second. `get_or_compute(key, ttl, loader)` calls `loader()`
exactly once on a cache miss and must not call it again for a subsequent
hit within the TTL window.
"""

from __future__ import annotations

import time
from datetime import timedelta

import pytest

from boogie_sdk.infra.cache_client import CacheClient


@pytest.fixture
def client() -> CacheClient:
    return CacheClient()


# -- set / get ------------------------------------------------------------


def test_set_then_get_returns_the_value(client: CacheClient) -> None:
    client.set("k1", b"hello", ttl=timedelta(seconds=30))
    assert client.get("k1") == b"hello"


def test_get_missing_key_returns_none(client: CacheClient) -> None:
    assert client.get("does-not-exist") is None


def test_set_overwrites_previous_value(client: CacheClient) -> None:
    client.set("k1", b"first", ttl=timedelta(seconds=30))
    client.set("k1", b"second", ttl=timedelta(seconds=30))
    assert client.get("k1") == b"second"


# -- delete -----------------------------------------------------------------


def test_delete_removes_the_key(client: CacheClient) -> None:
    client.set("k1", b"hello", ttl=timedelta(seconds=30))
    client.delete("k1")
    assert client.get("k1") is None


def test_delete_missing_key_does_not_raise(client: CacheClient) -> None:
    client.delete("never-existed")  # should be a no-op, not an error


# -- TTL expiry ---------------------------------------------------------------


def test_get_returns_none_after_ttl_expires(client: CacheClient) -> None:
    client.set("k1", b"transient", ttl=timedelta(milliseconds=1))
    time.sleep(0.05)  # generous margin over the 1ms TTL, still fast overall
    assert client.get("k1") is None


def test_get_returns_value_before_ttl_expires(client: CacheClient) -> None:
    client.set("k1", b"still-fresh", ttl=timedelta(seconds=30))
    assert client.get("k1") == b"still-fresh"


# -- get_or_compute -----------------------------------------------------------


def test_get_or_compute_calls_loader_on_miss_and_returns_its_value(
    client: CacheClient,
) -> None:
    calls = {"count": 0}

    def loader() -> bytes:
        calls["count"] += 1
        return b"computed-value"

    result = client.get_or_compute("k1", ttl=timedelta(seconds=30), loader=loader)

    assert result == b"computed-value"
    assert calls["count"] == 1


def test_get_or_compute_does_not_call_loader_again_on_subsequent_hit(
    client: CacheClient,
) -> None:
    calls = {"count": 0}

    def loader() -> bytes:
        calls["count"] += 1
        return b"computed-value"

    first = client.get_or_compute("k1", ttl=timedelta(seconds=30), loader=loader)
    second = client.get_or_compute("k1", ttl=timedelta(seconds=30), loader=loader)

    assert first == second == b"computed-value"
    assert calls["count"] == 1


def test_get_or_compute_calls_loader_again_after_ttl_expires(
    client: CacheClient,
) -> None:
    calls = {"count": 0}

    def loader() -> bytes:
        calls["count"] += 1
        return f"value-{calls['count']}".encode()

    first = client.get_or_compute("k1", ttl=timedelta(milliseconds=1), loader=loader)
    time.sleep(0.05)
    second = client.get_or_compute("k1", ttl=timedelta(milliseconds=1), loader=loader)

    assert calls["count"] == 2
    assert first != second


def test_get_or_compute_populates_the_cache_so_plain_get_sees_it(
    client: CacheClient,
) -> None:
    def loader() -> bytes:
        return b"populated"

    client.get_or_compute("k1", ttl=timedelta(seconds=30), loader=loader)

    assert client.get("k1") == b"populated"
