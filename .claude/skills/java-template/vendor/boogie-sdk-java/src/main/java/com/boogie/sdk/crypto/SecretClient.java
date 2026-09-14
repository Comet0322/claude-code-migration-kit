package com.boogie.sdk.crypto;

import com.boogie.sdk.core.NotFoundException;

import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

/**
 * SecretClient. See boogie-sdk-api.md section 5.1 (crypto).
 *
 * Backed by an in-memory store keyed by path (simulates the "built-in TTL
 * cache" fronting a real secret backend -- there is no real backend here, so
 * putSecret populates the store directly and getSecret reads it back).
 */
public class SecretClient {

    private final Map<String, Secret> store = new ConcurrentHashMap<>();

    public Secret getSecret(String path) {
        Secret secret = store.get(path);
        if (secret == null) {
            throw new NotFoundException("secret not found: " + path);
        }
        return secret;
    }

    public void putSecret(String path, Map<String, String> data) {
        store.put(path, new Secret(path, Map.copyOf(data)));
    }
}
