from __future__ import annotations

import argparse
from pathlib import Path

from harness.driver import DriverConfig, run_loop
from harness.evaluate import append_history, apply_variant, build_eval_report, load_test_config
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
    parser.add_argument(
        "--variant",
        default=None,
        help=(
            "test-config.json 的 variants 底下的一個 key，強制指定要選的"
            " domain skill 做迴歸測試（只能搭配 --mode e2e——convert-only"
            " 本來就跳過 domain-skill 選定，這個參數沒有意義）"
        ),
    )
    parser.add_argument("--fixtures-root", default="fixtures")
    parser.add_argument("--templates-root", default=".claude/skills/migration/templates")
    parser.add_argument("--runs-root", default="runs")
    parser.add_argument("--history-path", default="harness/history.tsv")
    parser.add_argument("--max-turns", type=int, default=20)
    parser.add_argument("--max-wallclock-seconds", type=int, default=3600)
    parser.add_argument("--per-call-timeout-seconds", type=int, default=1800)
    args = parser.parse_args(argv)

    if args.variant and args.mode != "e2e":
        raise SystemExit("--variant 只能搭配 --mode e2e")

    fixtures_root = Path(args.fixtures_root)
    templates_root = Path(args.templates_root)
    runs_root = Path(args.runs_root)
    # harness/run.py 本身在 repo 根目錄底下的 harness/ 子資料夾——不再靠
    # templates_root 的上層目錄反推 repo_root（templates/ 移進
    # .claude/skills/migration/ 之後，templates_root 已經不是 repo 根目
    # 錄的直接子目錄，反推會算錯），改成從這支腳本自己的路徑算。
    repo_root = Path(__file__).resolve().parent.parent

    test_config = load_test_config(args.fixture, fixtures_root)
    test_config, force_domain_skill = apply_variant(test_config, args.variant)
    # 純粹是給 run 目錄命名/eval-report/history.tsv 用的標籤，實際讀
    # fixtures/ 底下的資料夾一律用 args.fixture 本名——variant 不是另一份
    # fixture，只是同一份來源用不同方式跑。
    fixture_label = f"{args.fixture}--{args.variant}" if args.variant else args.fixture

    run_dir = create_run_dir(fixture_label, args.mode, runs_root)
    if args.mode == "e2e":
        provision_e2e(args.fixture, run_dir, fixtures_root, repo_root, templates_root, force_domain_skill)
    else:
        provision_convert_only(args.fixture, run_dir, fixtures_root, repo_root, templates_root)

    config = DriverConfig(
        max_turns=args.max_turns,
        max_wallclock_seconds=args.max_wallclock_seconds,
        per_call_timeout_seconds=args.per_call_timeout_seconds,
    )
    result = run_loop(run_dir, args.mode, config)

    state = read_run_state(run_dir)
    report = build_eval_report(fixture_label, args.mode, result, state, test_config)
    (run_dir / "eval-report.md").write_text(report, encoding="utf-8")
    append_history(Path(args.history_path), fixture_label, args.mode, result, state, test_config, repo_root)

    print(report)
    return _EXIT_CODES[result.outcome]


if __name__ == "__main__":
    raise SystemExit(main())
