"""Tests for Tracer and Span. See boogie-sdk-api.md (this skill's library doc)
section 5.4 (observability).

The design doc only documents `start_span(name) -> Span`, and that a span
"結束" (ends) either via `span.end()` or via `with` (the stub's
`Span.__enter__`/`__exit__` already call `end()`). There is no real
OTel/Jaeger collector behind this fake and no design-doc read-back method,
so this test file pins down the testable conventions:

**Additive convention beyond the design doc**: `Tracer` keeps a
`finished_spans: list[tuple[str, float]]` attribute — a list of
`(name, duration_seconds)` tuples, appended to exactly once each time a
span it created finishes (i.e. the first time `end()` runs on that span,
however it's triggered: direct call or `with`-block exit including via
exception). This is the only way to observe a span's outcome given the
design doc has no read-back API, flagged here for the acceptance reviewer.

Other conventions tested here:

- `end()` must not append twice, and must not raise, if called more than
  once on the same span (idempotent-safe), whether the second call is
  explicit or happens via `__exit__` after an explicit `end()`.
- Starting a second span before ending the first does not raise and both
  spans are tracked independently — trace-context propagation/parenting
  itself is out of scope per the task brief.
- `duration_seconds` for a finished span is a plausible non-negative
  number. To keep this fast and deterministic, tests either monkeypatch
  `time.monotonic` (used as the time source, per this file's convention)
  or accept a small real sleep (a few ms) as a simpler alternative for
  "nonzero duration" checks.
"""

from __future__ import annotations

import time

import pytest

from boogie_sdk.observability.tracer import Tracer


def test_start_span_returns_a_span_usable_as_context_manager() -> None:
    tracer = Tracer()

    with tracer.start_span("work") as span:
        assert span is not None


def test_context_manager_exit_calls_end_and_records_finished_span() -> None:
    tracer = Tracer()

    with tracer.start_span("work"):
        pass

    assert len(tracer.finished_spans) == 1
    name, duration = tracer.finished_spans[0]
    assert name == "work"
    assert duration >= 0


def test_context_manager_calls_end_even_on_exception() -> None:
    tracer = Tracer()

    with pytest.raises(ValueError):
        with tracer.start_span("risky"):
            raise ValueError("boom")

    assert len(tracer.finished_spans) == 1
    assert tracer.finished_spans[0][0] == "risky"


def test_explicit_end_records_finished_span() -> None:
    tracer = Tracer()

    span = tracer.start_span("manual")
    span.end()

    assert len(tracer.finished_spans) == 1
    assert tracer.finished_spans[0][0] == "manual"


def test_end_called_twice_does_not_raise_and_records_once() -> None:
    tracer = Tracer()

    span = tracer.start_span("double-end")
    span.end()
    span.end()

    assert len(tracer.finished_spans) == 1


def test_end_after_context_manager_exit_does_not_raise_or_duplicate() -> None:
    tracer = Tracer()

    with tracer.start_span("cm-then-manual") as span:
        pass
    span.end()

    assert len(tracer.finished_spans) == 1


def test_two_spans_started_before_either_ends_are_independent() -> None:
    tracer = Tracer()

    span_a = tracer.start_span("outer")
    span_b = tracer.start_span("inner")

    span_b.end()
    span_a.end()

    assert len(tracer.finished_spans) == 2
    names = [name for name, _ in tracer.finished_spans]
    assert names == ["inner", "outer"]


def test_multiple_spans_across_tracer_lifetime_all_appear_in_finished_spans() -> None:
    tracer = Tracer()

    with tracer.start_span("first"):
        pass
    with tracer.start_span("second"):
        pass

    assert [name for name, _ in tracer.finished_spans] == ["first", "second"]


def test_span_duration_reflects_elapsed_monotonic_time(monkeypatch) -> None:
    # Two calls are expected (start, end); any extra calls keep returning
    # the last value instead of raising, so the test degrades gracefully
    # if the implementation samples the clock more than twice per span.
    pending = [100.0, 100.25]

    def fake_monotonic() -> float:
        return pending.pop(0) if pending else 100.25

    monkeypatch.setattr(time, "monotonic", fake_monotonic)

    tracer = Tracer()
    span = tracer.start_span("timed")
    span.end()

    _, duration = tracer.finished_spans[0]
    assert duration == pytest.approx(0.25)


def test_span_records_a_plausible_nonzero_duration_with_real_sleep() -> None:
    tracer = Tracer()

    with tracer.start_span("sleepy"):
        time.sleep(0.01)

    _, duration = tracer.finished_spans[0]
    assert duration > 0
