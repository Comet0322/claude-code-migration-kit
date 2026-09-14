"""Tests for SchedulerClient. See boogie-sdk-api.md (this skill's library doc)
section 5.2.

Conventions pinned down by this test file (none exist yet beyond the
public method shapes):

- **Lock semantics**: `lock(name, ttl)` is non-blocking "try-lock"
  semantics, not blocking-wait. If `name` is already held by an
  outstanding, unreleased `Lock`, a second `lock()` call for the *same
  name* raises `InfraError` immediately (chosen over blocking so tests
  stay fast and deterministic). The returned `Lock` is a context manager
  (usable via `with sdk.lock(...):`) and also exposes an explicit
  `release()`. After `release()` (directly or via `__exit__`), the name
  becomes lockable again. Locks for different names never contend with
  each other.
- **schedule_cron**: real background scheduling isn't deterministically
  testable, so this fake treats `schedule_cron(cron_expr, task)` as
  "register only" — it must not raise and must not execute `task`
  synchronously. As a test-only introspection point, `SchedulerClient`
  exposes a `_registered_jobs` list (each entry pairing the registered
  `cron_expr` and `task`) so tests can assert registration happened
  without needing real scheduling.
"""

from __future__ import annotations

from datetime import timedelta

import pytest

from boogie_sdk.core.errors import InfraError
from boogie_sdk.infra.scheduler_client import Lock, SchedulerClient


@pytest.fixture
def client() -> SchedulerClient:
    return SchedulerClient()


# -- lock: acquire / contention -----------------------------------------------


def test_lock_returns_a_lock_object(client: SchedulerClient) -> None:
    lock = client.lock("job-a", ttl=timedelta(seconds=30))
    assert isinstance(lock, Lock)
    lock.release()


def test_second_lock_for_same_name_while_held_raises_infra_error(
    client: SchedulerClient,
) -> None:
    held = client.lock("job-a", ttl=timedelta(seconds=30))

    with pytest.raises(InfraError):
        client.lock("job-a", ttl=timedelta(seconds=30))

    held.release()


def test_locks_for_different_names_do_not_contend(client: SchedulerClient) -> None:
    lock_a = client.lock("job-a", ttl=timedelta(seconds=30))
    lock_b = client.lock("job-b", ttl=timedelta(seconds=30))  # must not raise

    lock_a.release()
    lock_b.release()


# -- lock: release makes the name lockable again ------------------------------


def test_lock_becomes_available_again_after_explicit_release(
    client: SchedulerClient,
) -> None:
    first = client.lock("job-a", ttl=timedelta(seconds=30))
    first.release()

    second = client.lock("job-a", ttl=timedelta(seconds=30))  # must not raise
    second.release()


def test_lock_is_usable_as_a_context_manager(client: SchedulerClient) -> None:
    with client.lock("job-a", ttl=timedelta(seconds=30)):
        # While held, a second acquisition attempt fails.
        with pytest.raises(InfraError):
            client.lock("job-a", ttl=timedelta(seconds=30))

    # After the `with` block exits, the name is lockable again.
    lock = client.lock("job-a", ttl=timedelta(seconds=30))
    lock.release()


def test_context_manager_releases_even_if_body_raises(
    client: SchedulerClient,
) -> None:
    class BoomError(Exception):
        pass

    with pytest.raises(BoomError):
        with client.lock("job-a", ttl=timedelta(seconds=30)):
            raise BoomError

    # Lock must have been released on the way out despite the exception.
    lock = client.lock("job-a", ttl=timedelta(seconds=30))
    lock.release()


# -- schedule_cron: register-only ---------------------------------------------


def test_schedule_cron_does_not_raise(client: SchedulerClient) -> None:
    client.schedule_cron("0 * * * *", lambda: None)


def test_schedule_cron_does_not_execute_task_synchronously(
    client: SchedulerClient,
) -> None:
    executed = {"flag": False}

    def task() -> None:
        executed["flag"] = True

    client.schedule_cron("0 * * * *", task)

    assert executed["flag"] is False


def test_schedule_cron_registers_job_in_registered_jobs_introspection(
    client: SchedulerClient,
) -> None:
    def task() -> None:
        pass

    client.schedule_cron("*/5 * * * *", task)

    assert len(client._registered_jobs) == 1
    registered_cron_expr, registered_task = client._registered_jobs[0]
    assert registered_cron_expr == "*/5 * * * *"
    assert registered_task is task


def test_schedule_cron_multiple_registrations_accumulate(
    client: SchedulerClient,
) -> None:
    client.schedule_cron("0 * * * *", lambda: None)
    client.schedule_cron("0 0 * * *", lambda: None)

    assert len(client._registered_jobs) == 2
