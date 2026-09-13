import json
from pathlib import Path

import pytest

from harness.evaluate import (
    apply_variant,
    compute_prompt_version,
    load_test_config,
    build_eval_report,
    append_history,
)
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


def test_apply_variant_none_returns_config_unchanged():
    test_config = {"expected_outcome": "needs-human"}

    effective, force_domain_skill = apply_variant(test_config, None)

    assert effective == test_config
    assert force_domain_skill is None


def test_apply_variant_merges_named_variant_and_extracts_force_domain_skill():
    test_config = {
        "expected_outcome": "needs-human",
        "expected_domain_skill": None,
        "variants": {
            "force-java": {
                "force_domain_skill": "domain-200-delphi-java",
                "expected_outcome": "success",
                "expected_domain_skill": "domain-200-delphi-java",
            }
        },
    }

    effective, force_domain_skill = apply_variant(test_config, "force-java")

    assert effective["expected_outcome"] == "success"
    assert effective["expected_domain_skill"] == "domain-200-delphi-java"
    assert "variants" not in effective
    assert force_domain_skill == "domain-200-delphi-java"


def test_apply_variant_unknown_name_raises():
    with pytest.raises(KeyError):
        apply_variant({"variants": {"force-java": {}}}, "does-not-exist")


def test_build_eval_report_flags_mismatch(tmp_path: Path):
    state = RunState(
        run_dir=tmp_path,
        unit_states={"UserSync": UnitState("UserSync", "pass", {}, "")},
        domain_skill="domain-200-vb-java",
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
    assert lines[0].startswith("timestamp\tprompt_version\t")
    assert len(lines) == 3


def test_append_history_without_repo_root_leaves_prompt_version_blank(tmp_path: Path):
    state = RunState(run_dir=tmp_path, unit_states={})
    result = DriverResult(Outcome.SUCCESS, 1, "ok", "")
    history_path = tmp_path / "history.tsv"

    append_history(history_path, "dept200-vb6", "e2e", result, state, {})

    header, row = history_path.read_text(encoding="utf-8").splitlines()
    fields = dict(zip(header.split("\t"), row.split("\t")))
    assert fields["prompt_version"] == ""


def test_append_history_with_repo_root_fills_prompt_version(tmp_path: Path):
    repo_root = tmp_path / "repo"
    (repo_root / ".claude" / "skills" / "migration").mkdir(parents=True)
    (repo_root / ".claude" / "skills" / "migration" / "SKILL.md").write_text("hello", encoding="utf-8")
    state = RunState(run_dir=tmp_path, unit_states={})
    result = DriverResult(Outcome.SUCCESS, 1, "ok", "")
    history_path = tmp_path / "history.tsv"

    append_history(history_path, "dept200-vb6", "e2e", result, state, {}, repo_root)

    header, row = history_path.read_text(encoding="utf-8").splitlines()
    fields = dict(zip(header.split("\t"), row.split("\t")))
    assert fields["prompt_version"] == compute_prompt_version(repo_root)
    assert len(fields["prompt_version"]) == 12


def test_compute_prompt_version_changes_when_a_skill_file_changes(tmp_path: Path):
    skill_path = tmp_path / ".claude" / "skills" / "migration"
    skill_path.mkdir(parents=True)
    (skill_path / "SKILL.md").write_text("version one", encoding="utf-8")

    before = compute_prompt_version(tmp_path)
    (skill_path / "SKILL.md").write_text("version two", encoding="utf-8")
    after = compute_prompt_version(tmp_path)

    assert before != after


def test_compute_prompt_version_ignores_files_outside_claude(tmp_path: Path):
    skill_path = tmp_path / ".claude" / "skills" / "migration"
    skill_path.mkdir(parents=True)
    (skill_path / "SKILL.md").write_text("content", encoding="utf-8")
    before = compute_prompt_version(tmp_path)

    (tmp_path / "harness").mkdir()
    (tmp_path / "harness" / "unrelated.py").write_text("print(1)", encoding="utf-8")
    after = compute_prompt_version(tmp_path)

    assert before == after
