"""IdGenerator stub. See boogie-sdk-api.md (this skill's library doc) section 5.5 (governance).

Implements a simple Snowflake-style id: a monotonic counter combined with
a timestamp component, guarded by a lock so ids are unique and
non-decreasing across successive calls on the same instance.
"""

from __future__ import annotations

import itertools
import threading
import time


class IdGenerator:
    # 22 bits reserved for the per-tick sequence, matching classic
    # Snowflake-style layouts (timestamp << 22 | sequence).
    _SEQUENCE_BITS = 22
    _SEQUENCE_MASK = (1 << _SEQUENCE_BITS) - 1

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._counter = itertools.count()
        self._last_id = -1

    def next_id(self) -> int:
        with self._lock:
            timestamp_ms = int(time.time() * 1000)
            sequence = next(self._counter) & self._SEQUENCE_MASK
            candidate = (timestamp_ms << self._SEQUENCE_BITS) | sequence

            if candidate <= self._last_id:
                candidate = self._last_id + 1

            self._last_id = candidate
            return candidate
