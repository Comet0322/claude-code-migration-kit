package com.boogie.sdk.governance;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.util.Map;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

/**
 * Tests for HealthCheck and HealthReport. See boogie-sdk-api.md section
 * 5.5 (governance).
 *
 * <p>The design doc documents {@code register(name, Supplier<Boolean>
 * check)} and {@code HealthReport status()}, and {@code HealthReport} is
 * already a concrete record ({@code record HealthReport(boolean healthy,
 * Map<String, Boolean> checks)}) — no additive members are needed here.
 * This test file pins down the conventions the design doc leaves open,
 * mirroring the already-built Python port's {@code HealthCheck}:
 *
 * <ul>
 *   <li>No checks registered: {@code status()} reports {@code
 *       healthy=true} with an empty {@code checks} map (vacuous AND).
 *   <li>Each registered check contributes one entry to {@code checks},
 *       keyed by its registered name, with the boolean the check
 *       returned.
 *   <li>Overall {@code healthy} is the logical AND of every individual
 *       check result: any single {@code false} makes the whole report
 *       unhealthy.
 *   <li>A check whose {@code Supplier<Boolean>} throws is caught
 *       internally and treated as {@code false} for that entry — the
 *       exception must not propagate out of {@code status()}, and must
 *       not prevent other checks from running.
 *   <li>Registering a second check under a name already in use overwrites
 *       the first (last registration for a name wins), matching {@code
 *       register}'s lack of a "duplicate name" error in the design doc.
 * </ul>
 *
 * <p>{@code register}/{@code status} currently throw {@link
 * UnsupportedOperationException} (skeleton stage) — every test below is
 * expected to fail with that exception until the `implementer` stage
 * fills in real bodies; that failure mode is expected/fine per the TDD
 * pipeline.
 */
class HealthCheckTest {

    private HealthCheck healthCheck;

    @BeforeEach
    void setUp() {
        healthCheck = new HealthCheck();
    }

    @Test
    void noChecksRegisteredIsHealthyWithEmptyChecksMap() {
        HealthReport report = healthCheck.status();

        assertTrue(report.healthy());
        assertTrue(report.checks().isEmpty());
    }

    @Test
    void singlePassingCheckIsHealthy() {
        healthCheck.register("db", () -> true);

        HealthReport report = healthCheck.status();

        assertTrue(report.healthy());
        assertEquals(Map.of("db", true), report.checks());
    }

    @Test
    void singleFailingCheckIsUnhealthy() {
        healthCheck.register("db", () -> false);

        HealthReport report = healthCheck.status();

        assertFalse(report.healthy());
        assertEquals(Map.of("db", false), report.checks());
    }

    @Test
    void overallHealthyRequiresEveryCheckToPass() {
        healthCheck.register("db", () -> true);
        healthCheck.register("cache", () -> true);
        healthCheck.register("queue", () -> true);

        assertTrue(healthCheck.status().healthy());
    }

    @Test
    void oneFailingCheckAmongManyMakesTheWholeReportUnhealthy() {
        healthCheck.register("db", () -> true);
        healthCheck.register("cache", () -> false);
        healthCheck.register("queue", () -> true);

        HealthReport report = healthCheck.status();

        assertFalse(report.healthy());
        assertEquals(3, report.checks().size());
        assertFalse(report.checks().get("cache"));
    }

    @Test
    void checkThatThrowsIsTreatedAsFalseAndDoesNotPropagate() {
        healthCheck.register("flaky", () -> {
            throw new RuntimeException("boom");
        });

        HealthReport report = healthCheck.status();

        assertFalse(report.healthy());
        assertFalse(report.checks().get("flaky"));
    }

    @Test
    void aThrowingCheckDoesNotPreventOtherChecksFromRunning() {
        healthCheck.register("flaky", () -> {
            throw new RuntimeException("boom");
        });
        healthCheck.register("db", () -> true);

        HealthReport report = healthCheck.status();

        assertEquals(2, report.checks().size());
        assertTrue(report.checks().get("db"));
        assertFalse(report.checks().get("flaky"));
    }

    @Test
    void registeringTheSameNameTwiceOverwritesTheFirstRegistration() {
        healthCheck.register("db", () -> false);
        healthCheck.register("db", () -> true);

        HealthReport report = healthCheck.status();

        assertEquals(1, report.checks().size());
        assertTrue(report.checks().get("db"));
    }
}
