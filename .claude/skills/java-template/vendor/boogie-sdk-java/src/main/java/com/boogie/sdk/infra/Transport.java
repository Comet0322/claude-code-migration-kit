package com.boogie.sdk.infra;

import java.util.Map;

/**
 * Injectable transport seam for {@link HttpClient}.
 *
 * HttpClient never opens a real socket; instead it delegates the actual
 * "sending" of a request to a Transport, which tests can implement with a
 * deterministic fake instead of a real network call. A Transport
 * implementation may throw to simulate a network failure — HttpClient is
 * expected to catch any such exception and drive its retry/backoff logic
 * around it (see HttpClientTest for the pinned-down conventions).
 *
 * Added here (not in boogie-sdk-api.md, which only documents
 * HttpClient's public get/post shape) purely as a test seam, mirroring the
 * Python port's `Transport` callable type in infra/http_client.py.
 */
@FunctionalInterface
public interface Transport {
    HttpResponse call(String method, String url, byte[] body, Map<String, String> headers) throws Exception;
}
