package com.boogie.sdk.governance;

import java.util.LinkedHashMap;
import java.util.Map;
import java.util.function.Supplier;

/**
 * HealthCheck stub. See boogie-sdk-api.md section 5.5 (governance).
 * Skeleton only — implemented during the Phase 1 TDD loop for the `governance` module.
 */
public class HealthCheck {

    private final Map<String, Supplier<Boolean>> checks = new LinkedHashMap<>();

    public synchronized void register(String name, Supplier<Boolean> check) {
        checks.put(name, check);
    }

    public synchronized HealthReport status() {
        Map<String, Boolean> results = new LinkedHashMap<>();
        boolean healthy = true;
        for (Map.Entry<String, Supplier<Boolean>> entry : checks.entrySet()) {
            boolean result;
            try {
                result = Boolean.TRUE.equals(entry.getValue().get());
            } catch (Throwable e) {
                result = false;
            }
            results.put(entry.getKey(), result);
            healthy = healthy && result;
        }
        return new HealthReport(healthy, results);
    }
}
