"""FlatFileParser stub. See boogie-sdk-api.md (this skill's library doc) section 5.3 (deviceio).

Skeleton only — implemented during the Phase 1 TDD loop for the `deviceio` module.
"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any, Protocol, TypeVar

from boogie_sdk.core.errors import ValidationError

T = TypeVar("T")


class RecordSchema(Protocol[T]):
    def parse_row(self, raw: dict[str, Any]) -> T: ...


class FlatFileParser:
    def parse(self, file: Path, schema: RecordSchema[T]) -> list[T]:
        records: list[T] = []
        with Path(file).open(newline="") as f:
            reader = csv.DictReader(f)
            for raw in reader:
                try:
                    records.append(schema.parse_row(raw))
                except Exception as exc:
                    raise ValidationError(
                        f"Failed to parse row {raw!r}: {exc}"
                    ) from exc
        return records
