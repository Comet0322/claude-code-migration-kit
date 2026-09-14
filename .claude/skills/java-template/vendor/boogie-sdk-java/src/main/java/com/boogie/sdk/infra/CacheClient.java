package com.boogie.sdk.infra;

import java.time.Duration;
import java.util.Optional;
import java.util.concurrent.ConcurrentHashMap;
import java.util.function.Supplier;

/**
 * CacheClient stub. See boogie-sdk-api.md section 5.2 (infra).
 * Skeleton only — implemented during the Phase 1 TDD loop for the `infra` module.
 */
public class CacheClient {

    private record Entry(byte[] value, long expiresAtNanos) {
        boolean isExpired(long nowNanos) {
            return nowNanos - expiresAtNanos >= 0;
        }
    }

    private final ConcurrentHashMap<String, Entry> store = new ConcurrentHashMap<>();

    public Optional<byte[]> get(String key) {
        Entry entry = store.get(key);
        if (entry == null) {
            return Optional.empty();
        }
        if (entry.isExpired(System.nanoTime())) {
            store.remove(key, entry);
            return Optional.empty();
        }
        return Optional.of(entry.value());
    }

    public void set(String key, byte[] value, Duration ttl) {
        long expiresAt = System.nanoTime() + ttl.toNanos();
        store.put(key, new Entry(value, expiresAt));
    }

    public void delete(String key) {
        store.remove(key);
    }

    public byte[] getOrCompute(String key, Duration ttl, Supplier<byte[]> loader) {
        Optional<byte[]> existing = get(key);
        if (existing.isPresent()) {
            return existing.get();
        }
        byte[] computed = loader.get();
        set(key, computed, ttl);
        return computed;
    }
}
