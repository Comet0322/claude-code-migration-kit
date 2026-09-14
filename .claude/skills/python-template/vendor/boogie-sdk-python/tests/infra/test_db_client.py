"""Tests for DbClient. See boogie-sdk-api.md (this skill's library doc) section 5.2.

Convention pinned down by this test file (none exists yet beyond the public
method shapes): `DbClient` is expected to be backed by Python's stdlib
`sqlite3` against an in-memory database (`sqlite3.connect(":memory:")`).
This gives real SQL semantics for free (CREATE TABLE / INSERT / SELECT ...
WHERE, parameterized queries) rather than a hand-rolled fake, which is a
better training template. Consequences tests rely on:

- `query(sql, params)` returns `list[dict]` rows (column name -> value).
- `execute(sql, params)` returns the affected row count (sqlite3's
  `cursor.rowcount` semantics for INSERT/UPDATE/DELETE).
- `transaction(work)` calls `work(session)` where `session` exposes the same
  `query`/`execute` shape; the whole unit of work commits if `work` returns
  normally and rolls back if `work` raises — both paths are tested.
- Each `DbClient()` instance owns its own isolated in-memory database (no
  cross-instance state), which is what lets these tests run without any
  setup/teardown fixtures beyond a fresh client per test.
"""

from __future__ import annotations

import pytest

from boogie_sdk.infra.db_client import DbClient, DbSession


@pytest.fixture
def client() -> DbClient:
    db = DbClient()
    db.execute("CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT, age INTEGER)")
    return db


# -- execute ------------------------------------------------------------------


def test_execute_create_table_does_not_raise() -> None:
    db = DbClient()
    db.execute("CREATE TABLE t (id INTEGER PRIMARY KEY)")


def test_execute_insert_returns_affected_row_count(client: DbClient) -> None:
    affected = client.execute(
        "INSERT INTO users (id, name, age) VALUES (:id, :name, :age)",
        {"id": 1, "name": "Alice", "age": 30},
    )
    assert affected == 1


def test_execute_update_returns_affected_row_count(client: DbClient) -> None:
    client.execute(
        "INSERT INTO users (id, name, age) VALUES (:id, :name, :age)",
        {"id": 1, "name": "Alice", "age": 30},
    )
    client.execute(
        "INSERT INTO users (id, name, age) VALUES (:id, :name, :age)",
        {"id": 2, "name": "Alice", "age": 40},
    )

    affected = client.execute(
        "UPDATE users SET age = :age WHERE name = :name",
        {"age": 99, "name": "Alice"},
    )
    assert affected == 2


def test_execute_delete_returns_affected_row_count(client: DbClient) -> None:
    client.execute(
        "INSERT INTO users (id, name, age) VALUES (:id, :name, :age)",
        {"id": 1, "name": "Bob", "age": 25},
    )

    affected = client.execute("DELETE FROM users WHERE id = :id", {"id": 1})
    assert affected == 1


# -- query ----------------------------------------------------------------


def test_query_returns_list_of_dict_rows(client: DbClient) -> None:
    client.execute(
        "INSERT INTO users (id, name, age) VALUES (:id, :name, :age)",
        {"id": 1, "name": "Carol", "age": 22},
    )

    rows = client.query("SELECT id, name, age FROM users WHERE id = :id", {"id": 1})

    assert isinstance(rows, list)
    assert len(rows) == 1
    assert isinstance(rows[0], dict)
    assert rows[0]["name"] == "Carol"
    assert rows[0]["age"] == 22


def test_query_with_no_matching_rows_returns_empty_list(client: DbClient) -> None:
    rows = client.query("SELECT * FROM users WHERE id = :id", {"id": 999})
    assert rows == []


def test_query_without_params(client: DbClient) -> None:
    client.execute(
        "INSERT INTO users (id, name, age) VALUES (:id, :name, :age)",
        {"id": 1, "name": "Dave", "age": 50},
    )
    client.execute(
        "INSERT INTO users (id, name, age) VALUES (:id, :name, :age)",
        {"id": 2, "name": "Eve", "age": 51},
    )

    rows = client.query("SELECT * FROM users ORDER BY id")
    assert len(rows) == 2


# -- transaction: commit path ---------------------------------------------


def test_transaction_commits_on_normal_return(client: DbClient) -> None:
    def work(session: DbSession) -> str:
        session.execute(
            "INSERT INTO users (id, name, age) VALUES (:id, :name, :age)",
            {"id": 1, "name": "Frank", "age": 33},
        )
        return "done"

    result = client.transaction(work)

    assert result == "done"
    rows = client.query("SELECT * FROM users WHERE id = :id", {"id": 1})
    assert len(rows) == 1
    assert rows[0]["name"] == "Frank"


def test_transaction_return_value_is_propagated(client: DbClient) -> None:
    def work(session: DbSession) -> int:
        return 42

    assert client.transaction(work) == 42


# -- transaction: rollback path ---------------------------------------------


def test_transaction_rolls_back_on_exception(client: DbClient) -> None:
    class BoomError(Exception):
        pass

    def work(session: DbSession) -> None:
        session.execute(
            "INSERT INTO users (id, name, age) VALUES (:id, :name, :age)",
            {"id": 2, "name": "Grace", "age": 44},
        )
        raise BoomError("something went wrong mid-transaction")

    with pytest.raises(BoomError):
        client.transaction(work)

    rows = client.query("SELECT * FROM users WHERE id = :id", {"id": 2})
    assert rows == []


def test_transaction_rollback_does_not_affect_prior_committed_data(
    client: DbClient,
) -> None:
    client.execute(
        "INSERT INTO users (id, name, age) VALUES (:id, :name, :age)",
        {"id": 1, "name": "Henry", "age": 60},
    )

    class BoomError(Exception):
        pass

    def work(session: DbSession) -> None:
        session.execute(
            "INSERT INTO users (id, name, age) VALUES (:id, :name, :age)",
            {"id": 2, "name": "Ivy", "age": 61},
        )
        raise BoomError

    with pytest.raises(BoomError):
        client.transaction(work)

    rows = client.query("SELECT * FROM users ORDER BY id")
    assert [r["id"] for r in rows] == [1]


def test_transaction_session_query_sees_uncommitted_writes_within_same_transaction(
    client: DbClient,
) -> None:
    def work(session: DbSession) -> list:
        session.execute(
            "INSERT INTO users (id, name, age) VALUES (:id, :name, :age)",
            {"id": 5, "name": "Jack", "age": 19},
        )
        return session.query("SELECT * FROM users WHERE id = :id", {"id": 5})

    rows = client.transaction(work)
    assert len(rows) == 1
    assert rows[0]["name"] == "Jack"


# -- isolation between DbClient instances -----------------------------------


def test_separate_db_client_instances_are_isolated() -> None:
    db_a = DbClient()
    db_b = DbClient()
    db_a.execute("CREATE TABLE t (id INTEGER PRIMARY KEY)")

    # db_b never had the table created — querying it should fail rather
    # than silently see db_a's schema/data.
    with pytest.raises(Exception):
        db_b.query("SELECT * FROM t")
