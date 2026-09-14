"""RateLimiter stub. See boogie-sdk-api.md (this skill's library doc) section 5.5 (governance).

Token-bucket fake with a "full refill after the interval elapses" model
(see the test module docstring for the exact conventions pinned down for
`acquire()`'s non-blocking behavior).
"""

from __future__ import annotations

import time
from datetime import timedelta
from typing import Callable

from boogie_sdk.core.errors import RateLimitExceededError


class RateLimiter:
    def __init__(
        self,
        max_per_interval: int,
        interval: timedelta,
        time_source: Callable[[], float] | None = None,
    ) -> None:
        self._max_per_interval = max_per_interval
        self._interval_seconds = interval.total_seconds()
        self._time_source = time_source if time_source is not None else time.monotonic
        self._tokens = max_per_interval
        self._window_start = self._time_source()

    def _refill_if_needed(self) -> None:
        now = self._time_source()
        if now - self._window_start >= self._interval_seconds:
            self._tokens = self._max_per_interval
            self._window_start = now

    def try_acquire(self) -> bool:
        self._refill_if_needed()
        if self._tokens > 0:
            self._tokens -= 1
            return True
        return False

    def acquire(self) -> None:
        if not self.try_acquire():
            raise RateLimitExceededError("no token available")
