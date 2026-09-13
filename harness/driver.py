from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field

from claude_agent_sdk import ClaudeAgentOptions, ClaudeSDKClient, ResultError, ResultMessage, query

from harness.gates import Outcome, evaluate_gate
from harness.state import read_run_state

_DEFAULT_ALLOWED_TOOLS = ["Bash", "Edit", "Write", "Read", "Glob", "Grep", "Skill", "Task"]

# "fresh"（預設）：每一輪都重新起一個全新 subprocess/session，兩輪之間不
# 帶任何對話記憶——這剛好也在強制驗證 migration skill 設計裡最核心的一條
# 原則：狀態只活在 migration/ 底下的檔案，不靠隱藏的對話記憶傳遞（見
# README「Design principles」）。改成 "persistent" 能省掉每輪重開 process
# 的成本、跑起來快很多，但同時也讓這個驗證失去意義——如果 skill 哪天悄悄
# 開始依賴「記得自己剛剛的推理」而不是老實重新讀檔案，persistent 模式不會
# 抓到，只有 fresh 模式抓得到。真的要驗證 skill 設計是否正確，用 fresh；
# 只是想快速跑一次確認結果、不在意這條原則有沒有被驗到，才用 persistent。
_SESSION_MODES = ("fresh", "persistent")


@dataclass
class DriverConfig:
    max_turns: int = 20
    max_wallclock_seconds: int = 3600
    per_call_timeout_seconds: int = 1800
    allowed_tools: list[str] = field(default_factory=lambda: list(_DEFAULT_ALLOWED_TOOLS))
    session_mode: str = "fresh"


@dataclass
class DriverResult:
    outcome: Outcome
    turns_used: int
    last_reason: str
    last_stdout: str


class DriverTimeoutError(Exception):
    """單次 Claude Agent SDK 呼叫超過 per_call_timeout_seconds。"""


_E2E_PROMPT = "用 migration skill 處理這次遷移。"
_CONVERT_ONLY_PROMPT = "呼叫 migration-convert，manifest 路徑帶 migration/clarify/manifest.tsv。"


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


async def _query_streaming(client: ClaudeSDKClient, prompt: str) -> str:
    await client.query(prompt)
    last_result = ""
    try:
        async for message in client.receive_response():
            if isinstance(message, ResultMessage):
                last_result = message.result or ""
    except ResultError as exc:
        # 跟 _query_once 對稱處理，理由同上——見那邊的註解。
        last_result = exc.result or str(exc)
    return last_result


def _run_loop_fresh(run_dir, mode: str, config: DriverConfig) -> DriverResult:
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
            signoff_path = run_dir / "migration" / "convert" / "pilot-signoff.txt"
            signoff_path.parent.mkdir(parents=True, exist_ok=True)
            signoff_path.write_text(
                f"auto-approved by harness: {decision.reason}\n", encoding="utf-8"
            )

        if decision.outcome in (Outcome.SUCCESS, Outcome.NEEDS_HUMAN, Outcome.ERROR):
            return DriverResult(decision.outcome, turns, decision.reason, last_stdout)
        # Outcome.CONTINUE：進下一輪


async def _run_loop_persistent(run_dir, mode: str, config: DriverConfig) -> DriverResult:
    prompt = _E2E_PROMPT if mode == "e2e" else _CONVERT_ONLY_PROMPT
    start = time.monotonic()
    turns = 0
    last_stdout = ""

    options = ClaudeAgentOptions(
        cwd=str(run_dir),
        permission_mode="acceptEdits",
        allowed_tools=list(config.allowed_tools),
    )
    async with ClaudeSDKClient(options=options) as client:
        while True:
            if turns >= config.max_turns:
                return DriverResult(Outcome.ERROR, turns, f"超過 max_turns={config.max_turns}", last_stdout)
            if time.monotonic() - start >= config.max_wallclock_seconds:
                return DriverResult(Outcome.ERROR, turns, "超過 max_wallclock_seconds", last_stdout)

            try:
                last_stdout = await asyncio.wait_for(
                    _query_streaming(client, prompt), timeout=config.per_call_timeout_seconds
                )
            except (asyncio.TimeoutError, TimeoutError):
                turns += 1
                return DriverResult(
                    Outcome.ERROR,
                    turns,
                    f"claude query() 逾時（超過 per_call_timeout_seconds={config.per_call_timeout_seconds} 秒）",
                    last_stdout,
                )
            turns += 1

            state = read_run_state(run_dir)
            decision = evaluate_gate(state)

            if decision.write_pilot_signoff:
                signoff_path = run_dir / "migration" / "convert" / "pilot-signoff.txt"
                signoff_path.parent.mkdir(parents=True, exist_ok=True)
                signoff_path.write_text(
                    f"auto-approved by harness: {decision.reason}\n", encoding="utf-8"
                )

            if decision.outcome in (Outcome.SUCCESS, Outcome.NEEDS_HUMAN, Outcome.ERROR):
                return DriverResult(decision.outcome, turns, decision.reason, last_stdout)
            # Outcome.CONTINUE：進下一輪，同一個 client/session 繼續用


def run_loop(run_dir, mode: str, config: DriverConfig = DriverConfig()) -> DriverResult:
    if config.session_mode not in _SESSION_MODES:
        raise ValueError(f"未知的 session_mode: {config.session_mode!r}（合法值：{_SESSION_MODES}）")
    if config.session_mode == "persistent":
        return asyncio.run(_run_loop_persistent(run_dir, mode, config))
    return _run_loop_fresh(run_dir, mode, config)
