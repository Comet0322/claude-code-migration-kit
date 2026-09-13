from __future__ import annotations

import shutil
from datetime import datetime, timezone
from pathlib import Path


def create_run_dir(fixture_name: str, mode: str, runs_root: Path) -> Path:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_dir = runs_root / f"{fixture_name}-{mode}-{timestamp}"
    run_dir.mkdir(parents=True, exist_ok=False)
    return run_dir


def _seed_settings(run_dir: Path, templates_root: Path) -> None:
    claude_dir = run_dir / ".claude"
    claude_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(templates_root / "settings.json", claude_dir / "settings.json")


def provision_e2e(fixture_name: str, run_dir: Path, fixtures_root: Path, templates_root: Path) -> None:
    fixture_dir = fixtures_root / fixture_name
    shutil.copytree(fixture_dir / "legacy", run_dir / "legacy")
    _seed_settings(run_dir, templates_root)
    migration_dir = run_dir / "migration"
    migration_dir.mkdir(parents=True, exist_ok=True)
    (migration_dir / ".headless-test").write_text("", encoding="utf-8")


def provision_convert_only(fixture_name: str, run_dir: Path, fixtures_root: Path, templates_root: Path) -> None:
    fixture_dir = fixtures_root / fixture_name
    shutil.copytree(fixture_dir / "legacy", run_dir / "legacy")
    _seed_settings(run_dir, templates_root)
    golden_dir = fixture_dir / "golden-convert-input"
    shutil.copytree(golden_dir, run_dir / "migration", dirs_exist_ok=True)
