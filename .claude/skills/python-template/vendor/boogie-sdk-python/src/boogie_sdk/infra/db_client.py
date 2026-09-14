"""DbClient stub. See boogie-sdk-api.md (this skill's library doc) section 5.2 (infra).

Backed by `sqlite3.connect(":memory:")` per instance (see
tests/infra/test_db_client.py module docstring for the
pinned-down convention). Uses sqlite3's autocommit mode with explicit
BEGIN/COMMIT/ROLLBACK for `transaction`.
"""

from __future__ import annotations

import sqlite3
from typing import Any, Callable, TypeVar

Row = dict[str, Any]
T = TypeVar("T")


def _row_to_dict(row: sqlite3.Row) -> Row:
    return dict(row)


class DbSession:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection

    def query(self, sql: str, params: dict[str, Any] | None = None) -> list[Row]:
        cursor = self._connection.execute(sql, params or {})
        return [_row_to_dict(row) for row in cursor.fetchall()]

    def execute(self, sql: str, params: dict[str, Any] | None = None) -> int:
        cursor = self._connection.execute(sql, params or {})
        return cursor.rowcount


class DbClient:
    def __init__(self) -> None:
        # isolation_level=None -> sqlite3 autocommit mode; `transaction`
        # takes manual control via explicit BEGIN/COMMIT/ROLLBACK.
        self._connection = sqlite3.connect(":memory:", isolation_level=None)
        self._connection.row_factory = sqlite3.Row
        self._session = DbSession(self._connection)

    def query(self, sql: str, params: dict[str, Any] | None = None) -> list[Row]:
        return self._session.query(sql, params)

    def execute(self, sql: str, params: dict[str, Any] | None = None) -> int:
        return self._session.execute(sql, params)

    def transaction(self, work: Callable[[DbSession], T]) -> T:
        self._connection.execute("BEGIN")
        try:
            result = work(self._session)
        except Exception:
            self._connection.execute("ROLLBACK")
            raise
        else:
            self._connection.execute("COMMIT")
            return result
