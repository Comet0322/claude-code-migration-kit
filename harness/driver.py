from __future__ import annotations

import json
import subprocess
import time
from dataclasses import dataclass

from harness.gates import Outcome, evaluate_gate
from harness.state import read_run_state


@dataclass
class DriverConfig:
    max_turns: int = 20
    max_wallclock_seconds: int = 3600
    claude_bin: str = "claude"
    per_call_timeout_seconds: int = 900
    allowed_tools: str = "Bash,Edit,Write,Read,Glob,Grep,Skill,Task"


@dataclass
class DriverResult:
    outcome: Outcome
    turns_used: int
    last_reason: str
    last_stdout: str


_E2E_PROMPT = "用 migration skill 處理這次遷移。"
_CONVERT_ONLY_PROMPT = "呼叫 migration-convert，manifest 路徑帶 migration/manifest.tsv。"


def invoke_claude(run_dir, prompt: str, config: DriverConfig) -> str:
    cmd = [
        config.claude_bin,
        "-p",
        prompt,
        "--output-format",
        "json",
        "--permission-mode",
        "acceptEdits",
        "--allowedTools",
        config.allowed_tools,
    ]
    result = subprocess.run(
        cmd,
        cwd=run_dir,
        capture_output=True,
        text=True,
        timeout=config.per_call_timeout_seconds,
    )
    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError:
        return result.stdout
    return data.get("result", result.stdout)


def run_loop(run_dir, mode: str, config: DriverConfig = DriverConfig()) -> DriverResult:
    prompt = _E2E_PROMPT if mode == "e2e" else _CONVERT_ONLY_PROMPT
    start = time.monotonic()
    turns = 0
    last_stdout = ""

    while True:
        if turns >= config.max_turns:
            return DriverResult(Outcome.ERROR, turns, f"超過 max_turns={config.max_turns}", last_stdout)
        if time.monotonic() - start >= config.max_wallclock_seconds:
            return DriverResult(Outcome.ERROR, turns, "超過 max_wallclock_seconds", last_stdout)

        last_stdout = invoke_claude(run_dir, prompt, config)
        turns += 1

        state = read_run_state(run_dir)
        decision = evaluate_gate(state)

        if decision.write_pilot_signoff:
            (run_dir / "migration" / "pilot-signoff.txt").write_text(
                f"auto-approved by harness: {decision.reason}\n", encoding="utf-8"
            )

        if decision.outcome in (Outcome.SUCCESS, Outcome.NEEDS_HUMAN, Outcome.ERROR):
            return DriverResult(decision.outcome, turns, decision.reason, last_stdout)
        # Outcome.CONTINUE：進下一輪
