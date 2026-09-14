package com.boogie.sdk.observability;

import java.util.Collections;
import java.util.List;
import java.util.concurrent.CopyOnWriteArrayList;
import java.util.concurrent.atomic.AtomicBoolean;

/**
 * Tracer stub. See boogie-sdk-api.md section 5.4 (observability).
 *
 * <p>Additive beyond the design doc (test-writer stage, mirroring the
 * Python port's {@code Tracer.finished_spans}): a {@link FinishedSpan}
 * record and a {@link #finishedSpans()} getter, since the design doc
 * gives no way to read a span's outcome back.
 */
public class Tracer {

    /**
     * One completed span: the {@code name} it was started with, and its
     * duration in seconds, measured with {@link System#nanoTime()}.
     */
    public record FinishedSpan(String name, double durationSeconds) {
    }

    private final List<FinishedSpan> finished = new CopyOnWriteArrayList<>();

    public Span startSpan(String name) {
        long startNanos = System.nanoTime();
        AtomicBoolean ended = new AtomicBoolean(false);
        return () -> {
            if (ended.compareAndSet(false, true)) {
                double durationSeconds = (System.nanoTime() - startNanos) / 1_000_000_000.0;
                finished.add(new FinishedSpan(name, durationSeconds));
            }
        };
    }

    public List<FinishedSpan> finishedSpans() {
        return Collections.unmodifiableList(finished);
    }
}
