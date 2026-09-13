"""Minimal real implementation of corplib.db for migration-kit testing.

Backed by SQLite instead of the real MS SQL Server the domain skills
describe — enough to make generated code actually import, run, and be
tested against. Not a description of production behavior.
"""
from __future__ import annotations

import os
import sqlite3
from contextlib import contextmanager
from typing import Iterator, Optional


class _Cursor:
    def __init__(self, conn: sqlite3.Connection):
        self._conn = conn

    def fetch_all(self, sql: str, params: Optional[dict] = None) -> list[dict]:
        cur = self._conn.execute(sql, params or {})
        cols = [d[0] for d in cur.description] if cur.description else []
        return [dict(zip(cols, row)) for row in cur.fetchall()]

    def fetch_one(self, sql: str, params: Optional[dict] = None) -> Optional[dict]:
        rows = self.fetch_all(sql, params)
        return rows[0] if rows else None

    def execute(self, sql: str, params: Optional[dict] = None) -> None:
        self._conn.execute(sql, params or {})


class Database:
    """`:name` placeholders map straight onto sqlite3's own named-parameter
    syntax, so `conn.fetch_all(sql, {"id": 1})` works unmodified."""

    def __init__(self, dsn: str):
        self._dsn = dsn

    @classmethod
    def from_env(cls) -> "Database":
        return cls(os.environ.get("CORPLIB_DB_DSN", "corplib.sqlite3"))

    @contextmanager
    def session(self) -> Iterator[_Cursor]:
        conn = sqlite3.connect(self._dsn)
        try:
            cur = _Cursor(conn)
            yield cur
            conn.commit()
        finally:
            conn.close()

    @contextmanager
    def transaction(self) -> Iterator[_Cursor]:
        conn = sqlite3.connect(self._dsn)
        cur = _Cursor(conn)
        try:
            yield cur
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
