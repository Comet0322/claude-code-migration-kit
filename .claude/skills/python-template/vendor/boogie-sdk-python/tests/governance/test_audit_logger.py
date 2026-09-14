"""Tests for AuditLogger. See boogie-sdk-api.md (this skill's library doc) section
5.5 (governance).

`record(actor, action, resource, result) -> None` per the design doc has
no read-back API, so there is no way to assert anything happened without
an additive introspection point. This fake exposes `records: list[dict]`
(additive, not in the design doc) — a plain list of dicts, each with the
keys `"actor"`, `"action"`, `"resource"`, `"result"` holding exactly the
values passed to the corresponding `record()` call, appended to in call
order (never reordered or deduplicated).
"""

from __future__ import annotations

import pytest

from boogie_sdk.governance.audit_logger import AuditLogger


@pytest.fixture
def logger() -> AuditLogger:
    return AuditLogger()


def test_record_returns_none(logger: AuditLogger) -> None:
    assert logger.record("alice", "delete", "doc-1", "success") is None


def test_record_appends_an_entry_to_records(logger: AuditLogger) -> None:
    logger.record("alice", "delete", "doc-1", "success")

    assert len(logger.records) == 1


def test_record_entry_preserves_all_four_fields(logger: AuditLogger) -> None:
    logger.record("alice", "delete", "doc-1", "success")

    entry = logger.records[0]
    assert entry["actor"] == "alice"
    assert entry["action"] == "delete"
    assert entry["resource"] == "doc-1"
    assert entry["result"] == "success"


def test_multiple_records_preserve_call_order(logger: AuditLogger) -> None:
    logger.record("alice", "create", "doc-1", "success")
    logger.record("bob", "update", "doc-1", "success")
    logger.record("alice", "delete", "doc-1", "denied")

    actors = [entry["actor"] for entry in logger.records]
    actions = [entry["action"] for entry in logger.records]

    assert actors == ["alice", "bob", "alice"]
    assert actions == ["create", "update", "delete"]


def test_multiple_records_are_kept_as_distinct_entries(logger: AuditLogger) -> None:
    logger.record("alice", "create", "doc-1", "success")
    logger.record("alice", "create", "doc-1", "success")

    assert len(logger.records) == 2
