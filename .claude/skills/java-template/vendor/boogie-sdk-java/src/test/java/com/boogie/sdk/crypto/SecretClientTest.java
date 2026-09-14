package com.boogie.sdk.crypto;

import com.boogie.sdk.core.NotFoundException;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.util.Map;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;

/**
 * Tests for SecretClient. See boogie-sdk-api.md section 5.1 (crypto).
 *
 * getSecret has a built-in TTL cache per the design doc, but the cache's
 * internal shape (eviction, backing store fields, clock source) is an
 * implementation detail the stub does not expose. Per the task brief, we
 * keep these tests to observable, black-box behavior: put/get round-trip,
 * path correctness, overwrite visibility, and not-found handling. TTL
 * internals (e.g. "a second get within TTL skips the backing store") are
 * intentionally left untested here rather than reaching into private state
 * and locking the implementer into one specific cache internal.
 */
class SecretClientTest {

    private SecretClient client;

    @BeforeEach
    void setUp() {
        client = new SecretClient();
    }

    @Test
    void putThenGetRoundTrip() {
        client.putSecret("db/prod", Map.of("user", "admin", "password", "hunter2"));

        Secret secret = client.getSecret("db/prod");

        assertEquals("db/prod", secret.path());
        assertEquals(Map.of("user", "admin", "password", "hunter2"), secret.data());
    }

    @Test
    void getSecretReturnsEqualValueEachTime() {
        client.putSecret("db/prod", Map.of("user", "admin"));

        Secret first = client.getSecret("db/prod");
        Secret second = client.getSecret("db/prod");

        assertEquals(first, second);
    }

    @Test
    void putSecretOverwriteIsVisibleOnNextGet() {
        client.putSecret("api/key", Map.of("value", "old"));
        client.putSecret("api/key", Map.of("value", "new"));

        Secret secret = client.getSecret("api/key");

        assertEquals(Map.of("value", "new"), secret.data());
    }

    @Test
    void getSecretForUnknownPathRaisesNotFoundException() {
        assertThrows(NotFoundException.class, () -> client.getSecret("never/put/this/path"));
    }

    @Test
    void multiplePathsAreIndependent() {
        client.putSecret("a", Map.of("v", "1"));
        client.putSecret("b", Map.of("v", "2"));

        assertEquals(Map.of("v", "1"), client.getSecret("a").data());
        assertEquals(Map.of("v", "2"), client.getSecret("b").data());
    }
}
