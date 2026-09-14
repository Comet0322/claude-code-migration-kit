"""MetricsClient stub. See boogie-sdk-api.md (this skill's library doc) section 5.4 (observability).

Skeleton only — implemented during the Phase 1 TDD loop for the `observability` module.
"""

from __future__ import annotations


class Counter:
    def __init__(self, store: dict, name: str) -> None:
        self._store = store
        self._name = name
        self._store.setdefault(name, 0)

    def increment(self, amount: int = 1) -> None:
        self._store[self._name] = self._store.get(self._name, 0) + amount


class Gauge:
    def __init__(self, store: dict, name: str) -> None:
        self._store = store
        self._name = name
        self._store.setdefault(name, 0.0)

    def set(self, value: float) -> None:
        self._store[self._name] = value


class Timer:
    def __init__(self, store: dict, name: str) -> None:
        self._store = store
        self._name = name
        self._store.setdefault(name, {"total_seconds": 0.0, "count": 0})

    def record(self, duration_seconds: float) -> None:
        entry = self._store[self._name]
        entry["total_seconds"] += duration_seconds
        entry["count"] += 1


class MetricsClient:
    def __init__(self) -> None:
        self._counters: dict = {}
        self._gauges: dict = {}
        self._timers: dict = {}

    def counter(self, name: str) -> Counter:
        return Counter(self._counters, name)

    def gauge(self, name: str) -> Gauge:
        return Gauge(self._gauges, name)

    def timer(self, name: str) -> Timer:
        return Timer(self._timers, name)

    def snapshot(self) -> dict[str, float]:
        result: dict[str, float] = {}
        result.update(self._counters)
        result.update(self._gauges)
        for name, entry in self._timers.items():
            result[name] = entry["total_seconds"]
        return result
