package com.boogie.sdk.governance;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertTrue;

/**
 * Tests for IdGenerator. See boogie-sdk-api.md section 5.5 (governance).
 *
 * <p>The design doc only documents {@code long nextId()} with a
 * "Snowflake-style" comment and no bit-layout or formatting spec. Since
 * there is no real distributed-id service behind this fake and no format
 * is mandated, this test file deliberately does NOT assert on bit-width,
 * timestamp encoding, or any particular numeric range — mirroring the
 * already-built Python port's {@code test_id_generator.py}. It only pins
 * down the properties a Snowflake-style generator must have to be useful
 * as an id source:
 *
 * <ul>
 *   <li>every returned id is a non-negative {@code long}.
 *   <li>many calls in a row never collide (uniqueness), checked across a
 *       moderately large batch (1000+ calls) to catch a naive random or a
 *       poorly-seeded counter without making the test slow.
 *   <li>ids are non-decreasing across successive calls ({@code nextId()
 *       >= previous nextId()}), which is the one ordering guarantee
 *       "Snowflake-style" implies, without assuming strict monotonic
 *       increase (a real Snowflake id can repeat within the same clock
 *       tick and only strictly increases across ticks).
 * </ul>
 *
 * <p>{@code nextId()} currently throws {@link UnsupportedOperationException}
 * (skeleton stage) — every test below is expected to fail with that
 * exception until the `implementer` stage fills in a real body; that
 * failure mode is expected/fine per the TDD pipeline.
 */
class IdGeneratorTest {

    private IdGenerator generator;

    @BeforeEach
    void setUp() {
        generator = new IdGenerator();
    }

    @Test
    void nextIdReturnsANonNegativeValue() {
        assertTrue(generator.nextId() >= 0);
    }

    @Test
    void manyCallsReturnDistinctIds() {
        java.util.Set<Long> seen = new java.util.HashSet<>();
        for (int i = 0; i < 1000; i++) {
            assertTrue(seen.add(generator.nextId()), "duplicate id encountered at call " + i);
        }
        assertTrue(seen.size() == 1000);
    }

    @Test
    void manyCallsAreAllNonNegative() {
        for (int i = 0; i < 1000; i++) {
            assertTrue(generator.nextId() >= 0);
        }
    }

    @Test
    void idsAreNonDecreasingAcrossSuccessiveCalls() {
        long previous = generator.nextId();
        for (int i = 0; i < 1000; i++) {
            long current = generator.nextId();
            assertTrue(current >= previous, "id decreased: " + current + " < " + previous);
            previous = current;
        }
    }

    @Test
    void twoSeparateGeneratorsDoNotNeedToCoordinate() {
        // Two independent generator instances are still each internally
        // consistent (own ids stay unique) even though nothing requires
        // them to interleave in any particular order relative to each
        // other.
        IdGenerator other = new IdGenerator();

        java.util.Set<Long> idsA = new java.util.HashSet<>();
        java.util.Set<Long> idsB = new java.util.HashSet<>();
        for (int i = 0; i < 50; i++) {
            assertTrue(idsA.add(generator.nextId()));
            assertTrue(idsB.add(other.nextId()));
        }
    }
}
