"""Tests for FilePollingClient. See boogie-sdk-api.md (this skill's library doc)
section 5.3 (deviceio).

`poll_once(directory, pattern)` is a straightforward, real one-shot glob
(`Path.glob(pattern)`) against a real directory — no fakery needed, so it is
tested with real files under `tmp_path`.

`watch(directory, pattern, handler)` convention (invented here, since a real
implementation would poll on an interval and that isn't deterministically
testable): **`watch()` performs exactly one synchronous poll pass at call
time** — it is not a background thread or loop. It calls `handler(path)`
exactly once per currently-matching file (as of that single poll), then
returns. This makes it behave, for a single call, like `poll_once` plus a
callback per match — fully deterministic and synchronous for tests.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from boogie_sdk.deviceio.file_polling_client import FilePollingClient


@pytest.fixture
def client() -> FilePollingClient:
    return FilePollingClient()


# -- poll_once ------------------------------------------------------------


def test_poll_once_finds_matching_files(client: FilePollingClient, tmp_path: Path) -> None:
    (tmp_path / "a.csv").write_text("1,2,3")
    (tmp_path / "b.csv").write_text("4,5,6")
    (tmp_path / "c.txt").write_text("ignore me")

    matches = client.poll_once(tmp_path, "*.csv")

    assert sorted(p.name for p in matches) == ["a.csv", "b.csv"]


def test_poll_once_returns_empty_list_when_no_matches(
    client: FilePollingClient, tmp_path: Path
) -> None:
    (tmp_path / "readme.md").write_text("nothing here")

    matches = client.poll_once(tmp_path, "*.csv")

    assert matches == []


def test_poll_once_returns_paths_pointing_into_directory(
    client: FilePollingClient, tmp_path: Path
) -> None:
    target = tmp_path / "data.csv"
    target.write_text("x")

    matches = client.poll_once(tmp_path, "*.csv")

    assert len(matches) == 1
    assert matches[0].resolve() == target.resolve()


def test_poll_once_does_not_recurse_into_subdirectories(
    client: FilePollingClient, tmp_path: Path
) -> None:
    (tmp_path / "top.csv").write_text("x")
    sub = tmp_path / "sub"
    sub.mkdir()
    (sub / "nested.csv").write_text("y")

    matches = client.poll_once(tmp_path, "*.csv")

    assert [p.name for p in matches] == ["top.csv"]


# -- watch (one-shot synchronous poll convention) --------------------------


def test_watch_calls_handler_once_per_matching_file(
    client: FilePollingClient, tmp_path: Path
) -> None:
    (tmp_path / "a.csv").write_text("1")
    (tmp_path / "b.csv").write_text("2")

    seen: list[Path] = []
    client.watch(tmp_path, "*.csv", seen.append)

    assert sorted(p.name for p in seen) == ["a.csv", "b.csv"]


def test_watch_does_not_call_handler_for_non_matching_files(
    client: FilePollingClient, tmp_path: Path
) -> None:
    (tmp_path / "a.csv").write_text("1")
    (tmp_path / "skip.txt").write_text("2")

    seen: list[Path] = []
    client.watch(tmp_path, "*.csv", seen.append)

    assert [p.name for p in seen] == ["a.csv"]


def test_watch_with_no_matches_never_calls_handler(
    client: FilePollingClient, tmp_path: Path
) -> None:
    calls = []
    client.watch(tmp_path, "*.csv", calls.append)

    assert calls == []


def test_watch_returns_after_single_pass_and_does_not_block(
    client: FilePollingClient, tmp_path: Path
) -> None:
    # Documents the deterministic "one poll pass, then return" convention:
    # calling watch() twice in a row (as if driving it manually) sees the
    # same file both times rather than hanging or requiring a stop signal.
    (tmp_path / "a.csv").write_text("1")

    first_seen: list[Path] = []
    second_seen: list[Path] = []
    client.watch(tmp_path, "*.csv", first_seen.append)
    client.watch(tmp_path, "*.csv", second_seen.append)

    assert len(first_seen) == 1
    assert len(second_seen) == 1
