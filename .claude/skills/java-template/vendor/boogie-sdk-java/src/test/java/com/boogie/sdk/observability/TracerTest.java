package com.boogie.sdk.observability;

import org.junit.jupiter.api.Test;

import java.util.List;

import static org.junit.jupiter.api.Assertions.assertDoesNotThrow;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

/**
 * Tests for Tracer and Span. See boogie-sdk-api.md section 5.4
 * (observability).
 *
 * <p>The design doc only documents {@code startSpan(name) -> Span}, and
 * that a span ends either via {@code span.end()} or via try-with-resources
 * exit ({@code Span extends AutoCloseable}; its default {@code close()}
 * already calls {@code end()}). There is no real OTel/Jaeger collector
 * behind this fake and no design-doc read-back method, so this test file
 * pins down the testable conventions, mirroring the Python port's
 * {@code Tracer.finished_spans} ({@code
 * boogie-sdk/python/src/boogie_sdk/observability/tracer.py}):
 *
 * <p><b>Additive convention beyond the design doc:</b> {@code Tracer}
 * gets a {@code List<FinishedSpan> finishedSpans()} getter, where {@code
 * FinishedSpan} is a {@code record FinishedSpan(String name, double
 * durationSeconds)}. Exactly one entry is appended the first time a span
 * finishes (direct {@code end()} call, or try-with-resources exit
 * including exit via an exception) — this is the only way to observe a
 * span's outcome given the design doc has no read-back API, flagged here
 * for the acceptance reviewer. Duration is measured with {@link
 * System#nanoTime()}.
 *
 * <p>Other conventions tested here:
 *
 * <ul>
 *   <li>{@code end()} must not append twice, and must not throw, if
 *       called more than once on the same span (idempotent), whether the
 *       second call is explicit or happens via try-with-resources exit
 *       after an earlier explicit {@code end()}.
 *   <li>Starting a second span before ending the first does not throw,
 *       and both spans are tracked independently — trace-context
 *       propagation/parenting is out of scope per the task brief.
 *   <li>{@code durationSeconds} for a finished span is a plausible
 *       non-negative number. To keep this fast and deterministic without
 *       a clock-injection seam (none exists on this stub, unlike the
 *       Python port's {@code time.monotonic} which can be monkeypatched),
 *       a small real sleep (10ms) is used for the "nonzero duration"
 *       check instead of mocking {@link System#nanoTime()}.
 * </ul>
 *
 * <p>{@code startSpan}/{@code end}/{@code finishedSpans} currently throw
 * {@link UnsupportedOperationException} (skeleton stage) — every test
 * below is expected to fail with that exception until the `implementer`
 * stage fills in real bodies; that failure mode is expected/fine per the
 * TDD pipeline.
 */
class TracerTest {

    @Test
    void startSpanReturnsASpanUsableAsContextManager() {
        Tracer tracer = new Tracer();

        try (Span span = tracer.startSpan("work")) {
            assertNotNull(span);
        }
    }

    @Test
    void tryWithResourcesClosingCallsEndAndRecordsFinishedSpan() {
        Tracer tracer = new Tracer();

        try (Span span = tracer.startSpan("work")) {
            // no-op body
        }

        List<Tracer.FinishedSpan> finished = tracer.finishedSpans();
        assertEquals(1, finished.size());
        assertEquals("work", finished.get(0).name());
        assertTrue(finished.get(0).durationSeconds() >= 0);
    }

    @Test
    void tryWithResourcesCallsEndEvenOnException() {
        Tracer tracer = new Tracer();

        assertThrows(IllegalStateException.class, () -> {
            try (Span span = tracer.startSpan("risky")) {
                throw new IllegalStateException("boom");
            }
        });

        List<Tracer.FinishedSpan> finished = tracer.finishedSpans();
        assertEquals(1, finished.size());
        assertEquals("risky", finished.get(0).name());
    }

    @Test
    void explicitEndRecordsFinishedSpan() {
        Tracer tracer = new Tracer();

        Span span = tracer.startSpan("manual");
        span.end();

        List<Tracer.FinishedSpan> finished = tracer.finishedSpans();
        assertEquals(1, finished.size());
        assertEquals("manual", finished.get(0).name());
    }

    @Test
    void endCalledTwiceDoesNotThrowAndRecordsOnce() {
        Tracer tracer = new Tracer();

        Span span = tracer.startSpan("double-end");
        span.end();

        assertDoesNotThrow(span::end);
        assertEquals(1, tracer.finishedSpans().size());
    }

    @Test
    void endAfterTryWithResourcesDoesNotThrowOrDuplicate() {
        Tracer tracer = new Tracer();
        Span span = tracer.startSpan("cm-then-manual");

        try (span) {
            // no-op body
        }

        assertDoesNotThrow(span::end);
        assertEquals(1, tracer.finishedSpans().size());
    }

    @Test
    void twoSpansStartedBeforeEitherEndsAreIndependent() {
        Tracer tracer = new Tracer();

        Span spanA = tracer.startSpan("outer");
        Span spanB = tracer.startSpan("inner");

        spanB.end();
        spanA.end();

        List<Tracer.FinishedSpan> finished = tracer.finishedSpans();
        assertEquals(2, finished.size());
        assertEquals("inner", finished.get(0).name());
        assertEquals("outer", finished.get(1).name());
    }

    @Test
    void multipleSpansAcrossTracerLifetimeAllAppearInFinishedSpans() {
        Tracer tracer = new Tracer();

        try (Span span = tracer.startSpan("first")) {
            // no-op body
        }
        try (Span span = tracer.startSpan("second")) {
            // no-op body
        }

        List<Tracer.FinishedSpan> finished = tracer.finishedSpans();
        assertEquals(2, finished.size());
        assertEquals("first", finished.get(0).name());
        assertEquals("second", finished.get(1).name());
    }

    @Test
    void spanRecordsAPlausibleNonzeroDurationWithRealSleep() throws InterruptedException {
        Tracer tracer = new Tracer();

        try (Span span = tracer.startSpan("sleepy")) {
            Thread.sleep(10);
        }

        List<Tracer.FinishedSpan> finished = tracer.finishedSpans();
        assertTrue(finished.get(0).durationSeconds() > 0);
    }
}
