package com.boogie.sdk.infra;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.time.Duration;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.function.Supplier;

import static org.junit.jupiter.api.Assertions.assertArrayEquals;
import static org.junit.jupiter.api.Assertions.assertDoesNotThrow;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

/**
 * Tests for CacheClient. See boogie-sdk-api.md section 5.2 (infra).
 *
 * Conventions this test file pins down (none exist yet beyond the public
 * method shapes):
 *
 * - Backing store: a plain in-memory map keyed by string, with per-key
 *   expiry tracked via a monotonic clock ({@code System.nanoTime()}), not
 *   wall-clock time — so TTL expiry can be tested fast and deterministically
 *   with a very short TTL plus a short sleep, unaffected by system clock
 *   adjustments.
 * - {@code get} never throws for a missing or expired key: it returns
 *   {@code Optional.empty()} in both cases.
 * - {@code getOrCompute} calls {@code loader} only on miss/expiry, caches
 *   the freshly computed value under the given ttl, and must not call
 *   {@code loader} again while the cached value is still fresh.
 */
class CacheClientTest {

    private CacheClient client;

    @BeforeEach
    void setUp() {
        client = new CacheClient();
    }

    // -- get / set / delete --------------------------------------------

    @Test
    void getOnMissingKeyReturnsEmpty() {
        assertTrue(client.get("nope").isEmpty());
    }

    @Test
    void setThenGetReturnsTheStoredValue() {
        client.set("k", "v".getBytes(), Duration.ofSeconds(30));
        assertArrayEquals("v".getBytes(), client.get("k").orElseThrow());
    }

    @Test
    void setOverwritesAnExistingValueForTheSameKey() {
        client.set("k", "v1".getBytes(), Duration.ofSeconds(30));
        client.set("k", "v2".getBytes(), Duration.ofSeconds(30));
        assertArrayEquals("v2".getBytes(), client.get("k").orElseThrow());
    }

    @Test
    void differentKeysDoNotInterfereWithEachOther() {
        client.set("a", "1".getBytes(), Duration.ofSeconds(30));
        client.set("b", "2".getBytes(), Duration.ofSeconds(30));

        assertArrayEquals("1".getBytes(), client.get("a").orElseThrow());
        assertArrayEquals("2".getBytes(), client.get("b").orElseThrow());
    }

    @Test
    void deleteRemovesAKey() {
        client.set("k", "v".getBytes(), Duration.ofSeconds(30));
        client.delete("k");
        assertTrue(client.get("k").isEmpty());
    }

    @Test
    void deleteOnAMissingKeyDoesNotThrow() {
        assertDoesNotThrow(() -> client.delete("never-set"));
    }

    // -- TTL expiry ------------------------------------------------------

    @Test
    void getBeforeTtlExpiryReturnsTheValue() {
        client.set("k", "v".getBytes(), Duration.ofSeconds(30));
        assertTrue(client.get("k").isPresent());
    }

    @Test
    void getAfterTtlExpiryReturnsEmpty() throws InterruptedException {
        client.set("k", "v".getBytes(), Duration.ofMillis(20));
        Thread.sleep(60);
        assertTrue(client.get("k").isEmpty());
    }

    // -- getOrCompute ------------------------------------------------------

    @Test
    void getOrComputeCallsLoaderOnMissAndReturnsItsValue() {
        byte[] result = client.getOrCompute("k", Duration.ofSeconds(30), () -> "computed".getBytes());
        assertArrayEquals("computed".getBytes(), result);
    }

    @Test
    void getOrComputeCachesTheComputedValueForSubsequentGets() {
        client.getOrCompute("k", Duration.ofSeconds(30), () -> "computed".getBytes());
        assertArrayEquals("computed".getBytes(), client.get("k").orElseThrow());
    }

    @Test
    void getOrComputeDoesNotCallLoaderAgainWhileValueIsFresh() {
        AtomicInteger calls = new AtomicInteger();
        Supplier<byte[]> loader = () -> {
            calls.incrementAndGet();
            return "v".getBytes();
        };

        byte[] first = client.getOrCompute("k", Duration.ofSeconds(30), loader);
        byte[] second = client.getOrCompute("k", Duration.ofSeconds(30), loader);

        assertArrayEquals(first, second);
        assertEquals(1, calls.get());
    }

    @Test
    void getOrComputeRecomputesAfterTheCachedValueExpires() throws InterruptedException {
        AtomicInteger calls = new AtomicInteger();
        Supplier<byte[]> loader = () -> {
            int n = calls.incrementAndGet();
            return ("v" + n).getBytes();
        };

        client.getOrCompute("k", Duration.ofMillis(20), loader);
        Thread.sleep(60);
        client.getOrCompute("k", Duration.ofMillis(20), loader);

        assertEquals(2, calls.get());
    }
}
