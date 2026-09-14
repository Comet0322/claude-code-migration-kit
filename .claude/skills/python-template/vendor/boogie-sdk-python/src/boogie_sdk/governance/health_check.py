"""HealthCheck stub. See boogie-sdk-api.md (this skill's library doc) section 5.5 (governance).

Skeleton only — implemented during the Phase 1 TDD loop for the `governance` module.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable


@dataclass(frozen=True)
class HealthReport:
    healthy: bool
    checks: dict[str, bool] = field(default_factory=dict)


class HealthCheck:
    def __init__(self) -> None:
        self._checks: dict[str, Callable[[], bool]] = {}

    def register(self, name: str, check: Callable[[], bool]) -> None:
        self._checks[name] = check

    def status(self) -> HealthReport:
        results: dict[str, bool] = {}
        for name, check in self._checks.items():
            try:
                results[name] = bool(check())
            except Exception:
                results[name] = False

        healthy = all(results.values())
        return HealthReport(healthy=healthy, checks=results)
