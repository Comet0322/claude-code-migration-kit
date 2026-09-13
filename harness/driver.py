from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field

from claude_agent_sdk import ClaudeAgentOptions, ResultError, ResultMessage, query

from harness.gates import Outcome, evaluate_gate
from harness.state import read_run_state

_DEFAULT_ALLOWED_TOOLS = ["Bash", "Edit", "Write", "Read", "Glob", "Grep", "Skill", "Task"]


@dataclass
class DriverConfig:
    max_turns: int = 20
    max_wallclock_seconds: int = 3600
    per_call_timeout_seconds: int = 1800
    allowed_tools: list[str] = field(default_factory=lambda: list(_DEFAULT_ALLOWED_TOOLS))


@dataclass
class DriverResult:
    outcome: Outcome
    turns_used: int
    last_reason: str
    last_stdout: str


class DriverTimeoutError(Exception):
    """單次 Claude Agent SDK query() 呼叫超過 per_call_timeout_seconds。"""


_E2E_PROMPT = "用 migration skill 處理這次遷移。"
_CONVERT_ONLY_PROMPT = "呼叫 migration-convert，manifest 路徑帶 migration/manifest.tsv。"


async def _query_once(run_dir, prompt: str, config: DriverConfig) -> str:
    options = ClaudeAgentOptions(
        cwd=str(run_dir),
        permission_mode="acceptEdits",
        allowed_tools=list(config.allowed_tools),
    )
    last_result = ""
    try:
        async for message in query(prompt=prompt, options=options):
            if isinstance(message, ResultMessage):
                last_result = message.result or ""
    except ResultError as exc:
        # 跟舊版「claude -p --output-format json」的行為一致：is_error 的
        # 最終回合本身不讓呼叫端崩潰——實際該不該繼續、要不要停下來，交給
        # gates.py 讀 run 目錄裡的檔案狀態決定，這裡只負責取回文字內容。
        last_result = exc.result or str(exc)
    return last_result


def invoke_claude(run_dir, prompt: str, config: DriverConfig) -> str:
    try:
        return asyncio.run(
            asyncio.wait_for(_query_once(run_dir, prompt, config), timeout=config.per_call_timeout_seconds)
        )
    except (asyncio.TimeoutError, TimeoutError) as exc:
        raise DriverTimeoutError(
            f"claude query() 逾時（超過 per_call_timeout_seconds={config.per_call_timeout_seconds} 秒）"
        ) from exc


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

        try:
            last_stdout = invoke_claude(run_dir, prompt, config)
        except DriverTimeoutError as exc:
            turns += 1
            return DriverResult(Outcome.ERROR, turns, str(exc), last_stdout)
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
