"""Download (Extract) stage of the ETL demo.

See boogie-sdk-api.md section 7 (migration cheat sheet). This is
where a legacy job would have hit its source system directly.

Unlike `process.py`/`upload.py` (which don't touch the database at all),
this stage is SQL-driven: the actual SQL statements live in the sibling
`sql/` directory as plain `.sql` files rather than being embedded as string
literals here, mirroring how a real migrated job would keep its SQL
maintainable/reviewable on its own instead of scattered through code. `main.py`
owns the database connection (`sdk.db`) and hands it to `download()` --
this module only ever touches the `DbClient` it's given, it never reaches
back into the wider `sdk` facade.
"""

from __future__ import annotations

from pathlib import Path

from boogie_sdk.infra.db_client import DbClient, DbSession, Row

SQL_DIR = Path(__file__).parent / "sql"

# "Sensor readings" seed data, standing in for whatever a legacy plant-floor
# batch job used to read out of its Access/SQL Server table every night.
# Row SENSOR-05 is deliberately bad data (a non-numeric reading) so the demo
# can show a single row failing without taking the whole batch down with it.
SEED_READINGS: list[dict[str, str]] = [
    {"device_id": "SENSOR-01", "contact_phone": "0912345678", "reading_value": "23.5", "recorded_at": "2026-09-14 01:15:00"},
    {"device_id": "SENSOR-02", "contact_phone": "0922334455", "reading_value": "24.1", "recorded_at": "2026-09-14 01:20:00"},
    {"device_id": "SENSOR-03", "contact_phone": "0933445566", "reading_value": "22.8", "recorded_at": "2026-09-14 01:30:00"},
    {"device_id": "SENSOR-04", "contact_phone": "0944556677", "reading_value": "23.9", "recorded_at": "2026-09-14 01:40:00"},
    {"device_id": "SENSOR-05", "contact_phone": "0955667788", "reading_value": "ERR", "recorded_at": "2026-09-14 01:45:00"},
    {"device_id": "SENSOR-06", "contact_phone": "0966778899", "reading_value": "23.2", "recorded_at": "2026-09-14 01:50:00"},
]


def _load_sql(name: str) -> str:
    return (SQL_DIR / name).read_text(encoding="utf-8")


def download(db: DbClient) -> list[Row]:
    """Extract stage.

    Cheat sheet: 直接組 SQL 字串操作 ADODB.Connection / TADOConnection ->
    `sdk.db.query(...)` / `execute(...)`.

    In a real migration the table would already exist in the target DB; here
    we create + seed it first so the example is runnable with zero setup.
    `db.transaction(...)` mirrors how a legacy job would wrap its own
    multi-row insert in a manual BEGIN/COMMIT to avoid partial writes.
    """
    db.execute(_load_sql("create_table.sql"))

    insert_sql = _load_sql("insert_reading.sql")

    def _seed(session: DbSession) -> None:
        for reading in SEED_READINGS:
            session.execute(insert_sql, reading)

    db.transaction(_seed)

    return db.query(_load_sql("select_all.sql"))
