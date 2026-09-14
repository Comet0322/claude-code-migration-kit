package com.boogie.sdk.infra;

/**
 * Lock stub. See boogie-sdk-api.md section 5.2 (infra).
 * Skeleton only — implemented during the Phase 1 TDD loop for the `infra` module.
 */
public interface Lock extends AutoCloseable {
    void release();

    @Override
    default void close() {
        release();
    }
}
