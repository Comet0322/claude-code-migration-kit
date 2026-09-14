package com.boogie.sdk.infra;

import com.boogie.sdk.core.NotFoundException;

import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

/**
 * ServiceDiscoveryClient stub. See boogie-sdk-api.md section 5.2 (infra).
 * Skeleton only — implemented during the Phase 1 TDD loop for the `infra` module.
 *
 * {@link #register(String, Endpoint)} is additive beyond the design doc's
 * `resolve`-only shape: since there is no real service registry behind
 * this fake, the test-writer stage added `register` so tests (and any
 * other caller) can seed the fake registry before resolving from it. Same
 * pattern used by the Python port's ServiceDiscoveryClient. See
 * ServiceDiscoveryClientTest for the pinned-down conventions.
 */
public class ServiceDiscoveryClient {

    private final Map<String, Endpoint> registry = new ConcurrentHashMap<>();

    public void register(String serviceName, Endpoint endpoint) {
        registry.put(serviceName, endpoint);
    }

    public Endpoint resolve(String serviceName) {
        Endpoint endpoint = registry.get(serviceName);
        if (endpoint == null) {
            throw new NotFoundException("service not registered: " + serviceName);
        }
        return endpoint;
    }
}
