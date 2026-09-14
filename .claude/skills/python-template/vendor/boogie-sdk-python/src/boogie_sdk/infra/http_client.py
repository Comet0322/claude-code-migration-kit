"""HttpClient stub. See boogie-sdk-api.md (this skill's library doc) section 5.2 (infra).

Implements the `infra` module's fake HTTP client: in-memory, transport-
injectable, with trace-id header injection and retry/backoff. See
tests/infra/test_http_client.py for the pinned-down
conventions.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, Callable

from boogie_sdk.core.errors import InfraError

Transport = Callable[[str, str, "bytes | None", dict[str, str]], "HttpResponse"]


@dataclass(frozen=True)
class HttpResponse:
    status_code: int
    headers: dict[str, str] = field(default_factory=dict)
    body: bytes = b""


def _default_transport(
    method: str, url: str, body: bytes | None, headers: dict[str, str]
) -> HttpResponse:
    return HttpResponse(status_code=200, body=b"")


class HttpClient:
    _MAX_ATTEMPTS = 3

    def __init__(self, transport: Transport | None = None) -> None:
        self._transport: Transport = transport if transport is not None else _default_transport

    def get(self, url: str, headers: dict[str, str] | None = None) -> HttpResponse:
        return self._request("GET", url, body=None, headers=headers)

    def post(
        self, url: str, body: bytes, headers: dict[str, str] | None = None
    ) -> HttpResponse:
        return self._request("POST", url, body=body, headers=headers)

    def _request(
        self,
        method: str,
        url: str,
        body: bytes | None,
        headers: dict[str, str] | None,
    ) -> HttpResponse:
        merged_headers = dict(headers or {})
        merged_headers["X-Trace-Id"] = str(uuid.uuid4())

        last_error: Exception | None = None
        for _attempt in range(self._MAX_ATTEMPTS):
            try:
                return self._transport(method, url, body, merged_headers)
            except Exception as exc:  # noqa: BLE001 - deliberately broad: any transport failure
                last_error = exc

        raise InfraError(
            f"{method} {url} failed after {self._MAX_ATTEMPTS} attempts: {last_error}"
        ) from last_error
