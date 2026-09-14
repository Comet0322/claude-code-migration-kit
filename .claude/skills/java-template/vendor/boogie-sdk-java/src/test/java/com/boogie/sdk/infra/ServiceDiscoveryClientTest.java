package com.boogie.sdk.infra;

import com.boogie.sdk.core.NotFoundException;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;

/**
 * Tests for ServiceDiscoveryClient. See boogie-sdk-api.md section 5.2
 * (infra).
 *
 * Conventions this test file pins down (none exist yet beyond the public
 * `resolve` method shape):
 *
 * - There is no real service registry behind this fake, so
 *   {@link ServiceDiscoveryClient#register(String, Endpoint)} is added
 *   (additive beyond the design doc) purely so tests — and any other
 *   caller — can seed the fake registry before resolving from it. Same
 *   pattern used by the Python port's ServiceDiscoveryClient.
 * - {@code resolve} on a service name that was never registered throws
 *   {@link NotFoundException}.
 * - {@code register} overwrites any previous registration for the same
 *   service name.
 */
class ServiceDiscoveryClientTest {

    private ServiceDiscoveryClient client;

    @BeforeEach
    void setUp() {
        client = new ServiceDiscoveryClient();
    }

    @Test
    void resolveOnAnUnregisteredServiceThrowsNotFound() {
        assertThrows(NotFoundException.class, () -> client.resolve("unknown-service"));
    }

    @Test
    void resolveReturnsTheRegisteredEndpoint() {
        client.register("orders", new Endpoint("orders.internal", 8080));

        Endpoint resolved = client.resolve("orders");

        assertEquals("orders.internal", resolved.host());
        assertEquals(8080, resolved.port());
    }

    @Test
    void registerOverwritesAPreviousRegistrationForTheSameName() {
        client.register("orders", new Endpoint("old-host", 1111));
        client.register("orders", new Endpoint("new-host", 2222));

        Endpoint resolved = client.resolve("orders");

        assertEquals("new-host", resolved.host());
        assertEquals(2222, resolved.port());
    }

    @Test
    void differentServiceNamesResolveIndependently() {
        client.register("orders", new Endpoint("orders-host", 1));
        client.register("payments", new Endpoint("payments-host", 2));

        assertEquals("orders-host", client.resolve("orders").host());
        assertEquals("payments-host", client.resolve("payments").host());
    }
}
