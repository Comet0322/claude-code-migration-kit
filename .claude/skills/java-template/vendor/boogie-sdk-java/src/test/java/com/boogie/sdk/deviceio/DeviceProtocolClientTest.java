package com.boogie.sdk.deviceio;

import com.boogie.sdk.core.DeviceIoException;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.assertDoesNotThrow;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

/**
 * Tests for DeviceProtocolClient. See boogie-sdk-api.md section 5.3 (deviceio).
 *
 * <p>There is no real device/socket behind this fake — {@code connect(endpoint)}
 * simply records connection state in-memory, {@code sendCommand} validates that
 * state, and {@code onEvent}/{@code disconnect} are plain bookkeeping.
 * Conventions this test file pins down (none exist yet beyond the design doc's
 * public method shapes), mirroring the already-built Python port's {@code
 * DeviceProtocolClient}:
 *
 * <ul>
 *   <li><b>{@code isConnected()} (additive, not in the design doc):</b>
 *       exposes whether the client is currently connected, so tests can
 *       observe {@code connect()}/{@code disconnect()} effects without
 *       depending on internals. Starts {@code false}, becomes {@code true}
 *       after a successful {@code connect()}, and goes back to {@code
 *       false} after {@code disconnect()}. {@code disconnect()} on a
 *       never-connected client is safe (does not throw).
 *   <li><b>{@code sendCommand} before {@code connect()} throws {@link
 *       DeviceIoException}.</b> Likewise, calling {@code sendCommand}
 *       <i>after</i> {@code disconnect()} throws {@link DeviceIoException}
 *       again — connection state is not "sticky" once torn down.
 *   <li><b>{@code simulateEvent(DeviceEvent)} (additive, not in the design
 *       doc):</b> since no real device exists to emit an event, this method
 *       invokes every handler registered via {@code onEvent}, in
 *       registration order, with the given {@code DeviceEvent}. This is a
 *       test-only affordance for driving the event-handling path
 *       deterministically. Event delivery via {@code simulateEvent} is
 *       independent of connection state — only {@code sendCommand} is
 *       gated on it.
 *   <li>{@code onEvent} supports registering multiple handlers; all of
 *       them fire, in registration order, on {@code simulateEvent}.
 * </ul>
 */
class DeviceProtocolClientTest {

    private DeviceProtocolClient client;

    @BeforeEach
    void setUp() {
        client = new DeviceProtocolClient();
    }

    // -- connect / isConnected -----------------------------------------------

    @Test
    void notConnectedBeforeConnect() {
        assertFalse(client.isConnected());
    }

    @Test
    void connectMarksClientConnected() {
        client.connect("device://line-1");
        assertTrue(client.isConnected());
    }

    @Test
    void disconnectClearsConnectionState() {
        client.connect("device://line-1");
        client.disconnect();
        assertFalse(client.isConnected());
    }

    @Test
    void disconnectWithoutConnectIsSafe() {
        assertDoesNotThrow(() -> client.disconnect());
        assertFalse(client.isConnected());
    }

    // -- sendCommand -----------------------------------------------------------

    @Test
    void sendCommandBeforeConnectThrowsDeviceIoException() {
        assertThrows(DeviceIoException.class,
                () -> client.sendCommand(new DeviceCommand("START", Map.of())));
    }

    @Test
    void sendCommandAfterConnectSucceeds() {
        client.connect("device://line-1");

        assertDoesNotThrow(() ->
                client.sendCommand(new DeviceCommand("START", Map.of("speed", 5))));
    }

    @Test
    void sendCommandAfterDisconnectThrowsDeviceIoException() {
        client.connect("device://line-1");
        client.disconnect();

        assertThrows(DeviceIoException.class,
                () -> client.sendCommand(new DeviceCommand("STOP", Map.of())));
    }

    // -- onEvent / simulateEvent -------------------------------------------------

    @Test
    void simulateEventInvokesRegisteredHandler() {
        List<DeviceEvent> received = new ArrayList<>();
        client.onEvent(received::add);

        DeviceEvent event = new DeviceEvent("alarm", Map.of("code", 42));
        client.simulateEvent(event);

        assertEquals(List.of(event), received);
    }

    @Test
    void simulateEventInvokesAllRegisteredHandlersInOrder() {
        List<String> calls = new ArrayList<>();
        client.onEvent(evt -> calls.add("first:" + evt.name()));
        client.onEvent(evt -> calls.add("second:" + evt.name()));

        client.simulateEvent(new DeviceEvent("ping", Map.of()));

        assertEquals(List.of("first:ping", "second:ping"), calls);
    }

    @Test
    void simulateEventWithNoHandlersDoesNotThrow() {
        assertDoesNotThrow(() -> client.simulateEvent(new DeviceEvent("ping", Map.of())));
    }

    @Test
    void simulateEventWorksRegardlessOfConnectionState() {
        // Event delivery is independent of connect()/disconnect() bookkeeping —
        // only sendCommand is gated on connection state.
        List<DeviceEvent> received = new ArrayList<>();
        client.onEvent(received::add);

        DeviceEvent event = new DeviceEvent("alarm", Map.of());
        client.simulateEvent(event);

        assertEquals(List.of(event), received);
    }
}
