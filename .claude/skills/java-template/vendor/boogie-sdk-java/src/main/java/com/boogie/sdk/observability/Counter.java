package com.boogie.sdk.observability;

/**
 * Counter stub. See boogie-sdk-api.md section 5.4 (observability).
 * Skeleton only — implemented during the Phase 1 TDD loop for the `observability` module.
 */
public interface Counter {
    void increment();

    void increment(long amount);
}
