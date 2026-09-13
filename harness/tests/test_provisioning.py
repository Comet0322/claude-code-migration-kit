import re
from pathlib import Path

from harness.provisioning import create_run_dir, provision_e2e, provision_convert_only


def test_create_run_dir_makes_timestamped_directory(tmp_path: Path):
    runs_root = tmp_path / "runs"

    run_dir = create_run_dir("dept200-vb6", "e2e", runs_root)

    assert run_dir.exists()
    assert run_dir.parent == runs_root
    assert re.match(r"^dept200-vb6-e2e-\d{8}T\d{6}Z$", run_dir.name)


def _make_fixture(fixtures_root: Path, name: str) -> Path:
    fixture_dir = fixtures_root / name
    (fixture_dir / "legacy").mkdir(parents=True)
    (fixture_dir / "legacy" / "UserSync.bas").write_text("' code\n", encoding="utf-8")
    return fixture_dir


def _make_templates(templates_root: Path) -> None:
    templates_root.mkdir(parents=True, exist_ok=True)
    (templates_root / "settings.json").write_text('{"permissions": {"deny": []}}', encoding="utf-8")


def test_provision_e2e_copies_legacy_seeds_settings_and_writes_marker(tmp_path: Path):
    fixtures_root = tmp_path / "fixtures"
    templates_root = tmp_path / "templates"
    _make_fixture(fixtures_root, "dept200-vb6")
    _make_templates(templates_root)
    run_dir = tmp_path / "runs" / "run1"
    run_dir.mkdir(parents=True)

    provision_e2e("dept200-vb6", run_dir, fixtures_root, templates_root)

    assert (run_dir / "legacy" / "UserSync.bas").exists()
    assert (run_dir / ".claude" / "settings.json").exists()
    assert (run_dir / "migration" / ".headless-test").exists()


def test_provision_convert_only_copies_golden_input_without_marker(tmp_path: Path):
    fixtures_root = tmp_path / "fixtures"
    templates_root = tmp_path / "templates"
    fixture_dir = _make_fixture(fixtures_root, "dept200-vb6")
    golden_dir = fixture_dir / "golden-convert-input"
    golden_dir.mkdir()
    (golden_dir / "manifest.tsv").write_text("UserSync\tlegacy/UserSync.bas\ttarget/user_sync.py\n", encoding="utf-8")
    (golden_dir / "RULEBOOK.md").write_text("# rules\n", encoding="utf-8")
    _make_templates(templates_root)
    run_dir = tmp_path / "runs" / "run2"
    run_dir.mkdir(parents=True)

    provision_convert_only("dept200-vb6", run_dir, fixtures_root, templates_root)

    assert (run_dir / "migration" / "manifest.tsv").exists()
    assert (run_dir / "migration" / "RULEBOOK.md").exists()
    assert not (run_dir / "migration" / ".headless-test").exists()
