package com.boogie.sdk.governance;

/**
 * IdGenerator stub. See boogie-sdk-api.md section 5.5 (governance).
 * Skeleton only — implemented during the Phase 1 TDD loop for the `governance` module.
 *
 * <p>Simple Snowflake-style generator: the high bits carry the current
 * timestamp (milliseconds since epoch) and the low bits carry a
 * monotonically increasing per-millisecond sequence, so ids are always
 * non-negative, unique per instance, and non-decreasing across successive
 * calls, without requiring coordination between separate instances.
 */
public class IdGenerator {

    private static final int SEQUENCE_BITS = 16;
    private static final long SEQUENCE_MASK = (1L << SEQUENCE_BITS) - 1;

    private long lastTimestamp = -1L;
    private long sequence = 0L;

    public synchronized long nextId() {
        long timestamp = System.currentTimeMillis();

        if (timestamp < lastTimestamp) {
            // Clock moved backwards; stay non-decreasing by reusing the last timestamp.
            timestamp = lastTimestamp;
        }

        if (timestamp == lastTimestamp) {
            sequence = (sequence + 1) & SEQUENCE_MASK;
            if (sequence == 0L) {
                // Sequence exhausted for this millisecond; advance to the next one.
                timestamp++;
            }
        } else {
            sequence = 0L;
        }

        lastTimestamp = timestamp;

        return (timestamp << SEQUENCE_BITS) | sequence;
    }
}
