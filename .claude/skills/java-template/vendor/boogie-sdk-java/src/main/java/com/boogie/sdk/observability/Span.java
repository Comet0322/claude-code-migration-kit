package com.boogie.sdk.observability;

/**
 * Span stub. See boogie-sdk-api.md section 5.4 (observability).
 * Skeleton only — implemented during the Phase 1 TDD loop for the `observability` module.
 */
public interface Span extends AutoCloseable {
    void end();

    @Override
    default void close() {
        end();
    }
}
