"""Tracer stub. See boogie-sdk-api.md (this skill's library doc) section 5.4 (observability).

Skeleton only — implemented during the Phase 1 TDD loop for the `observability` module.
"""

from __future__ import annotations

import time


class Span:
    def __init__(self, tracer: "Tracer", name: str) -> None:
        self._tracer = tracer
        self._name = name
        self._start = time.monotonic()
        self._ended = False

    def end(self) -> None:
        if self._ended:
            return
        self._ended = True
        duration = time.monotonic() - self._start
        self._tracer.finished_spans.append((self._name, duration))

    def __enter__(self) -> "Span":
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.end()


class Tracer:
    def __init__(self) -> None:
        self.finished_spans: list[tuple[str, float]] = []

    def start_span(self, name: str) -> Span:
        return Span(self, name)
