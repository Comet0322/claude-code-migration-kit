package com.boogie.sdk;

import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import java.util.function.Supplier;

/** Shared lazy-singleton cache used by {@link BoogieSdk} and its sub-namespaces. */
final class LazyRegistry {
    private final Map<String, Object> instances = new ConcurrentHashMap<>();

    @SuppressWarnings("unchecked")
    <T> T get(String key, Supplier<T> factory) {
        return (T) instances.computeIfAbsent(key, k -> factory.get());
    }

    void clear() {
        instances.clear();
    }
}
