"""SchedulerClient stub. See boogie-sdk-api.md (this skill's library doc) section 5.2 (infra).

Non-blocking try-lock semantics and register-only `schedule_cron` with a
`_registered_jobs` introspection list — see
tests/infra/test_scheduler_client.py module docstring for
the pinned-down conventions.
"""

from __future__ import annotations

import threading
from datetime import timedelta
from typing import Callable

from boogie_sdk.core.errors import InfraError


class Lock:
    def __init__(self, name: str, scheduler: "SchedulerClient") -> None:
        self._name = name
        self._scheduler = scheduler
        self._released = False

    def release(self) -> None:
        if self._released:
            return
        self._released = True
        self._scheduler._release(self._name)

    def __enter__(self) -> "Lock":
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.release()


class SchedulerClient:
    def __init__(self) -> None:
        self._held_locks: set[str] = set()
        self._guard = threading.Lock()
        self._registered_jobs: list[tuple[str, Callable[[], None]]] = []

    def lock(self, name: str, ttl: timedelta) -> Lock:
        with self._guard:
            if name in self._held_locks:
                raise InfraError(f"lock already held: {name!r}")
            self._held_locks.add(name)
        return Lock(name, self)

    def _release(self, name: str) -> None:
        with self._guard:
            self._held_locks.discard(name)

    def schedule_cron(self, cron_expr: str, task: Callable[[], None]) -> None:
        self._registered_jobs.append((cron_expr, task))
