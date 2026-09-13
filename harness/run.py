from __future__ import annotations

import argparse
from pathlib import Path

from harness.driver import DriverConfig, run_loop
from harness.evaluate import append_history, build_eval_report, load_test_config
from harness.gates import Outcome
from harness.provisioning import create_run_dir, provision_convert_only, provision_e2e
from harness.state import read_run_state

_EXIT_CODES = {
    Outcome.SUCCESS: 0,
    Outcome.NEEDS_HUMAN: 1,
    Outcome.ERROR: 2,
}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="遷移 kit 自動化測試框架")
    parser.add_argument("--fixture", required=True)
    parser.add_argument("--mode", choices=["e2e", "convert-only"], required=True)
    parser.add_argument("--fixtures-root", default="fixtures")
    parser.add_argument("--templates-root", default="templates")
    parser.add_argument("--runs-root", default="runs")
    parser.add_argument("--history-path", default="harness/history.tsv")
    parser.add_argument("--max-turns", type=int, default=20)
    parser.add_argument("--max-wallclock-seconds", type=int, default=3600)
    args = parser.parse_args(argv)

    fixtures_root = Path(args.fixtures_root)
    templates_root = Path(args.templates_root)
    runs_root = Path(args.runs_root)

    run_dir = create_run_dir(args.fixture, args.mode, runs_root)
    if args.mode == "e2e":
        provision_e2e(args.fixture, run_dir, fixtures_root, templates_root)
    else:
        provision_convert_only(args.fixture, run_dir, fixtures_root, templates_root)

    config = DriverConfig(max_turns=args.max_turns, max_wallclock_seconds=args.max_wallclock_seconds)
    result = run_loop(run_dir, args.mode, config)

    state = read_run_state(run_dir)
    test_config = load_test_config(args.fixture, fixtures_root)
    report = build_eval_report(args.fixture, args.mode, result, state, test_config)
    (run_dir / "eval-report.md").write_text(report, encoding="utf-8")
    append_history(Path(args.history_path), args.fixture, args.mode, result, state, test_config)

    print(report)
    return _EXIT_CODES[result.outcome]


if __name__ == "__main__":
    raise SystemExit(main())
