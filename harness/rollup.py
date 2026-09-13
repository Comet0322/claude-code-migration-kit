from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from pathlib import Path


def load_history(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh, delimiter="\t"))


def rollup_by_prompt_version(rows: list[dict[str, str]]) -> list[dict[str, object]]:
    """One row per prompt_version, aggregating every history.tsv run under it.

    This is the "did editing this SKILL.md/agent file actually help" view —
    compare the row for the version before an edit against the row after.
    """
    groups: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        groups[row.get("prompt_version", "")].append(row)

    result: list[dict[str, object]] = []
    for version, group_rows in groups.items():
        total = len(group_rows)
        successes = sum(1 for r in group_rows if r.get("outcome") == "success")
        domain_matches = sum(1 for r in group_rows if r.get("domain_skill_match") == "True")
        units_pass = sum(int(r.get("units_pass", 0) or 0) for r in group_rows)
        units_total = sum(int(r.get("units_total", 0) or 0) for r in group_rows)
        result.append(
            {
                "prompt_version": version,
                "runs": total,
                "success_rate": successes / total if total else 0.0,
                "domain_skill_match_rate": domain_matches / total if total else 0.0,
                "units_pass_rate": (units_pass / units_total) if units_total else None,
            }
        )
    result.sort(key=lambda r: r["prompt_version"])
    return result


def format_report(rollups: list[dict[str, object]]) -> str:
    lines = ["prompt_version\truns\tsuccess_rate\tdomain_skill_match_rate\tunits_pass_rate"]
    for r in rollups:
        units_pass_rate = r["units_pass_rate"]
        units_pass_str = f"{units_pass_rate:.2f}" if units_pass_rate is not None else "n/a"
        lines.append(
            f"{r['prompt_version']}\t{r['runs']}\t{r['success_rate']:.2f}\t"
            f"{r['domain_skill_match_rate']:.2f}\t{units_pass_str}"
        )
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="依 prompt_version 卷起 harness/history.tsv，比較不同 prompt 版本間的 pass rate"
    )
    parser.add_argument("--history-path", default="harness/history.tsv")
    args = parser.parse_args(argv)

    rows = load_history(Path(args.history_path))
    print(format_report(rollup_by_prompt_version(rows)), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
