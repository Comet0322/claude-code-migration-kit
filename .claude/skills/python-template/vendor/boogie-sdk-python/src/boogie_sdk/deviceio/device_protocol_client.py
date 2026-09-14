"""DeviceProtocolClient stub. See boogie-sdk-api.md (this skill's library doc) section 5.3 (deviceio).

Skeleton only — implemented during the Phase 1 TDD loop for the `deviceio` module.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from boogie_sdk.core.errors import DeviceIoError


@dataclass(frozen=True)
class DeviceCommand:
    name: str
    args: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class DeviceEvent:
    name: str
    payload: dict[str, Any] = field(default_factory=dict)


class DeviceProtocolClient:
    def __init__(self) -> None:
        self._connected = False
        self._handlers: list[Callable[[DeviceEvent], None]] = []

    @property
    def is_connected(self) -> bool:
        return self._connected

    def connect(self, endpoint: str) -> None:
        self._connected = True

    def send_command(self, cmd: DeviceCommand) -> None:
        if not self._connected:
            raise DeviceIoError("Cannot send command: client is not connected")

    def on_event(self, handler: Callable[[DeviceEvent], None]) -> None:
        self._handlers.append(handler)

    def simulate_event(self, event: DeviceEvent) -> None:
        for handler in self._handlers:
            handler(event)

    def disconnect(self) -> None:
        self._connected = False
