from __future__ import annotations

import csv
import json
import re
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class UnitState:
    unit_id: str
    status: str
    attempts: dict[str, int]
    last_note: str


@dataclass
class RunState:
    run_dir: Path
    manifest_rows: list[dict[str, str]] = field(default_factory=list)
    pilot_manifest_exists: bool = False
    pilot_signoff_exists: bool = False
    unit_states: dict[str, UnitState] = field(default_factory=dict)
    integration_status: str | None = None
    deviation_rows: list[dict[str, str]] = field(default_factory=list)
    rulebook_amendments_pending: bool = False
    decision_log_last_status: str | None = None
    ground_truth_tier: str | None = None


_MANIFEST_FIELDS = ["unit_id", "source_path", "target_path"]
_DEVIATION_FIELDS = ["timestamp", "unit_id", "category", "detail"]


def _read_tsv(path: Path, fieldnames: list[str], skip_header: bool = False) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as fh:
        lines = fh.readlines()
    if skip_header and lines:
        lines = lines[1:]
    reader = csv.DictReader(lines, fieldnames=fieldnames, delimiter="\t")
    return list(reader)


def _read_unit_states(migration_dir: Path) -> dict[str, UnitState]:
    state_dir = migration_dir / "state"
    if not state_dir.exists():
        return {}
    result: dict[str, UnitState] = {}
    for path in state_dir.glob("*.json"):
        if path.stem == "_integration":
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        result[path.stem] = UnitState(
            unit_id=path.stem,
            status=data.get("status", "pending"),
            attempts=data.get("attempts", {}),
            last_note=data.get("last_note", ""),
        )
    return result


def _read_integration_status(migration_dir: Path) -> str | None:
    path = migration_dir / "state" / "_integration.json"
    if not path.exists():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    return data.get("status")


def _read_rulebook_amendments_pending(migration_dir: Path) -> bool:
    path = migration_dir / "rulebook-amendments.md"
    if not path.exists():
        return False
    return path.read_text(encoding="utf-8").strip() != ""


_STATUS_LINE_RE = re.compile(r"^STATUS:\s*(decided|needs-human)\s*$", re.MULTILINE)


def _read_decision_log_last_status(migration_dir: Path) -> str | None:
    path = migration_dir / "decision-log.md"
    if not path.exists():
        return None
    matches = _STATUS_LINE_RE.findall(path.read_text(encoding="utf-8"))
    return matches[-1] if matches else None


def _read_ground_truth_tier(migration_dir: Path) -> str | None:
    path = migration_dir / "ground-truth-strategy.md"
    if not path.exists():
        return None
    first_line = path.read_text(encoding="utf-8").splitlines()[0] if path.stat().st_size else ""
    match = re.match(r"^tier:\s*(environment|snapshot|inference)\s*$", first_line.strip())
    return match.group(1) if match else None


def read_run_state(run_dir: Path) -> RunState:
    migration_dir = run_dir / "migration"
    manifest_path = migration_dir / "manifest.tsv"
    return RunState(
        run_dir=run_dir,
        manifest_rows=_read_tsv(manifest_path, _MANIFEST_FIELDS, skip_header=True),
        pilot_manifest_exists=(migration_dir / "pilot-manifest.tsv").exists(),
        pilot_signoff_exists=(migration_dir / "pilot-signoff.txt").exists(),
        unit_states=_read_unit_states(migration_dir),
        integration_status=_read_integration_status(migration_dir),
        # deviation-log.tsv 是純追加寫入的 log，每次只是 >> 加一行資料，
        # 從來沒有寫過標題列——這裡務必維持 skip_header=False，改成 True
        # 會靜默漏掉第一筆真實的 deviation 記錄。跟上面 manifest.tsv 的
        # skip_header=True 是刻意的不對稱，不是遺漏。
        deviation_rows=_read_tsv(migration_dir / "deviation-log.tsv", _DEVIATION_FIELDS, skip_header=False),
        rulebook_amendments_pending=_read_rulebook_amendments_pending(migration_dir),
        decision_log_last_status=_read_decision_log_last_status(migration_dir),
        ground_truth_tier=_read_ground_truth_tier(migration_dir),
    )
