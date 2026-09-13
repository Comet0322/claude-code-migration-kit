import json
from pathlib import Path

from harness.evaluate import load_test_config, build_eval_report, append_history
from harness.driver import DriverResult
from harness.gates import Outcome
from harness.state import RunState, UnitState


def test_load_test_config_reads_json(tmp_path: Path):
    fixtures_root = tmp_path / "fixtures"
    fixture_dir = fixtures_root / "dept200-vb6"
    fixture_dir.mkdir(parents=True)
    (fixture_dir / "test-config.json").write_text(
        json.dumps({"expected_outcome": "success", "expected_domain_skill": "domain-200-vb-java"}),
        encoding="utf-8",
    )

    config = load_test_config("dept200-vb6", fixtures_root)

    assert config["expected_outcome"] == "success"
    assert config["expected_domain_skill"] == "domain-200-vb-java"


def test_build_eval_report_flags_mismatch(tmp_path: Path):
    (tmp_path / "migration").mkdir()
    (tmp_path / "migration" / "domain-skill.txt").write_text("domain-200-vb-java\n", encoding="utf-8")
    state = RunState(
        run_dir=tmp_path,
        unit_states={"UserSync": UnitState("UserSync", "pass", {}, "")},
    )
    result = DriverResult(Outcome.SUCCESS, 3, "ok", "")
    test_config = {
        "expected_outcome": "success",
        "expected_domain_skill": "domain-200-vb-java",
        "expected_units": {"UserSync": "pass"},
    }

    report = build_eval_report("dept200-vb6", "e2e", result, state, test_config)

    assert "MATCH" in report
    assert "domain-200-vb-java" in report
    assert "UserSync: expected=pass actual=pass [MATCH]" in report


def test_append_history_writes_header_once(tmp_path: Path):
    (tmp_path / "migration").mkdir()
    state = RunState(run_dir=tmp_path, unit_states={"UserSync": UnitState("UserSync", "pass", {}, "")})
    result = DriverResult(Outcome.SUCCESS, 3, "ok", "")
    test_config = {"expected_domain_skill": None, "expected_units": {"UserSync": "pass"}}
    history_path = tmp_path / "history.tsv"

    append_history(history_path, "dept200-vb6", "e2e", result, state, test_config)
    append_history(history_path, "dept200-vb6", "e2e", result, state, test_config)

    lines = history_path.read_text(encoding="utf-8").splitlines()
    assert lines[0].startswith("timestamp\t")
    assert len(lines) == 3
