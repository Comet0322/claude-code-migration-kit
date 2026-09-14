package com.boogie.sdk.observability;

import org.junit.jupiter.api.Test;

import java.util.Map;

import static org.junit.jupiter.api.Assertions.assertEquals;

/**
 * Tests for MetricsClient, Counter, Gauge, Timer. See boogie-sdk-api.md
 * section 5.4 (observability).
 *
 * <p>The design doc only documents {@code counter(name) -> Counter},
 * {@code gauge(name) -> Gauge}, {@code timer(name) -> Timer}, {@code
 * Counter.increment()}/{@code increment(long amount)}, {@code
 * Gauge.set(double value)}, {@code Timer.record(double
 * durationSeconds)}. There is no real Prometheus/StatsD backend behind
 * this fake and no design-doc method to read values back, so this test
 * file pins down the testable conventions, mirroring the Python port's
 * {@code MetricsClient} ({@code
 * boogie-sdk/python/src/boogie_sdk/observability/metrics_client.py}):
 *
 * <ul>
 *   <li>Calling {@code counter(name)} (or {@code gauge}/{@code timer})
 *       twice with the same {@code name} must return handles that
 *       operate on the *same* underlying value — i.e. they behave as if
 *       backed by a shared per-name store, regardless of whether the two
 *       calls return the literal same object.
 *   <li>{@code Counter.increment()} defaults to an amount of 1;
 *       {@code increment(long amount)} adds the given amount. Both
 *       accumulate across calls on handles obtained from the same name.
 *   <li>{@code Gauge.set(value)}: last-write-wins — only the most
 *       recently set value is kept.
 *   <li>{@code Timer.record(durationSeconds)}: accumulates
 *       *observations*, not a single scalar. This test file's picked
 *       convention: a timer tracks a count of {@code record()} calls and
 *       a running total of seconds, so mean duration is recoverable as
 *       total / count. Multiple {@code record()} calls on the same timer
 *       name increase both.
 * </ul>
 *
 * <p><b>Additive convention beyond the design doc:</b> since there is no
 * design-doc method to read a metric's current value, {@code
 * MetricsClient} gets a {@code Map<String, Double> snapshot()} method
 * purely for test verification — the same pattern as {@code
 * ServiceDiscoveryClient.register} in the `infra` module (an extension
 * flagged here for the acceptance reviewer). Keys are the metric names
 * passed to {@code counter}/{@code gauge}/{@code timer}; this test
 * file's convention for values:
 *
 * <ul>
 *   <li>counters snapshot to their current total.
 *   <li>gauges snapshot to their last-set value.
 *   <li>timers snapshot to their running total of seconds (the sum of
 *       recorded durations) — since {@code snapshot()} returns a single
 *       {@code double} per name, and the call count is separately
 *       observable by calling {@code record()} a known number of times
 *       and checking total seconds divided by that count.
 * </ul>
 *
 * <p>Metric names across {@code counter}/{@code gauge}/{@code timer} are
 * treated as independent namespaces in this test file (a counter named
 * "x" and a gauge named "x" are not required to collide) — only
 * same-kind, same-name lookups are tested here since the design doc does
 * not specify cross-kind collision behavior.
 *
 * <p>{@code counter}/{@code gauge}/{@code timer}/{@code snapshot}
 * currently throw {@link UnsupportedOperationException} (skeleton
 * stage) — every test below is expected to fail with that exception
 * until the `implementer` stage fills in real bodies; that failure mode
 * is expected/fine per the TDD pipeline.
 */
class MetricsClientTest {

    // -- Counter --------------------------------------------------------

    @Test
    void counterIncrementDefaultsToAmount1() {
        MetricsClient client = new MetricsClient();
        Counter counter = client.counter("requests");

        counter.increment();

        assertEquals(1.0, client.snapshot().get("requests"));
    }

    @Test
    void counterIncrementAcceptsExplicitAmount() {
        MetricsClient client = new MetricsClient();
        Counter counter = client.counter("bytesSent");

        counter.increment(5);

        assertEquals(5.0, client.snapshot().get("bytesSent"));
    }

    @Test
    void counterAccumulatesAcrossCalls() {
        MetricsClient client = new MetricsClient();
        Counter counter = client.counter("requests");

        counter.increment();
        counter.increment();

        assertEquals(2.0, client.snapshot().get("requests"));
    }

    @Test
    void sameCounterNameSharesUnderlyingValueAcrossHandles() {
        MetricsClient client = new MetricsClient();

        client.counter("requests").increment();
        client.counter("requests").increment();

        assertEquals(2.0, client.snapshot().get("requests"));
    }

    @Test
    void differentCounterNamesAreIndependent() {
        MetricsClient client = new MetricsClient();

        client.counter("a").increment();
        client.counter("b").increment(10);

        Map<String, Double> snapshot = client.snapshot();
        assertEquals(1.0, snapshot.get("a"));
        assertEquals(10.0, snapshot.get("b"));
    }

    // -- Gauge ------------------------------------------------------------

    @Test
    void gaugeSetRecordsTheValue() {
        MetricsClient client = new MetricsClient();
        Gauge gauge = client.gauge("queueDepth");

        gauge.set(42);

        assertEquals(42.0, client.snapshot().get("queueDepth"));
    }

    @Test
    void gaugeSetIsLastWriteWins() {
        MetricsClient client = new MetricsClient();
        Gauge gauge = client.gauge("queueDepth");

        gauge.set(10);
        gauge.set(3);

        assertEquals(3.0, client.snapshot().get("queueDepth"));
    }

    @Test
    void sameGaugeNameSharesUnderlyingValueAcrossHandles() {
        MetricsClient client = new MetricsClient();

        client.gauge("temp").set(1);
        client.gauge("temp").set(99);

        assertEquals(99.0, client.snapshot().get("temp"));
    }

    // -- Timer --------------------------------------------------------------

    @Test
    void timerRecordContributesToTotalSeconds() {
        MetricsClient client = new MetricsClient();
        Timer timer = client.timer("requestDuration");

        timer.record(0.5);

        assertEquals(0.5, client.snapshot().get("requestDuration"));
    }

    @Test
    void timerAccumulatesMultipleObservations() {
        MetricsClient client = new MetricsClient();
        Timer timer = client.timer("requestDuration");

        timer.record(0.5);
        timer.record(1.5);

        assertEquals(2.0, client.snapshot().get("requestDuration"));
    }

    @Test
    void sameTimerNameSharesUnderlyingValueAcrossHandles() {
        MetricsClient client = new MetricsClient();

        client.timer("requestDuration").record(1.0);
        client.timer("requestDuration").record(2.0);

        assertEquals(3.0, client.snapshot().get("requestDuration"));
    }

    @Test
    void differentTimerNamesAreIndependent() {
        MetricsClient client = new MetricsClient();

        client.timer("a").record(1.0);
        client.timer("b").record(2.0);

        Map<String, Double> snapshot = client.snapshot();
        assertEquals(1.0, snapshot.get("a"));
        assertEquals(2.0, snapshot.get("b"));
    }

    // -- snapshot across kinds --------------------------------------------

    @Test
    void snapshotIncludesAllMetricKindsByName() {
        MetricsClient client = new MetricsClient();
        client.counter("requests").increment();
        client.gauge("queueDepth").set(7);
        client.timer("requestDuration").record(0.25);

        Map<String, Double> snapshot = client.snapshot();

        assertEquals(1.0, snapshot.get("requests"));
        assertEquals(7.0, snapshot.get("queueDepth"));
        assertEquals(0.25, snapshot.get("requestDuration"));
    }
}
