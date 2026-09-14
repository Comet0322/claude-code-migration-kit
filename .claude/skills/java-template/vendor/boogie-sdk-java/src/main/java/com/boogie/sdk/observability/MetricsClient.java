package com.boogie.sdk.observability;

import java.util.LinkedHashMap;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.atomic.DoubleAccumulator;
import java.util.concurrent.atomic.DoubleAdder;

/**
 * MetricsClient stub. See boogie-sdk-api.md section 5.4 (observability).
 *
 * <p>Additive beyond the design doc (test-writer stage, mirroring the
 * Python port's {@code MetricsClient}): a {@link #snapshot()} method,
 * since the design doc gives no way to read a metric's current value
 * back. Counters/gauges/timers are each their own namespace, keyed by
 * name, with shared state across repeated {@code counter}/{@code
 * gauge}/{@code timer} calls for the same name.
 */
public class MetricsClient {

    private final Map<String, DoubleAdder> counters = new ConcurrentHashMap<>();
    private final Map<String, DoubleAccumulator> gauges = new ConcurrentHashMap<>();
    private final Map<String, DoubleAdder> timers = new ConcurrentHashMap<>();

    public Counter counter(String name) {
        DoubleAdder total = counters.computeIfAbsent(name, n -> new DoubleAdder());
        return new Counter() {
            @Override
            public void increment() {
                total.add(1L);
            }

            @Override
            public void increment(long amount) {
                total.add(amount);
            }
        };
    }

    public Gauge gauge(String name) {
        DoubleAccumulator value = gauges.computeIfAbsent(name, n -> new DoubleAccumulator((x, y) -> y, 0.0));
        return value::accumulate;
    }

    public Timer timer(String name) {
        DoubleAdder totalSeconds = timers.computeIfAbsent(name, n -> new DoubleAdder());
        return totalSeconds::add;
    }

    public Map<String, Double> snapshot() {
        Map<String, Double> result = new LinkedHashMap<>();
        counters.forEach((name, value) -> result.put(name, value.sum()));
        gauges.forEach((name, value) -> result.put(name, value.doubleValue()));
        timers.forEach((name, value) -> result.put(name, value.sum()));
        return result;
    }
}
