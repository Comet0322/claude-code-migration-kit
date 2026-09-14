"""Tests for SecretClient. See boogie-sdk-api.md (this skill's library doc) section 5.1.

`get_secret` has a built-in TTL cache per the design doc, but the cache's
internal shape (eviction, backing store attribute names, clock source) is an
implementation detail the stub does not expose. Per the task brief, we keep
these tests to observable, black-box behavior: put/get round-trip, path
correctness, overwrite visibility, and not-found handling. TTL internals
(e.g. "a second get within TTL skips the backing store") are intentionally
left untested here rather than reaching into private attributes and locking
the implementer into one specific cache internal.
"""

from __future__ import annotations

import pytest

from boogie_sdk.core.errors import NotFoundError
from boogie_sdk.crypto.secret_client import Secret, SecretClient


@pytest.fixture
def client() -> SecretClient:
    return SecretClient()


def test_put_then_get_round_trip(client: SecretClient) -> None:
    client.put_secret("db/prod", {"user": "admin", "password": "hunter2"})

    secret = client.get_secret("db/prod")

    assert isinstance(secret, Secret)
    assert secret.path == "db/prod"
    assert secret.data == {"user": "admin", "password": "hunter2"}


def test_get_secret_returns_new_dataclass_instance_each_time(
    client: SecretClient,
) -> None:
    client.put_secret("db/prod", {"user": "admin"})

    first = client.get_secret("db/prod")
    second = client.get_secret("db/prod")

    assert first == second


def test_put_secret_overwrite_is_visible_on_next_get(client: SecretClient) -> None:
    client.put_secret("api/key", {"value": "old"})
    client.put_secret("api/key", {"value": "new"})

    secret = client.get_secret("api/key")

    assert secret.data == {"value": "new"}


def test_get_secret_for_unknown_path_raises_not_found_error(
    client: SecretClient,
) -> None:
    with pytest.raises(NotFoundError):
        client.get_secret("never/put/this/path")


def test_multiple_paths_are_independent(client: SecretClient) -> None:
    client.put_secret("a", {"v": "1"})
    client.put_secret("b", {"v": "2"})

    assert client.get_secret("a").data == {"v": "1"}
    assert client.get_secret("b").data == {"v": "2"}
