"""Tests for FlatFileParser. See boogie-sdk-api.md (this skill's library doc)
section 5.3 (deviceio).

Conventions invented for this module (the design doc only specifies
`parse(file, schema) -> list[T]` generically):

- **Flat-file format is CSV** — a very common legacy interchange format.
  The first line is treated as a header row; each subsequent row is handed
  to `schema.parse_row(raw)` as a `dict[str, str]` keyed by header name
  (i.e. the same shape `csv.DictReader` produces).
- **Malformed-row handling: `parse` raises `ValidationError` on the first
  row whose `schema.parse_row` call raises.** This module does not silently
  skip bad data nor silently collect partial results — a flat-file feed with
  a corrupt row aborts the whole parse so the caller notices immediately.
  (An alternative would be to skip bad rows or collect per-row errors; this
  fake picks "raise immediately" and documents it here so the implementer
  matches this exact behavior.)
- A `RecordSchema` for tests is any object with a `parse_row(raw: dict) ->
  T` method (per the `Protocol` in `flat_file_parser.py`) — see
  `_DeviceReadingSchema` below.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pytest

from boogie_sdk.core.errors import ValidationError
from boogie_sdk.deviceio.flat_file_parser import FlatFileParser


@dataclass(frozen=True)
class DeviceReading:
    device_id: str
    value: float


class _DeviceReadingSchema:
    """Minimal RecordSchema implementation used across these tests."""

    def parse_row(self, raw: dict[str, str]) -> DeviceReading:
        return DeviceReading(device_id=raw["device_id"], value=float(raw["value"]))


@pytest.fixture
def parser() -> FlatFileParser:
    return FlatFileParser()


def _write_csv(tmp_path: Path, text: str) -> Path:
    file = tmp_path / "readings.csv"
    file.write_text(text)
    return file


# -- happy path -------------------------------------------------------------


def test_parse_returns_typed_records_for_each_data_row(
    parser: FlatFileParser, tmp_path: Path
) -> None:
    file = _write_csv(
        tmp_path,
        "device_id,value\n"
        "dev-1,12.5\n"
        "dev-2,7.0\n",
    )

    records = parser.parse(file, _DeviceReadingSchema())

    assert records == [
        DeviceReading(device_id="dev-1", value=12.5),
        DeviceReading(device_id="dev-2", value=7.0),
    ]


def test_parse_preserves_row_order(parser: FlatFileParser, tmp_path: Path) -> None:
    file = _write_csv(
        tmp_path,
        "device_id,value\n"
        "z,1\n"
        "a,2\n"
        "m,3\n",
    )

    records = parser.parse(file, _DeviceReadingSchema())

    assert [r.device_id for r in records] == ["z", "a", "m"]


def test_parse_header_only_file_returns_empty_list(
    parser: FlatFileParser, tmp_path: Path
) -> None:
    file = _write_csv(tmp_path, "device_id,value\n")

    records = parser.parse(file, _DeviceReadingSchema())

    assert records == []


def test_parse_passes_raw_dict_keyed_by_header_to_schema(
    parser: FlatFileParser, tmp_path: Path
) -> None:
    file = _write_csv(tmp_path, "device_id,value\ndev-9,3.5\n")

    seen_rows: list[dict[str, str]] = []

    class RecordingSchema:
        def parse_row(self, raw: dict[str, str]) -> None:
            seen_rows.append(dict(raw))

    parser.parse(file, RecordingSchema())

    assert seen_rows == [{"device_id": "dev-9", "value": "3.5"}]


# -- malformed rows -----------------------------------------------------------


def test_parse_raises_validation_error_on_malformed_row(
    parser: FlatFileParser, tmp_path: Path
) -> None:
    file = _write_csv(
        tmp_path,
        "device_id,value\n"
        "dev-1,12.5\n"
        "dev-2,not-a-number\n",
    )

    with pytest.raises(ValidationError):
        parser.parse(file, _DeviceReadingSchema())


def test_parse_stops_at_first_malformed_row_without_partial_results_leaking(
    parser: FlatFileParser, tmp_path: Path
) -> None:
    # Even though dev-1 parses fine before the bad row, a failed parse raises
    # rather than returning a partial list — the caller gets nothing back.
    file = _write_csv(
        tmp_path,
        "device_id,value\n"
        "dev-1,12.5\n"
        "dev-2,garbage\n",
    )

    with pytest.raises(ValidationError):
        parser.parse(file, _DeviceReadingSchema())
