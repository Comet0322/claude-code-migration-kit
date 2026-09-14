"""Tests for BatchTracker. See boogie-sdk-api.md (this skill's library doc) section 5.3
(deviceio).

Conventions invented for this module:

- **`create_batch(batch_id)` records an initial `"created"` `BatchEvent`.**
  `get_history(batch_id)` therefore always returns at least one event for a
  known batch — the creation itself is part of the history, not just a side
  effect that sets up empty state.
- **`get_history` returns events in chronological order** (creation first,
  then each `update_status` call in the order it was made).
- **`update_status` on an unknown `batch_id` raises `NotFoundError`.**
- **`get_history` on an unknown `batch_id` raises `NotFoundError`.**
  A batch must be created via `create_batch` before either method accepts
  its id.
"""

from __future__ import annotations

import pytest

from boogie_sdk.core.errors import NotFoundError
from boogie_sdk.deviceio.batch_tracker import BatchTracker


@pytest.fixture
def tracker() -> BatchTracker:
    return BatchTracker()


# -- create_batch / get_history: created event ------------------------------


def test_create_batch_records_initial_created_event(tracker: BatchTracker) -> None:
    tracker.create_batch("batch-1")

    history = tracker.get_history("batch-1")

    assert len(history) == 1
    assert history[0].batch_id == "batch-1"
    assert history[0].status == "created"


def test_get_history_is_chronological_including_creation_first(
    tracker: BatchTracker,
) -> None:
    tracker.create_batch("batch-1")
    tracker.update_status("batch-1", "running")
    tracker.update_status("batch-1", "completed")

    history = tracker.get_history("batch-1")

    assert [e.status for e in history] == ["created", "running", "completed"]


def test_get_history_events_are_non_decreasing_in_time(tracker: BatchTracker) -> None:
    tracker.create_batch("batch-1")
    tracker.update_status("batch-1", "running")
    tracker.update_status("batch-1", "completed")

    history = tracker.get_history("batch-1")

    timestamps = [e.at for e in history]
    assert timestamps == sorted(timestamps)


def test_update_status_appends_event_with_given_status(tracker: BatchTracker) -> None:
    tracker.create_batch("batch-1")
    tracker.update_status("batch-1", "paused")

    history = tracker.get_history("batch-1")

    assert history[-1].status == "paused"
    assert history[-1].batch_id == "batch-1"


def test_multiple_batches_have_independent_histories(tracker: BatchTracker) -> None:
    tracker.create_batch("batch-1")
    tracker.create_batch("batch-2")
    tracker.update_status("batch-1", "running")

    history_1 = tracker.get_history("batch-1")
    history_2 = tracker.get_history("batch-2")

    assert [e.status for e in history_1] == ["created", "running"]
    assert [e.status for e in history_2] == ["created"]


# -- NotFoundError for unknown batch_id --------------------------------------


def test_update_status_on_unknown_batch_raises_not_found_error(
    tracker: BatchTracker,
) -> None:
    with pytest.raises(NotFoundError):
        tracker.update_status("does-not-exist", "running")


def test_get_history_on_unknown_batch_raises_not_found_error(
    tracker: BatchTracker,
) -> None:
    with pytest.raises(NotFoundError):
        tracker.get_history("does-not-exist")
