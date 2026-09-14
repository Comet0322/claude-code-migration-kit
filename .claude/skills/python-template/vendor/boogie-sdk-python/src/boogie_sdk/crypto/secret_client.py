"""SecretClient stub. See boogie-sdk-api.md (this skill's library doc) section 5.1 (crypto).

Simulated in-memory secret store, keyed by an opaque ``path`` string. Per the
design doc ``get_secret`` has a "built-in TTL cache" -- since this fake never
talks to a real backing store there is nothing to cache *from*, so the store
below is simply the source of truth. A dict-based TTL cache layer could be
added later without changing the observable behavior the tests assert on.
"""

from __future__ import annotations

from dataclasses import dataclass

from boogie_sdk.core.errors import NotFoundError


@dataclass(frozen=True)
class Secret:
    path: str
    data: dict[str, str]


class SecretClient:
    def __init__(self) -> None:
        self._store: dict[str, dict[str, str]] = {}

    def get_secret(self, path: str) -> Secret:
        try:
            data = self._store[path]
        except KeyError as exc:
            raise NotFoundError(f"no secret at path: {path!r}") from exc
        return Secret(path=path, data=dict(data))

    def put_secret(self, path: str, data: dict[str, str]) -> None:
        self._store[path] = dict(data)
