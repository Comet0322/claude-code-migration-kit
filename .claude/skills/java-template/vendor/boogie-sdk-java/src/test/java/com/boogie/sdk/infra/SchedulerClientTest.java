package com.boogie.sdk.infra;

import com.boogie.sdk.core.InfraException;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.time.Duration;
import java.util.concurrent.atomic.AtomicBoolean;

import static org.junit.jupiter.api.Assertions.assertDoesNotThrow;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertThrows;

/**
 * Tests for SchedulerClient. See boogie-sdk-api.md section 5.2 (infra).
 *
 * Conventions this test file pins down (none exist yet beyond the public
 * method shapes):
 *
 * - {@code lock(name, ttl)}: non-blocking "try-lock" semantics, not
 *   blocking-wait. If {@code name} is already held by an outstanding,
 *   unreleased {@link Lock}, a second {@code lock()} call for the *same
 *   name* raises {@link InfraException} immediately (chosen over blocking
 *   so tests stay fast and deterministic). The returned {@code Lock} is
 *   usable via try-with-resources (it extends {@code AutoCloseable}) and
 *   also exposes an explicit {@code release()}; after release (either
 *   way) the name becomes lockable again. Locks for different names never
 *   contend with each other.
 * - {@code scheduleCron(cronExpr, task)}: real background scheduling
 *   isn't deterministically testable, so this fake treats it as
 *   "register only" — it must not raise and must not execute {@code task}
 *   synchronously. This file deliberately does not require any internal
 *   introspection list on {@code SchedulerClient} beyond the public API
 *   (unlike the Python port's {@code _registered_jobs}); "task never ran
 *   synchronously" is observed instead via a flag the task closure itself
 *   sets, which is sufficient coverage for a register-only fake without
 *   growing the class's public surface further.
 */
class SchedulerClientTest {

    private SchedulerClient client;

    @BeforeEach
    void setUp() {
        client = new SchedulerClient();
    }

    // -- lock: acquire / contention --------------------------------------

    @Test
    void lockReturnsALockObject() {
        Lock lock = client.lock("job-a", Duration.ofSeconds(30));
        assertNotNull(lock);
        lock.release();
    }

    @Test
    void secondLockForTheSameNameWhileHeldThrowsInfraException() {
        Lock held = client.lock("job-a", Duration.ofSeconds(30));

        assertThrows(InfraException.class, () -> client.lock("job-a", Duration.ofSeconds(30)));

        held.release();
    }

    @Test
    void locksForDifferentNamesDoNotContend() {
        Lock lockA = client.lock("job-a", Duration.ofSeconds(30));
        Lock lockB = assertDoesNotThrow(() -> client.lock("job-b", Duration.ofSeconds(30)));

        lockA.release();
        lockB.release();
    }

    // -- lock: release makes the name lockable again ---------------------

    @Test
    void lockBecomesAvailableAgainAfterExplicitRelease() {
        Lock first = client.lock("job-a", Duration.ofSeconds(30));
        first.release();

        Lock second = assertDoesNotThrow(() -> client.lock("job-a", Duration.ofSeconds(30)));
        second.release();
    }

    @Test
    void releaseIsIdempotent() {
        Lock lock = client.lock("job-a", Duration.ofSeconds(30));
        lock.release();

        assertDoesNotThrow(lock::release);
    }

    @Test
    void lockIsUsableAsATryWithResources() {
        try (Lock lock = client.lock("job-a", Duration.ofSeconds(30))) {
            assertThrows(InfraException.class, () -> client.lock("job-a", Duration.ofSeconds(30)));
        }

        Lock afterwards = assertDoesNotThrow(() -> client.lock("job-a", Duration.ofSeconds(30)));
        afterwards.release();
    }

    @Test
    void tryWithResourcesReleasesTheLockEvenIfTheBodyThrows() {
        class BoomException extends RuntimeException {
        }

        assertThrows(BoomException.class, () -> {
            try (Lock lock = client.lock("job-a", Duration.ofSeconds(30))) {
                throw new BoomException();
            }
        });

        Lock afterwards = assertDoesNotThrow(() -> client.lock("job-a", Duration.ofSeconds(30)));
        afterwards.release();
    }

    // -- scheduleCron: register-only --------------------------------------

    @Test
    void scheduleCronDoesNotThrow() {
        assertDoesNotThrow(() -> client.scheduleCron("0 * * * *", () -> {
        }));
    }

    @Test
    void scheduleCronDoesNotExecuteTheTaskSynchronously() {
        AtomicBoolean executed = new AtomicBoolean(false);

        client.scheduleCron("0 * * * *", () -> executed.set(true));

        assertFalse(executed.get());
    }

    @Test
    void scheduleCronAcceptsMultipleRegistrationsWithoutThrowing() {
        assertDoesNotThrow(() -> {
            client.scheduleCron("0 * * * *", () -> {
            });
            client.scheduleCron("*/5 * * * *", () -> {
            });
        });
    }
}
