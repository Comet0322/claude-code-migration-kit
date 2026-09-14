"""Tests for DeviceProtocolClient. See boogie-sdk-api.md (this skill's library doc)
section 5.3 (deviceio).

There is no real device/socket behind this fake — `connect(endpoint)` simply
records connection state in-memory, `send_command` validates that state, and
`on_event`/`disconnect` are plain bookkeeping. Conventions invented for
testability (documented here since the design doc doesn't spell them out):

- **`is_connected` property (additive)**: exposes whether the client is
  currently connected, so tests can observe `connect()`/`disconnect()`
  effects without depending on internals. Starts `False`, becomes `True`
  after a successful `connect()`, and goes back to `False` after
  `disconnect()`.
- **`send_command` before `connect()` raises `DeviceIoError`.** Likewise,
  calling `send_command` *after* `disconnect()` raises `DeviceIoError` again
  — connection state is not "sticky" once torn down.
- **`simulate_event(event: DeviceEvent)` (additive)**: since no real device
  exists to emit an event, this method invokes every handler registered via
  `on_event`, in registration order, with the given `DeviceEvent`. This is a
  test-only affordance for driving the event-handling path deterministically.
- `on_event` supports registering multiple handlers; all of them fire on
  `simulate_event`.
"""

from __future__ import annotations

import pytest

from boogie_sdk.core.errors import DeviceIoError
from boogie_sdk.deviceio.device_protocol_client import (
    DeviceCommand,
    DeviceEvent,
    DeviceProtocolClient,
)


@pytest.fixture
def client() -> DeviceProtocolClient:
    return DeviceProtocolClient()


# -- connect / is_connected ---------------------------------------------------


def test_not_connected_before_connect(client: DeviceProtocolClient) -> None:
    assert client.is_connected is False


def test_connect_marks_client_connected(client: DeviceProtocolClient) -> None:
    client.connect("device://line-1")
    assert client.is_connected is True


def test_disconnect_clears_connection_state(client: DeviceProtocolClient) -> None:
    client.connect("device://line-1")
    client.disconnect()
    assert client.is_connected is False


def test_disconnect_without_connect_is_safe(client: DeviceProtocolClient) -> None:
    # Disconnecting a never-connected client should not raise.
    client.disconnect()
    assert client.is_connected is False


# -- send_command --------------------------------------------------------------


def test_send_command_before_connect_raises_device_io_error(
    client: DeviceProtocolClient,
) -> None:
    with pytest.raises(DeviceIoError):
        client.send_command(DeviceCommand(name="START"))


def test_send_command_after_connect_succeeds(client: DeviceProtocolClient) -> None:
    client.connect("device://line-1")
    # Should not raise.
    client.send_command(DeviceCommand(name="START", args={"speed": 5}))


def test_send_command_after_disconnect_raises_device_io_error(
    client: DeviceProtocolClient,
) -> None:
    client.connect("device://line-1")
    client.disconnect()
    with pytest.raises(DeviceIoError):
        client.send_command(DeviceCommand(name="STOP"))


# -- on_event / simulate_event -------------------------------------------------


def test_simulate_event_invokes_registered_handler(
    client: DeviceProtocolClient,
) -> None:
    received: list[DeviceEvent] = []
    client.on_event(received.append)

    event = DeviceEvent(name="alarm", payload={"code": 42})
    client.simulate_event(event)

    assert received == [event]


def test_simulate_event_invokes_all_registered_handlers_in_order(
    client: DeviceProtocolClient,
) -> None:
    calls: list[str] = []
    client.on_event(lambda evt: calls.append(f"first:{evt.name}"))
    client.on_event(lambda evt: calls.append(f"second:{evt.name}"))

    client.simulate_event(DeviceEvent(name="ping"))

    assert calls == ["first:ping", "second:ping"]


def test_simulate_event_with_no_handlers_does_not_raise(
    client: DeviceProtocolClient,
) -> None:
    # No handlers registered — simulate_event should be a no-op, not an error.
    client.simulate_event(DeviceEvent(name="ping"))


def test_simulate_event_works_regardless_of_connection_state(
    client: DeviceProtocolClient,
) -> None:
    # Event delivery is independent of connect()/disconnect() bookkeeping —
    # only send_command is gated on connection state.
    received: list[DeviceEvent] = []
    client.on_event(received.append)

    event = DeviceEvent(name="alarm")
    client.simulate_event(event)

    assert received == [event]
