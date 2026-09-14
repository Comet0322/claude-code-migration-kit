"""Logger stub. See boogie-sdk-api.md (this skill's library doc) section 5.4 (observability).

Skeleton only — implemented during the Phase 1 TDD loop for the `observability` module.
"""

from __future__ import annotations

import json
import sys
from typing import Callable


class Logger:
    def __init__(self, sink: Callable[[dict], None] | None = None) -> None:
        self._sink = sink

    def info(self, msg: str, **fields: object) -> None:
        self._emit("info", msg, fields)

    def warn(self, msg: str, **fields: object) -> None:
        self._emit("warn", msg, fields)

    def error(
        self, msg: str, exc: BaseException | None = None, **fields: object
    ) -> None:
        record = self._build_record("error", msg, fields)
        record["exc"] = str(exc) if exc is not None else None
        self._dispatch(record)

    def _emit(self, level: str, msg: str, fields: dict) -> None:
        record = self._build_record(level, msg, fields)
        self._dispatch(record)

    @staticmethod
    def _build_record(level: str, msg: str, fields: dict) -> dict:
        record: dict = {"level": level, "msg": msg}
        record.update(fields)
        return record

    def _dispatch(self, record: dict) -> None:
        if self._sink is not None:
            self._sink(record)
            return
        try:
            line = json.dumps(record, default=str)
        except Exception:
            line = str(record)
        print(line, file=sys.stdout)
