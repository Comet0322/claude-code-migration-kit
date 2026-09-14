package com.boogie.sdk.infra;

import com.boogie.sdk.core.InfraException;
import org.junit.jupiter.api.Test;

import java.io.IOException;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.concurrent.TimeoutException;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.concurrent.atomic.AtomicReference;

import static org.junit.jupiter.api.Assertions.assertArrayEquals;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNotEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

/**
 * Tests for HttpClient. See boogie-sdk-api.md section 5.2 (infra).
 *
 * HttpClient is an in-memory fake: it never opens a real socket.
 * Conventions this test file pins down (no existing convention in the
 * design doc or stubs beyond the public get/post method shapes):
 *
 * - Transport injection: {@code HttpClient(Transport transport)} accepts
 *   an injectable {@link Transport} (a small functional interface added
 *   for this purpose, see Transport.java) — the seam these tests use to
 *   control responses deterministically instead of hitting a real
 *   network. A Transport implementation may also throw to simulate a
 *   network failure; HttpClient is expected to catch that and drive its
 *   retry/backoff logic. The no-arg constructor is still usable
 *   standalone, falling back to a canned 200 response for get/post.
 * - Trace-id header: the client auto-injects an {@code "X-Trace-Id"}
 *   header into every outgoing request (merged with any caller-supplied
 *   headers — caller headers must not be dropped). Each call gets its own
 *   unique trace id.
 * - Retry/backoff: when the transport throws, get/post retry a small,
 *   bounded number of times and return the eventual successful response
 *   if one of the retries succeeds. If every attempt fails, the client
 *   wraps the underlying failure in {@link InfraException} (the raw
 *   transport exception never escapes). Tests keep retry counts small and
 *   never sleep for a meaningful amount of time, so the whole file stays
 *   fast.
 */
class HttpClientTest {

    // -- default transport / basic usability -----------------------------

    @Test
    void noArgConstructorGetReturnsACanned200WithoutConfiguration() {
        HttpClient client = new HttpClient();

        HttpResponse response = client.get("http://example.invalid/resource", Map.of());

        assertEquals(200, response.statusCode());
    }

    // -- transport invocation ---------------------------------------------

    @Test
    void getCallsTransportWithMethodUrlAndHeaders() {
        List<Object[]> calls = new ArrayList<>();
        Transport transport = (method, url, body, headers) -> {
            calls.add(new Object[]{method, url, body, headers});
            return new HttpResponse(200, Map.of(), "ok".getBytes());
        };
        HttpClient client = new HttpClient(transport);

        HttpResponse response = client.get("http://svc/x", Map.of("Accept", "application/json"));

        assertEquals(200, response.statusCode());
        assertArrayEquals("ok".getBytes(), response.body());
        assertEquals(1, calls.size());
        Object[] call = calls.get(0);
        assertEquals("GET", ((String) call[0]).toUpperCase());
        assertEquals("http://svc/x", call[1]);
        @SuppressWarnings("unchecked")
        Map<String, String> capturedHeaders = (Map<String, String>) call[3];
        assertEquals("application/json", capturedHeaders.get("Accept"));
    }

    @Test
    void postCallsTransportWithTheGivenBody() {
        List<Object[]> calls = new ArrayList<>();
        Transport transport = (method, url, body, headers) -> {
            calls.add(new Object[]{method, url, body, headers});
            return new HttpResponse(201, Map.of(), "created".getBytes());
        };
        HttpClient client = new HttpClient(transport);

        HttpResponse response = client.post("http://svc/x", "payload".getBytes(), Map.of("X-Foo", "bar"));

        assertEquals(201, response.statusCode());
        Object[] call = calls.get(0);
        assertEquals("POST", ((String) call[0]).toUpperCase());
        assertArrayEquals("payload".getBytes(), (byte[]) call[2]);
        @SuppressWarnings("unchecked")
        Map<String, String> capturedHeaders = (Map<String, String>) call[3];
        assertEquals("bar", capturedHeaders.get("X-Foo"));
    }

    // -- trace-id header injection ------------------------------------------

    @Test
    void getInjectsATraceIdHeader() {
        AtomicReference<Map<String, String>> captured = new AtomicReference<>();
        Transport transport = (method, url, body, headers) -> {
            captured.set(headers);
            return new HttpResponse(200, Map.of(), new byte[0]);
        };
        HttpClient client = new HttpClient(transport);

        client.get("http://svc/x", Map.of());

        assertNotNull(captured.get().get("X-Trace-Id"));
        assertFalse(captured.get().get("X-Trace-Id").isEmpty());
    }

    @Test
    void traceIdIsUniquePerCall() {
        List<String> traceIds = new ArrayList<>();
        Transport transport = (method, url, body, headers) -> {
            traceIds.add(headers.get("X-Trace-Id"));
            return new HttpResponse(200, Map.of(), new byte[0]);
        };
        HttpClient client = new HttpClient(transport);

        client.get("http://svc/x", Map.of());
        client.get("http://svc/x", Map.of());

        assertEquals(2, traceIds.size());
        assertNotEquals(traceIds.get(0), traceIds.get(1));
    }

    @Test
    void callerSuppliedHeadersArePreservedAlongsideTheTraceId() {
        AtomicReference<Map<String, String>> captured = new AtomicReference<>();
        Transport transport = (method, url, body, headers) -> {
            captured.set(headers);
            return new HttpResponse(200, Map.of(), new byte[0]);
        };
        HttpClient client = new HttpClient(transport);

        client.get("http://svc/x", Map.of("Authorization", "Bearer t"));

        assertEquals("Bearer t", captured.get().get("Authorization"));
        assertNotNull(captured.get().get("X-Trace-Id"));
    }

    // -- retry / backoff ------------------------------------------------------

    @Test
    void getRetriesAfterTransientTransportFailuresThenSucceeds() {
        AtomicInteger attempts = new AtomicInteger();
        Transport transport = (method, url, body, headers) -> {
            if (attempts.incrementAndGet() <= 2) {
                throw new IOException("simulated network failure");
            }
            return new HttpResponse(200, Map.of(), "finally ok".getBytes());
        };
        HttpClient client = new HttpClient(transport);

        HttpResponse response = client.get("http://svc/x", Map.of());

        assertEquals(200, response.statusCode());
        assertArrayEquals("finally ok".getBytes(), response.body());
        assertEquals(3, attempts.get());
    }

    @Test
    void getRaisesInfraExceptionAfterExhaustingRetries() {
        AtomicInteger attempts = new AtomicInteger();
        Transport transport = (method, url, body, headers) -> {
            attempts.incrementAndGet();
            throw new IOException("simulated permanent failure");
        };
        HttpClient client = new HttpClient(transport);

        assertThrows(InfraException.class, () -> client.get("http://svc/x", Map.of()));

        // Retried more than once but bounded (not an infinite loop).
        assertTrue(attempts.get() > 1);
        assertTrue(attempts.get() <= 10);
    }

    @Test
    void postRaisesInfraExceptionAfterExhaustingRetries() {
        Transport transport = (method, url, body, headers) -> {
            throw new TimeoutException("simulated timeout");
        };
        HttpClient client = new HttpClient(transport);

        assertThrows(InfraException.class, () -> client.post("http://svc/x", "payload".getBytes(), Map.of()));
    }
}
