"""Tests for MetricsClient, Counter, Gauge, Timer. See
boogie-sdk-api.md (this skill's library doc) section 5.4 (observability).

The design doc only documents `counter(name) -> Counter`,
`gauge(name) -> Gauge`, `timer(name) -> Timer`, `Counter.increment(amount=1)`,
`Gauge.set(value)`, `Timer.record(duration_seconds)`. There is no real
Prometheus/StatsD backend behind this fake and no design-doc method to read
values back, so this test file pins down the testable conventions:

- Calling `counter(name)` (or `gauge`/`timer`) twice with the same `name`
  must return handles that operate on the *same* underlying value — i.e.
  they behave as if backed by a shared per-name store, regardless of
  whether the two calls return the literal same Python object.
- `Counter.increment(amount=1)`: accumulates. Calling it twice (with the
  default `amount`) on handles obtained from the same name brings the
  total to 2.
- `Gauge.set(value)`: last-write-wins — only the most recent value is kept.
- `Timer.record(duration_seconds)`: accumulates *observations*, not a
  single scalar. This test file's picked convention: a timer tracks
  `count` (number of `record()` calls) and `total_seconds` (sum of all
  recorded durations), so mean duration is recoverable as
  `total_seconds / count`. Multiple `record()` calls on the same timer
  name increase both.

**Additive convention beyond the design doc**: since there is no
design-doc method to read a metric's current value, `MetricsClient` gets a
`snapshot() -> dict[str, float]` method purely for test verification —
the same pattern as `ServiceDiscoveryClient.register` in the `infra`
module (an extension flagged here for the acceptance reviewer). Keys are
the metric names passed to `counter`/`gauge`/`timer`; this test file's
convention for values:

- counters snapshot to their current integer/float total.
- gauges snapshot to their last-set value.
- timers snapshot to their `total_seconds` (the sum of recorded
  durations) — since `snapshot()` returns a single float per name, and
  `count` is separately observable by calling `record()` a known number
  of times and checking `total_seconds` divided by that count.

Metric names across `counter`/`gauge`/`timer` are treated as independent
namespaces in this test file (a counter named "x" and a gauge named "x"
are not required to collide) — only same-kind, same-name lookups are
tested here since the design doc does not specify cross-kind collision
behavior.
"""

from __future__ import annotations

from boogie_sdk.observability.metrics_client import MetricsClient


# -- Counter --------------------------------------------------------------


def test_counter_increment_defaults_to_amount_1() -> None:
    client = MetricsClient()
    counter = client.counter("requests")

    counter.increment()

    assert client.snapshot()["requests"] == 1


def test_counter_increment_accepts_explicit_amount() -> None:
    client = MetricsClient()
    counter = client.counter("bytes_sent")

    counter.increment(amount=5)

    assert client.snapshot()["bytes_sent"] == 5


def test_counter_accumulates_across_calls() -> None:
    client = MetricsClient()
    counter = client.counter("requests")

    counter.increment()
    counter.increment()

    assert client.snapshot()["requests"] == 2


def test_same_counter_name_shares_underlying_value_across_handles() -> None:
    client = MetricsClient()

    client.counter("requests").increment()
    client.counter("requests").increment()

    assert client.snapshot()["requests"] == 2


def test_different_counter_names_are_independent() -> None:
    client = MetricsClient()

    client.counter("a").increment()
    client.counter("b").increment(amount=10)

    snapshot = client.snapshot()
    assert snapshot["a"] == 1
    assert snapshot["b"] == 10


# -- Gauge ------------------------------------------------------------------


def test_gauge_set_records_the_value() -> None:
    client = MetricsClient()
    gauge = client.gauge("queue_depth")

    gauge.set(42)

    assert client.snapshot()["queue_depth"] == 42


def test_gauge_set_is_last_write_wins() -> None:
    client = MetricsClient()
    gauge = client.gauge("queue_depth")

    gauge.set(10)
    gauge.set(3)

    assert client.snapshot()["queue_depth"] == 3


def test_same_gauge_name_shares_underlying_value_across_handles() -> None:
    client = MetricsClient()

    client.gauge("temp").set(1)
    client.gauge("temp").set(99)

    assert client.snapshot()["temp"] == 99


# -- Timer --------------------------------------------------------------


def test_timer_record_contributes_to_total_seconds() -> None:
    client = MetricsClient()
    timer = client.timer("request_duration")

    timer.record(0.5)

    assert client.snapshot()["request_duration"] == 0.5


def test_timer_accumulates_multiple_observations() -> None:
    client = MetricsClient()
    timer = client.timer("request_duration")

    timer.record(0.5)
    timer.record(1.5)

    assert client.snapshot()["request_duration"] == 2.0


def test_same_timer_name_shares_underlying_value_across_handles() -> None:
    client = MetricsClient()

    client.timer("request_duration").record(1.0)
    client.timer("request_duration").record(2.0)

    assert client.snapshot()["request_duration"] == 3.0


def test_different_timer_names_are_independent() -> None:
    client = MetricsClient()

    client.timer("a").record(1.0)
    client.timer("b").record(2.0)

    snapshot = client.snapshot()
    assert snapshot["a"] == 1.0
    assert snapshot["b"] == 2.0


# -- snapshot across kinds ------------------------------------------------


def test_snapshot_includes_all_metric_kinds_by_name() -> None:
    client = MetricsClient()
    client.counter("requests").increment()
    client.gauge("queue_depth").set(7)
    client.timer("request_duration").record(0.25)

    snapshot = client.snapshot()

    assert snapshot["requests"] == 1
    assert snapshot["queue_depth"] == 7
    assert snapshot["request_duration"] == 0.25
