import json
from pathlib import Path
from harness.state import read_run_state


def test_empty_run_dir_has_empty_manifest_and_no_flags(tmp_path: Path):
    run_dir = tmp_path / "run"
    (run_dir / "migration").mkdir(parents=True)

    state = read_run_state(run_dir)

    assert state.manifest_rows == []
    assert state.pilot_unit_ids == []
    assert state.pilot_signoff_exists is False
    assert state.unit_states == {}
    assert state.integration_status is None
    assert state.deviation_rows == []
    assert state.rulebook_amendments_pending is False
    assert state.decision_log_last_status is None
    assert state.domain_skill is None
    assert state.ground_truth_tier is None


def test_populated_run_dir_parses_all_files(tmp_path: Path):
    run_dir = tmp_path / "run"
    migration_dir = run_dir / "migration"
    clarify_dir = migration_dir / "clarify"
    convert_dir = migration_dir / "convert"
    state_dir = convert_dir / "state"
    state_dir.mkdir(parents=True)
    clarify_dir.mkdir(parents=True)

    (clarify_dir / "manifest.tsv").write_text(
        "unit_id\tsource_path\ttarget_path\tpilot\n"
        "UserSync\tlegacy/UserSync.bas\ttarget/user_sync.py\tyes\n",
        encoding="utf-8",
    )
    (convert_dir / "pilot-signoff.txt").write_text("ok\n", encoding="utf-8")
    (state_dir / "UserSync.json").write_text(
        json.dumps({"status": "pass", "attempts": {"test_writer": 1}, "last_note": ""}),
        encoding="utf-8",
    )
    (state_dir / "_integration.json").write_text(
        json.dumps({"status": "pass", "note": "ok"}), encoding="utf-8"
    )
    (convert_dir / "deviation-log.tsv").write_text(
        "2026-09-13T00:00:00Z\tUserSync\tnaming\tfoo\n", encoding="utf-8"
    )
    (convert_dir / "rulebook-amendments.md").write_text("- pending item\n", encoding="utf-8")
    (clarify_dir / "decision-log.md").write_text(
        "## 1. domain skill 選定\n\nrecommend X\n\nSTATUS: decided\n", encoding="utf-8"
    )
    (clarify_dir / "RULEBOOK.md").write_text(
        "---\n"
        "domain_skill: domain-200-vb-java\n"
        "ground_truth_tier: inference\n"
        "ground_truth_reason: no environment available\n"
        "---\n\n"
        "# Rulebook\n",
        encoding="utf-8",
    )

    state = read_run_state(run_dir)

    assert state.manifest_rows == [
        {
            "unit_id": "UserSync",
            "source_path": "legacy/UserSync.bas",
            "target_path": "target/user_sync.py",
            "pilot": "yes",
        }
    ]
    assert state.pilot_unit_ids == ["UserSync"]
    assert state.pilot_signoff_exists is True
    assert state.unit_states["UserSync"].status == "pass"
    assert state.integration_status == "pass"
    assert state.deviation_rows[0]["category"] == "naming"
    assert state.rulebook_amendments_pending is True
    assert state.decision_log_last_status == "decided"
    assert state.domain_skill == "domain-200-vb-java"
    assert state.ground_truth_tier == "inference"
