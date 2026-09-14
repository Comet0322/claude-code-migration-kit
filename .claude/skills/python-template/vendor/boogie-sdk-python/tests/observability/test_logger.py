"""Tests for Logger. See boogie-sdk-api.md (this skill's library doc) section 5.4
(observability).

The design doc only gives the method shapes (`info(msg, **fields)`,
`warn(msg, **fields)`, `error(msg, exc=None, **fields)`) — there is no real
log aggregator behind this fake, so this test file pins down the testable
convention:

**Additive convention beyond the design doc**: `Logger.__init__` takes an
optional `sink: Callable[[dict], None] | None = None` parameter. When a
sink is supplied, every call to `info`/`warn`/`error` builds a structured
record dict and passes it to the sink instead of (or as well as) printing.
The record dict always has:

- `"level"`: one of the literal strings `"info"`, `"warn"`, `"error"`,
  matching the method that was called.
- `"msg"`: the `msg` argument, unmodified.
- every keyword in `**fields`, merged directly into the top level of the
  record dict (so `logger.info("x", user_id=1)` produces a record
  containing `"user_id": 1`).

For `error()`, the optional `exc` argument is captured under the dedicated
key `"exc"` — as `str(exc)` when an exception instance is given, or `None`
when `exc` is omitted. This keeps the record JSON-serializable (a raw
`BaseException` object is not) and keeps `error()`'s shape consistent with
`info`/`warn` when `exc` isn't passed.

With no `sink` given, the class must still be usable standalone (the design
doc doesn't require a sink), so it falls back to some default behavior
(e.g. printing JSON to stdout) — this file does not test that default path
in detail since it isn't deterministic/observable without capturing stdout;
it only checks that omitting `sink` doesn't raise.
"""

from __future__ import annotations

from boogie_sdk.observability.logger import Logger


def test_info_calls_sink_with_level_info_and_msg() -> None:
    records: list[dict] = []
    logger = Logger(sink=records.append)

    logger.info("hello")

    assert len(records) == 1
    assert records[0]["level"] == "info"
    assert records[0]["msg"] == "hello"


def test_warn_calls_sink_with_level_warn() -> None:
    records: list[dict] = []
    logger = Logger(sink=records.append)

    logger.warn("careful")

    assert records[0]["level"] == "warn"
    assert records[0]["msg"] == "careful"


def test_error_calls_sink_with_level_error() -> None:
    records: list[dict] = []
    logger = Logger(sink=records.append)

    logger.error("boom")

    assert records[0]["level"] == "error"
    assert records[0]["msg"] == "boom"


def test_fields_are_merged_into_the_record() -> None:
    records: list[dict] = []
    logger = Logger(sink=records.append)

    logger.info("request handled", request_id="abc123", status_code=200)

    record = records[0]
    assert record["request_id"] == "abc123"
    assert record["status_code"] == 200


def test_fields_are_merged_for_warn_and_error_too() -> None:
    records: list[dict] = []
    logger = Logger(sink=records.append)

    logger.warn("retrying", attempt=2)
    logger.error("gave up", attempt=3)

    assert records[0]["attempt"] == 2
    assert records[1]["attempt"] == 3


def test_error_without_exc_records_none_for_exc_key() -> None:
    records: list[dict] = []
    logger = Logger(sink=records.append)

    logger.error("no exception here")

    assert records[0]["exc"] is None


def test_error_with_exc_captures_it_as_a_string() -> None:
    records: list[dict] = []
    logger = Logger(sink=records.append)

    try:
        raise ValueError("bad value")
    except ValueError as e:
        logger.error("failed", exc=e)

    assert "bad value" in records[0]["exc"]


def test_info_and_warn_do_not_populate_an_exc_key() -> None:
    records: list[dict] = []
    logger = Logger(sink=records.append)

    logger.info("hi")
    logger.warn("careful")

    assert "exc" not in records[0]
    assert "exc" not in records[1]


def test_multiple_calls_each_produce_their_own_record() -> None:
    records: list[dict] = []
    logger = Logger(sink=records.append)

    logger.info("first")
    logger.info("second")

    assert len(records) == 2
    assert records[0]["msg"] == "first"
    assert records[1]["msg"] == "second"


def test_logger_without_sink_does_not_raise() -> None:
    logger = Logger()

    logger.info("standalone")
    logger.warn("standalone")
    logger.error("standalone")
