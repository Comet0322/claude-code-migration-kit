"""ServiceDiscoveryClient stub. See boogie-sdk-api.md (this skill's library doc) section 5.2 (infra).

The design doc only documents `resolve`. `register` is an additive
convention required by the test suite to seed the fake registry — see
tests/infra/test_service_discovery_client.py module
docstring.
"""

from __future__ import annotations

from dataclasses import dataclass

from boogie_sdk.core.errors import NotFoundError


@dataclass(frozen=True)
class Endpoint:
    host: str
    port: int


class ServiceDiscoveryClient:
    def __init__(self) -> None:
        self._registry: dict[str, Endpoint] = {}

    def register(self, service_name: str, endpoint: Endpoint) -> None:
        self._registry[service_name] = endpoint

    def resolve(self, service_name: str) -> Endpoint:
        try:
            return self._registry[service_name]
        except KeyError:
            raise NotFoundError(f"service not registered: {service_name!r}") from None
