"""Tests for ServiceDiscoveryClient. See boogie-sdk-api.md (this skill's library doc)
section 5.2.

**Additive convention beyond the design doc**: the design doc only
documents `resolve(service_name) -> Endpoint`. Since there is no real
registry behind this fake, `resolve` needs *something* to resolve against,
so this test file requires a `register(service_name, endpoint)` method on
`ServiceDiscoveryClient` that populates the fake registry. This is an
extension beyond the documented public API — flagged here explicitly so
the acceptance reviewer understands why it exists (a fake service registry
is useless without a way to seed it, and the design doc doesn't specify
one). `resolve` on a name that was never `register`-ed raises
`NotFoundError`.
"""

from __future__ import annotations

import pytest

from boogie_sdk.core.errors import NotFoundError
from boogie_sdk.infra.service_discovery_client import Endpoint, ServiceDiscoveryClient


@pytest.fixture
def client() -> ServiceDiscoveryClient:
    return ServiceDiscoveryClient()


def test_register_then_resolve_returns_the_registered_endpoint(
    client: ServiceDiscoveryClient,
) -> None:
    client.register("orders-service", Endpoint(host="10.0.0.5", port=8080))

    endpoint = client.resolve("orders-service")

    assert endpoint == Endpoint(host="10.0.0.5", port=8080)


def test_resolve_unregistered_service_raises_not_found_error(
    client: ServiceDiscoveryClient,
) -> None:
    with pytest.raises(NotFoundError):
        client.resolve("never-registered-service")


def test_register_overwrites_previous_endpoint_for_same_name(
    client: ServiceDiscoveryClient,
) -> None:
    client.register("svc", Endpoint(host="1.1.1.1", port=1))
    client.register("svc", Endpoint(host="2.2.2.2", port=2))

    assert client.resolve("svc") == Endpoint(host="2.2.2.2", port=2)


def test_multiple_services_are_resolved_independently(
    client: ServiceDiscoveryClient,
) -> None:
    client.register("svc-a", Endpoint(host="10.0.0.1", port=100))
    client.register("svc-b", Endpoint(host="10.0.0.2", port=200))

    assert client.resolve("svc-a") == Endpoint(host="10.0.0.1", port=100)
    assert client.resolve("svc-b") == Endpoint(host="10.0.0.2", port=200)
