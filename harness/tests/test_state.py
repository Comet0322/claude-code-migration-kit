import json
from pathlib import Path
from harness.state import read_run_state


def test_empty_run_dir_has_empty_manifest_and_no_flags(tmp_path: Path):
    run_dir = tmp_path / "run"
    (run_dir / "migration").mkdir(parents=True)

    state = read_run_state(run_dir)

    assert state.manifest_rows == []
    assert state.pilot_manifest_exists is False
    assert state.pilot_signoff_exists is False
    assert state.unit_states == {}
    assert state.integration_status is None
    assert state.deviation_rows == []
    assert state.rulebook_amendments_pending is False
    assert state.decision_log_last_status is None
    assert state.ground_truth_tier is None


def test_populated_run_dir_parses_all_files(tmp_path: Path):
    run_dir = tmp_path / "run"
    migration_dir = run_dir / "migration"
    state_dir = migration_dir / "state"
    state_dir.mkdir(parents=True)

    (migration_dir / "manifest.tsv").write_text(
        "UserSync\tlegacy/UserSync.bas\ttarget/user_sync.py\n",
        encoding="utf-8",
    )
    (migration_dir / "pilot-manifest.tsv").write_text("", encoding="utf-8")
    (migration_dir / "pilot-signoff.txt").write_text("ok\n", encoding="utf-8")
    (state_dir / "UserSync.json").write_text(
        json.dumps({"status": "pass", "attempts": {"test_writer": 1}, "last_note": ""}),
        encoding="utf-8",
    )
    (state_dir / "_integration.json").write_text(
        json.dumps({"status": "pass", "note": "ok"}), encoding="utf-8"
    )
    (migration_dir / "deviation-log.tsv").write_text(
        "2026-09-13T00:00:00Z\tUserSync\tnaming\tfoo\n", encoding="utf-8"
    )
    (migration_dir / "rulebook-amendments.md").write_text("- pending item\n", encoding="utf-8")
    (migration_dir / "decision-log.md").write_text(
        "## 1. domain skill 選定\n\nrecommend X\n\nSTATUS: decided\n", encoding="utf-8"
    )
    (migration_dir / "ground-truth-strategy.md").write_text(
        "tier: inference\nno environment available\n", encoding="utf-8"
    )

    state = read_run_state(run_dir)

    assert state.manifest_rows == [
        {"unit_id": "UserSync", "source_path": "legacy/UserSync.bas", "target_path": "target/user_sync.py"}
    ]
    assert state.pilot_manifest_exists is True
    assert state.pilot_signoff_exists is True
    assert state.unit_states["UserSync"].status == "pass"
    assert state.integration_status == "pass"
    assert state.deviation_rows[0]["category"] == "naming"
    assert state.rulebook_amendments_pending is True
    assert state.decision_log_last_status == "decided"
    assert state.ground_truth_tier == "inference"
