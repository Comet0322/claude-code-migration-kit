from __future__ import annotations

import csv
import json
from pathlib import Path

from harness.driver import DriverResult
from harness.state import RunState


def load_test_config(fixture_name: str, fixtures_root: Path) -> dict:
    path = fixtures_root / fixture_name / "test-config.json"
    return json.loads(path.read_text(encoding="utf-8"))


def _read_domain_skill_file(state: RunState) -> str | None:
    path = state.run_dir / "migration" / "domain-skill.txt"
    if not path.exists():
        return None
    return path.read_text(encoding="utf-8").strip()


def build_eval_report(
    fixture_name: str, mode: str, result: DriverResult, state: RunState, test_config: dict
) -> str:
    expected_outcome = test_config.get("expected_outcome", "success")
    expected_domain_skill = test_config.get("expected_domain_skill")
    actual_domain_skill = _read_domain_skill_file(state)
    expected_units = test_config.get("expected_units", {})

    lines = [
        f"# Eval report: {fixture_name} ({mode})",
        "",
        f"- outcome: {result.outcome.value} (expected: {expected_outcome}, "
        f"{'MATCH' if result.outcome.value == expected_outcome else 'MISMATCH'})",
        f"- reason: {result.last_reason}",
        f"- turns_used: {result.turns_used}",
        "",
        "## Domain skill",
        f"- expected: {expected_domain_skill}",
        f"- actual: {actual_domain_skill}",
        f"- {'MATCH' if actual_domain_skill == expected_domain_skill else 'MISMATCH (or ambiguity by design)'}",
        "",
        "## Units",
    ]
    for unit_id, expected_status in expected_units.items():
        actual = state.unit_states.get(unit_id)
        actual_status = actual.status if actual else "(missing)"
        verdict = "MATCH" if actual_status == expected_status else "MISMATCH"
        lines.append(f"- {unit_id}: expected={expected_status} actual={actual_status} [{verdict}]")

    lines += [
        "",
        "## Deviations",
        f"- total: {len(state.deviation_rows)}",
        f"- rulebook_amendments_pending: {state.rulebook_amendments_pending}",
    ]
    return "\n".join(lines) + "\n"


_HISTORY_FIELDS = [
    "timestamp",
    "fixture",
    "mode",
    "outcome",
    "domain_skill_match",
    "units_pass",
    "units_total",
]


def append_history(
    history_path: Path, fixture_name: str, mode: str, result: DriverResult, state: RunState, test_config: dict
) -> None:
    from datetime import datetime, timezone

    expected_domain_skill = test_config.get("expected_domain_skill")
    actual_domain_skill = _read_domain_skill_file(state)
    expected_units = test_config.get("expected_units", {})
    units_pass = sum(
        1
        for unit_id, expected_status in expected_units.items()
        if state.unit_states.get(unit_id) and state.unit_states[unit_id].status == expected_status
    )

    row = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "fixture": fixture_name,
        "mode": mode,
        "outcome": result.outcome.value,
        "domain_skill_match": str(actual_domain_skill == expected_domain_skill),
        "units_pass": str(units_pass),
        "units_total": str(len(expected_units)),
    }

    is_new = not history_path.exists()
    with history_path.open("a", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=_HISTORY_FIELDS, delimiter="\t")
        if is_new:
            writer.writeheader()
        writer.writerow(row)
