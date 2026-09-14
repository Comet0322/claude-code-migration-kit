"""Tests for HealthCheck and HealthReport. See
boogie-sdk-api.md (this skill's library doc) section 5.5 (governance).

The design doc documents `register(name, check)` and
`status() -> HealthReport` but is silent on two edge cases this test
file pins down as conventions:

- **No checks registered**: `status()` is vacuously healthy — `healthy`
  is `True` and `checks` is an empty dict. This mirrors the usual
  "no evidence of failure" convention for health aggregation (an empty
  AND is `True`) rather than treating "nothing registered" as an error
  or as unhealthy.
- **A check that raises**: real health checks can throw (e.g. a DB ping
  that raises on a dropped connection). Rather than letting the
  exception propagate out of `status()` and take down whatever is
  polling health, a raising check is caught and treated as a failing
  (`False`) result for that check's entry, and it drags overall
  `healthy` to `False` just like an ordinary `False` return would.

Other behavior tested: `checks` is a `dict[str, bool]` keyed by the
registered name, and overall `healthy` is the AND of all individual
results.
"""

from __future__ import annotations

from boogie_sdk.governance.health_check import HealthCheck, HealthReport


def test_status_returns_a_health_report() -> None:
    hc = HealthCheck()
    report = hc.status()
    assert isinstance(report, HealthReport)


def test_no_checks_registered_is_healthy_with_empty_checks_dict() -> None:
    hc = HealthCheck()

    report = hc.status()

    assert report.healthy is True
    assert report.checks == {}


def test_all_checks_passing_is_overall_healthy_true() -> None:
    hc = HealthCheck()
    hc.register("db", lambda: True)
    hc.register("cache", lambda: True)

    report = hc.status()

    assert report.healthy is True
    assert report.checks == {"db": True, "cache": True}


def test_any_failing_check_makes_overall_healthy_false() -> None:
    hc = HealthCheck()
    hc.register("db", lambda: True)
    hc.register("cache", lambda: False)

    report = hc.status()

    assert report.healthy is False


def test_checks_dict_reflects_each_individual_result() -> None:
    hc = HealthCheck()
    hc.register("db", lambda: True)
    hc.register("cache", lambda: False)
    hc.register("queue", lambda: True)

    report = hc.status()

    assert report.checks == {"db": True, "cache": False, "queue": True}


def test_check_that_raises_is_treated_as_failing_not_propagated() -> None:
    hc = HealthCheck()

    def boom() -> bool:
        raise RuntimeError("connection refused")

    hc.register("flaky", boom)

    report = hc.status()  # must not raise

    assert report.checks["flaky"] is False
    assert report.healthy is False


def test_a_raising_check_does_not_affect_other_checks_results() -> None:
    hc = HealthCheck()

    def boom() -> bool:
        raise RuntimeError("boom")

    hc.register("flaky", boom)
    hc.register("healthy-one", lambda: True)

    report = hc.status()

    assert report.checks == {"flaky": False, "healthy-one": True}


def test_status_can_be_called_multiple_times_and_reflects_current_state() -> None:
    hc = HealthCheck()
    state = {"ok": True}
    hc.register("toggle", lambda: state["ok"])

    assert hc.status().healthy is True

    state["ok"] = False

    assert hc.status().healthy is False
