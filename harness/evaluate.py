from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

from harness.driver import DriverResult
from harness.state import RunState


def load_test_config(fixture_name: str, fixtures_root: Path) -> dict:
    path = fixtures_root / fixture_name / "test-config.json"
    return json.loads(path.read_text(encoding="utf-8"))


def apply_variant(test_config: dict, variant_name: str | None) -> tuple[dict, str | None]:
    """Merge a named entry from test_config["variants"] over the base config.

    Lets one fixture whose fingerprint is deliberately ambiguous across
    multiple domain skills (e.g. dept200-delphi, which by design can't be
    auto-resolved between domain-200-delphi-java/-python) be regression
    tested both unforced (expect needs-human) and once per forced domain
    skill (expect success) — without duplicating the underlying source
    fixture. Returns (effective_test_config, force_domain_skill); the latter
    is what provisioning needs to write the `.headless-test-domain-skill`
    marker migration-clarify's headless-test protocol checks for.
    """
    if variant_name is None:
        return test_config, None
    variants = test_config.get("variants", {})
    if variant_name not in variants:
        raise KeyError(f"this fixture's test-config.json has no variant named {variant_name!r}")
    variant = variants[variant_name]
    effective = {**test_config, **variant}
    effective.pop("variants", None)
    return effective, variant.get("force_domain_skill")


_PROMPT_DIRS = (".claude/skills", ".claude/agents")


def compute_prompt_version(repo_root: Path) -> str:
    """Content hash of every file under .claude/skills + .claude/agents.

    Deliberately a hash of on-disk content, not a git commit — this loop is
    meant to be run while iterating on prompts locally (possibly with
    uncommitted edits), and what we actually want to correlate a harness
    result against is "which exact prompt text produced this," not "which
    commit happened to be checked out."
    """
    files: list[Path] = []
    for rel in _PROMPT_DIRS:
        base = repo_root / rel
        if base.exists():
            files.extend(p for p in base.rglob("*") if p.is_file())
    files.sort(key=lambda p: p.relative_to(repo_root).as_posix())

    hasher = hashlib.sha256()
    for path in files:
        hasher.update(path.relative_to(repo_root).as_posix().encode("utf-8"))
        hasher.update(b"\0")
        hasher.update(path.read_bytes())
    return hasher.hexdigest()[:12]


def build_eval_report(
    fixture_name: str, mode: str, result: DriverResult, state: RunState, test_config: dict
) -> str:
    expected_outcome = test_config.get("expected_outcome", "success")
    expected_domain_skill = test_config.get("expected_domain_skill")
    actual_domain_skill = state.domain_skill
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
    "prompt_version",
    "fixture",
    "mode",
    "outcome",
    "domain_skill_match",
    "units_pass",
    "units_total",
]


def append_history(
    history_path: Path,
    fixture_name: str,
    mode: str,
    result: DriverResult,
    state: RunState,
    test_config: dict,
    repo_root: Path | None = None,
) -> None:
    from datetime import datetime, timezone

    expected_domain_skill = test_config.get("expected_domain_skill")
    actual_domain_skill = state.domain_skill
    expected_units = test_config.get("expected_units", {})
    units_pass = sum(
        1
        for unit_id, expected_status in expected_units.items()
        if state.unit_states.get(unit_id) and state.unit_states[unit_id].status == expected_status
    )

    row = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        # repo_root omitted (e.g. a caller that hasn't been updated yet) ->
        # empty string, not a crash; a rollup just can't group that row by
        # version.
        "prompt_version": compute_prompt_version(repo_root) if repo_root is not None else "",
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
