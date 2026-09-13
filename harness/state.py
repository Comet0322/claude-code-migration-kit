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
    pilot_unit_ids: list[str] = field(default_factory=list)
    pilot_signoff_exists: bool = False
    unit_states: dict[str, UnitState] = field(default_factory=dict)
    integration_status: str | None = None
    deviation_rows: list[dict[str, str]] = field(default_factory=list)
    rulebook_amendments_pending: bool = False
    decision_log_last_status: str | None = None
    domain_skill: str | None = None
    ground_truth_tier: str | None = None


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


def _read_tsv_with_header(path: Path) -> list[dict[str, str]]:
    # manifest.tsv's column set/order isn't fixed (migration-analyze's
    # unit_id/source_path/cycle_group/order_index/risk_flag/risk_reason,
    # plus target_path and pilot added later by migration-clarify) — read
    # the real header row instead of assuming a fixed column list/order.
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh, delimiter="\t")
        return list(reader)


def _read_unit_states(migration_dir: Path) -> dict[str, UnitState]:
    state_dir = migration_dir / "convert" / "state"
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
    path = migration_dir / "convert" / "state" / "_integration.json"
    if not path.exists():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    return data.get("status")


def _read_rulebook_amendments_pending(migration_dir: Path) -> bool:
    path = migration_dir / "convert" / "rulebook-amendments.md"
    if not path.exists():
        return False
    return path.read_text(encoding="utf-8").strip() != ""


_STATUS_LINE_RE = re.compile(r"^STATUS:\s*(decided|needs-human)\s*$", re.MULTILINE)


def _read_decision_log_last_status(migration_dir: Path) -> str | None:
    path = migration_dir / "clarify" / "decision-log.md"
    if not path.exists():
        return None
    matches = _STATUS_LINE_RE.findall(path.read_text(encoding="utf-8"))
    return matches[-1] if matches else None


_FRONTMATTER_RE = re.compile(r"\A---\n(.*?)\n---", re.DOTALL)


def _read_rulebook_frontmatter(migration_dir: Path) -> dict[str, str]:
    # domain_skill/ground_truth_tier/ground_truth_reason/target_shape/
    # parity_check all live as flat `key: value` lines in RULEBOOK.md's YAML
    # frontmatter (see migration-clarify) — no nested structures here, so a
    # tiny hand-rolled parser avoids pulling in a YAML dependency just for
    # this.
    path = migration_dir / "clarify" / "RULEBOOK.md"
    if not path.exists():
        return {}
    match = _FRONTMATTER_RE.match(path.read_text(encoding="utf-8"))
    if not match:
        return {}
    result: dict[str, str] = {}
    for line in match.group(1).splitlines():
        line = line.strip()
        if not line or ":" not in line:
            continue
        key, _, value = line.partition(":")
        result[key.strip()] = value.strip()
    return result


def _read_domain_skill(migration_dir: Path) -> str | None:
    return _read_rulebook_frontmatter(migration_dir).get("domain_skill") or None


def _read_ground_truth_tier(migration_dir: Path) -> str | None:
    tier = _read_rulebook_frontmatter(migration_dir).get("ground_truth_tier")
    return tier or None


def _pilot_unit_ids(manifest_rows: list[dict[str, str]]) -> list[str]:
    return [
        row["unit_id"]
        for row in manifest_rows
        if row.get("pilot", "").strip().lower() == "yes"
    ]


def read_run_state(run_dir: Path) -> RunState:
    migration_dir = run_dir / "migration"
    manifest_rows = _read_tsv_with_header(migration_dir / "clarify" / "manifest.tsv")
    return RunState(
        run_dir=run_dir,
        manifest_rows=manifest_rows,
        pilot_unit_ids=_pilot_unit_ids(manifest_rows),
        pilot_signoff_exists=(migration_dir / "convert" / "pilot-signoff.txt").exists(),
        unit_states=_read_unit_states(migration_dir),
        integration_status=_read_integration_status(migration_dir),
        # deviation-log.tsv 是純追加寫入的 log，每次只是 >> 加一行資料，
        # 從來沒有寫過標題列——這裡務必維持 skip_header=False，改成 True
        # 會靜默漏掉第一筆真實的 deviation 記錄。跟上面 manifest.tsv 的
        # skip_header=True 是刻意的不對稱，不是遺漏。
        deviation_rows=_read_tsv(migration_dir / "convert" / "deviation-log.tsv", _DEVIATION_FIELDS, skip_header=False),
        rulebook_amendments_pending=_read_rulebook_amendments_pending(migration_dir),
        decision_log_last_status=_read_decision_log_last_status(migration_dir),
        domain_skill=_read_domain_skill(migration_dir),
        ground_truth_tier=_read_ground_truth_tier(migration_dir),
    )
