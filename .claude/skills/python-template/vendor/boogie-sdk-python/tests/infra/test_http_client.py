"""Tests for HttpClient. See boogie-sdk-api.md (this skill's library doc) section 5.2.

HttpClient is an in-memory fake: it never opens a real socket. Conventions
this test file pins down (no existing convention in the design doc or
stubs beyond method shapes):

- **Transport injection**: `HttpClient(transport=...)` accepts an optional
  callable `transport(method: str, url: str, body: bytes | None,
  headers: dict[str, str]) -> HttpResponse`. This is the seam the tests use
  to control responses deterministically instead of hitting a real network.
  A transport may also raise an exception to simulate a network failure;
  `HttpClient` is expected to catch that and drive its retry/backoff logic.
  With no transport given, the client must still be usable standalone and
  fall back to some canned/default response (a 200) for `get`/`post`.
- **Trace-id header**: the client auto-injects a `X-Trace-Id` header into
  every outgoing request (merged with any caller-supplied headers, caller
  headers must not be dropped). Each call gets its own unique trace id.
- **Retry/backoff**: when the transport raises, `get`/`post` retry a small,
  bounded number of times and return the eventual successful response if
  one of the retries succeeds. If every attempt fails, the client wraps the
  underlying failure in `InfraError` (never lets the raw transport
  exception escape). Tests keep retry counts small and never sleep for a
  meaningful amount of time, so the whole file stays fast.
"""

from __future__ import annotations

import pytest

from boogie_sdk.core.errors import InfraError
from boogie_sdk.infra.http_client import HttpClient, HttpResponse

# -- default transport / basic usability -------------------------------------


def test_default_transport_returns_a_response_without_configuration() -> None:
    client = HttpClient()
    response = client.get("http://example.invalid/resource")

    assert isinstance(response, HttpResponse)
    assert response.status_code == 200


# -- transport invocation -----------------------------------------------------


def test_get_calls_transport_with_method_url_and_headers() -> None:
    calls = []

    def transport(method, url, body, headers):
        calls.append((method, url, body, headers))
        return HttpResponse(status_code=200, body=b"ok")

    client = HttpClient(transport=transport)
    response = client.get("http://svc/x", headers={"Accept": "application/json"})

    assert response.status_code == 200
    assert response.body == b"ok"
    assert len(calls) == 1
    method, url, body, headers = calls[0]
    assert method.upper() == "GET"
    assert url == "http://svc/x"
    assert headers["Accept"] == "application/json"


def test_post_calls_transport_with_body() -> None:
    calls = []

    def transport(method, url, body, headers):
        calls.append((method, url, body, headers))
        return HttpResponse(status_code=201, body=b"created")

    client = HttpClient(transport=transport)
    response = client.post("http://svc/x", body=b"payload", headers={"X-Foo": "bar"})

    assert response.status_code == 201
    method, url, body, headers = calls[0]
    assert method.upper() == "POST"
    assert body == b"payload"
    assert headers["X-Foo"] == "bar"


# -- trace-id header injection ------------------------------------------------


def test_get_injects_trace_id_header() -> None:
    captured_headers = {}

    def transport(method, url, body, headers):
        captured_headers.update(headers)
        return HttpResponse(status_code=200)

    client = HttpClient(transport=transport)
    client.get("http://svc/x")

    assert "X-Trace-Id" in captured_headers
    assert captured_headers["X-Trace-Id"]  # non-empty


def test_trace_id_is_unique_per_call() -> None:
    seen_trace_ids = []

    def transport(method, url, body, headers):
        seen_trace_ids.append(headers["X-Trace-Id"])
        return HttpResponse(status_code=200)

    client = HttpClient(transport=transport)
    client.get("http://svc/x")
    client.get("http://svc/x")

    assert len(seen_trace_ids) == 2
    assert seen_trace_ids[0] != seen_trace_ids[1]


def test_caller_supplied_headers_are_preserved_alongside_trace_id() -> None:
    captured_headers = {}

    def transport(method, url, body, headers):
        captured_headers.update(headers)
        return HttpResponse(status_code=200)

    client = HttpClient(transport=transport)
    client.get("http://svc/x", headers={"Authorization": "Bearer t"})

    assert captured_headers["Authorization"] == "Bearer t"
    assert "X-Trace-Id" in captured_headers


# -- retry / backoff -----------------------------------------------------------


def test_get_retries_after_transient_transport_failures_then_succeeds() -> None:
    attempts = {"count": 0}

    def flaky_transport(method, url, body, headers):
        attempts["count"] += 1
        if attempts["count"] <= 2:
            raise ConnectionError("simulated network failure")
        return HttpResponse(status_code=200, body=b"finally ok")

    client = HttpClient(transport=flaky_transport)
    response = client.get("http://svc/x")

    assert response.status_code == 200
    assert response.body == b"finally ok"
    assert attempts["count"] == 3


def test_get_raises_infra_error_after_exhausting_retries() -> None:
    attempts = {"count": 0}

    def always_failing_transport(method, url, body, headers):
        attempts["count"] += 1
        raise ConnectionError("simulated permanent failure")

    client = HttpClient(transport=always_failing_transport)

    with pytest.raises(InfraError):
        client.get("http://svc/x")

    # Retried more than once but bounded (not an infinite loop).
    assert attempts["count"] > 1
    assert attempts["count"] <= 10


def test_post_raises_infra_error_after_exhausting_retries() -> None:
    def always_failing_transport(method, url, body, headers):
        raise TimeoutError("simulated timeout")

    client = HttpClient(transport=always_failing_transport)

    with pytest.raises(InfraError):
        client.post("http://svc/x", body=b"payload")
