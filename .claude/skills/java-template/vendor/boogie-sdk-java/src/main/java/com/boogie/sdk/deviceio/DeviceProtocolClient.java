package com.boogie.sdk.deviceio;

import com.boogie.sdk.core.DeviceIoException;

import java.util.ArrayList;
import java.util.List;
import java.util.function.Consumer;

/**
 * DeviceProtocolClient stub. See boogie-sdk-api.md section 5.3 (deviceio).
 * Skeleton only — implemented during the Phase 1 TDD loop for the `deviceio` module.
 *
 * <p>Additive members beyond the design doc's method-only sketch
 * (test-writer stage, mirroring the already-built Python port's {@code
 * is_connected} property and {@code simulate_event} method), needed for
 * the deviceio test suite to compile — see DeviceProtocolClientTest for
 * the full conventions they establish:
 *
 * <ul>
 *   <li>{@link #isConnected()} exposes whether the client is currently
 *       connected, so tests can observe {@code connect()}/{@code
 *       disconnect()} effects without depending on internals.
 *   <li>{@link #simulateEvent(DeviceEvent)} invokes every handler
 *       registered via {@link #onEvent(Consumer)}, since there is no real
 *       device behind this fake to emit one — a test-only affordance for
 *       driving the event-handling path deterministically.
 * </ul>
 *
 * <p>Like every other method here, both still throw {@link
 * UnsupportedOperationException} at this skeleton stage; the implementer
 * stage fills in real bodies matching DeviceProtocolClientTest.
 */
public class DeviceProtocolClient {

    private boolean connected = false;
    private final List<Consumer<DeviceEvent>> handlers = new ArrayList<>();

    public void connect(String endpoint) {
        connected = true;
    }

    public boolean isConnected() {
        return connected;
    }

    public void sendCommand(DeviceCommand cmd) {
        if (!connected) {
            throw new DeviceIoException("not connected");
        }
    }

    public void onEvent(Consumer<DeviceEvent> handler) {
        handlers.add(handler);
    }

    public void simulateEvent(DeviceEvent event) {
        for (Consumer<DeviceEvent> handler : handlers) {
            handler.accept(event);
        }
    }

    public void disconnect() {
        connected = false;
    }
}
