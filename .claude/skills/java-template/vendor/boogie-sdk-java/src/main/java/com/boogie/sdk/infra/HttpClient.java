package com.boogie.sdk.infra;

import com.boogie.sdk.core.InfraException;

import java.util.HashMap;
import java.util.Map;
import java.util.UUID;

/**
 * HttpClient stub. See boogie-sdk-api.md section 5.2 (infra).
 * Skeleton only — implemented during the Phase 1 TDD loop for the `infra` module.
 *
 * The {@link Transport} field/constructors below are a test seam added by
 * the test-writer stage (see HttpClientTest for the pinned-down
 * conventions: trace-id header injection, retry/backoff, InfraException on
 * exhausted retries). get/post themselves remain unimplemented stubs for
 * the implementer stage.
 */
public class HttpClient {
    private static final int MAX_ATTEMPTS = 3;

    private final Transport transport;

    public HttpClient() {
        this(HttpClient::defaultTransport);
    }

    public HttpClient(Transport transport) {
        this.transport = transport;
    }

    private static HttpResponse defaultTransport(String method, String url, byte[] body, Map<String, String> headers) {
        return new HttpResponse(200, Map.of(), new byte[0]);
    }

    public HttpResponse get(String url, Map<String, String> headers) {
        return send("GET", url, null, headers);
    }

    public HttpResponse post(String url, byte[] body, Map<String, String> headers) {
        return send("POST", url, body, headers);
    }

    private HttpResponse send(String method, String url, byte[] body, Map<String, String> headers) {
        Map<String, String> merged = new HashMap<>(headers);
        merged.put("X-Trace-Id", UUID.randomUUID().toString());

        Exception lastFailure = null;
        for (int attempt = 0; attempt < MAX_ATTEMPTS; attempt++) {
            try {
                return transport.call(method, url, body, merged);
            } catch (Exception e) {
                lastFailure = e;
            }
        }
        throw new InfraException("HTTP " + method + " " + url + " failed after " + MAX_ATTEMPTS + " attempts", lastFailure);
    }
}
