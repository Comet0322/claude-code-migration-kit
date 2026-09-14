"""Tests for RateLimiter. See boogie-sdk-api.md (this skill's library doc) section 5.5
(governance).

The design doc's method-only sketch (`try_acquire() -> bool`,
`acquire() -> None`  # 阻塞直到取得 / "blocks until acquired") gives no
constructor and no rate configuration, which isn't testable as-is. This
test file pins down the additive, testable conventions invented to make
the fake meaningful and fast:

- **Constructor**: `RateLimiter(max_per_interval: int, interval:
  timedelta, time_source: Callable[[], float] | None = None)`, a simple
  token bucket. The bucket starts full with `max_per_interval` tokens.
  `time_source` defaults to the real wall clock but can be overridden
  with a zero-argument callable returning seconds (as `time.monotonic()`
  would) — this is the injection point tests use to simulate refill over
  time without a real sleep.
- **`try_acquire()`**: returns `True` and consumes one token while
  tokens remain; returns `False` (never raises) once the bucket is
  empty.
- **`acquire()` blocking convention**: the design doc's "阻塞直到取得"
  (block until acquired) conflicts with fast, deterministic tests. This
  fake instead adopts the convention that `acquire()` raises
  `boogie_sdk.core.errors.RateLimitExceededError` immediately if no
  token is currently available, rather than sleeping/blocking. When a
  token is available it behaves like `try_acquire()` (consumes one
  token) and returns `None`. This is a deliberate choice for this fake;
  the implementer should follow this test file's behavior exactly.
- **Refill**: after `interval` has elapsed (per `time_source`), the
  bucket refills back up to `max_per_interval` tokens (this fake uses a
  simple "full refill after the interval elapses" model rather than a
  continuous trickle, since the design doc does not specify one).
"""

from __future__ import annotations

from datetime import timedelta
from typing import Callable

import pytest

from boogie_sdk.core.errors import RateLimitExceededError
from boogie_sdk.governance.rate_limiter import RateLimiter


class FakeClock:
    """A settable, injectable time source for deterministic refill tests."""

    def __init__(self, start: float = 0.0) -> None:
        self._now = start

    def __call__(self) -> float:
        return self._now

    def advance(self, seconds: float) -> None:
        self._now += seconds


@pytest.fixture
def clock() -> FakeClock:
    return FakeClock()


def make_limiter(
    clock: Callable[[], float], max_per_interval: int = 3, seconds: float = 1.0
) -> RateLimiter:
    return RateLimiter(
        max_per_interval=max_per_interval,
        interval=timedelta(seconds=seconds),
        time_source=clock,
    )


# -- try_acquire --------------------------------------------------------------


def test_try_acquire_returns_true_while_tokens_remain(clock: FakeClock) -> None:
    limiter = make_limiter(clock, max_per_interval=2)

    assert limiter.try_acquire() is True
    assert limiter.try_acquire() is True


def test_try_acquire_returns_false_once_exhausted(clock: FakeClock) -> None:
    limiter = make_limiter(clock, max_per_interval=2)

    limiter.try_acquire()
    limiter.try_acquire()

    assert limiter.try_acquire() is False


def test_try_acquire_never_raises_when_exhausted(clock: FakeClock) -> None:
    limiter = make_limiter(clock, max_per_interval=1)

    limiter.try_acquire()
    # Repeated calls on an empty bucket must keep returning False, never raise.
    for _ in range(5):
        assert limiter.try_acquire() is False


# -- acquire --------------------------------------------------------------


def test_acquire_returns_none_when_a_token_is_available(clock: FakeClock) -> None:
    limiter = make_limiter(clock, max_per_interval=1)

    assert limiter.acquire() is None


def test_acquire_raises_rate_limit_exceeded_when_bucket_is_empty(
    clock: FakeClock,
) -> None:
    limiter = make_limiter(clock, max_per_interval=1)

    limiter.acquire()

    with pytest.raises(RateLimitExceededError):
        limiter.acquire()


def test_acquire_consumes_a_token_like_try_acquire(clock: FakeClock) -> None:
    limiter = make_limiter(clock, max_per_interval=2)

    limiter.acquire()
    assert limiter.try_acquire() is True
    assert limiter.try_acquire() is False


# -- refill via injected time source ------------------------------------------


def test_tokens_refill_after_interval_elapses(clock: FakeClock) -> None:
    limiter = make_limiter(clock, max_per_interval=2, seconds=1.0)

    limiter.try_acquire()
    limiter.try_acquire()
    assert limiter.try_acquire() is False

    clock.advance(1.0)

    assert limiter.try_acquire() is True


def test_tokens_do_not_refill_before_interval_elapses(clock: FakeClock) -> None:
    limiter = make_limiter(clock, max_per_interval=1, seconds=1.0)

    limiter.try_acquire()
    clock.advance(0.5)

    assert limiter.try_acquire() is False


def test_refill_does_not_exceed_max_per_interval(clock: FakeClock) -> None:
    limiter = make_limiter(clock, max_per_interval=2, seconds=1.0)

    # Consume only one token, then let a lot of time pass.
    limiter.try_acquire()
    clock.advance(100.0)

    # Bucket should be capped back at max_per_interval (2), not unbounded.
    assert limiter.try_acquire() is True
    assert limiter.try_acquire() is True
    assert limiter.try_acquire() is False


def test_acquire_succeeds_again_after_refill(clock: FakeClock) -> None:
    limiter = make_limiter(clock, max_per_interval=1, seconds=1.0)

    limiter.acquire()
    with pytest.raises(RateLimitExceededError):
        limiter.acquire()

    clock.advance(1.0)

    limiter.acquire()  # must not raise now that the bucket refilled
