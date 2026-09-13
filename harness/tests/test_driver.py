import asyncio
from pathlib import Path

import pytest
from claude_agent_sdk import ResultError, ResultMessage

from harness.driver import DriverConfig, DriverTimeoutError, invoke_claude
from harness.gates import Outcome


def _result_message(result: str, is_error: bool = False) -> ResultMessage:
    return ResultMessage(
        subtype="success",
        duration_ms=1,
        duration_api_ms=1,
        is_error=is_error,
        num_turns=1,
        session_id="s1",
        result=result,
    )


def test_invoke_claude_passes_options_and_returns_last_result(monkeypatch, tmp_path: Path):
    captured = {}

    async def fake_query(*, prompt, options):
        captured["prompt"] = prompt
        captured["options"] = options
        yield _result_message("done")

    monkeypatch.setattr("harness.driver.query", fake_query)

    output = invoke_claude(tmp_path, "跑 migration skill", DriverConfig())

    assert output == "done"
    assert captured["prompt"] == "跑 migration skill"
    assert captured["options"].cwd == str(tmp_path)
    assert captured["options"].permission_mode == "acceptEdits"
    assert captured["options"].allowed_tools == ["Bash", "Edit", "Write", "Read", "Glob", "Grep", "Skill", "Task"]


def test_invoke_claude_uses_last_result_message_when_multiple(monkeypatch, tmp_path: Path):
    async def fake_query(*, prompt, options):
        yield _result_message("intermediate")
        yield _result_message("final")

    monkeypatch.setattr("harness.driver.query", fake_query)

    output = invoke_claude(tmp_path, "prompt", DriverConfig())

    assert output == "final"


def test_invoke_claude_recovers_text_from_result_error_without_raising(monkeypatch, tmp_path: Path):
    # ResultError 是 SDK 對「最終回合 is_error=True」的自然反應（見
    # ResultMessage.is_error），對應舊版 CLI JSON 輸出裡 is_error 為 true
    # 的情況——舊版 invoke_claude 從不因此拋例外，只是把當時能拿到的文字
    # 內容原樣回傳，讓 gates.py 從檔案狀態（不是這段文字）決定下一步。SDK
    # 化之後維持同樣的行為：接住 ResultError，不讓它往上炸掉整個
    # run_loop。
    async def fake_query(*, prompt, options):
        yield _result_message("partial output before failure")
        raise ResultError("turn ended in error", data={"result": "partial output before failure"})

    monkeypatch.setattr("harness.driver.query", fake_query)

    output = invoke_claude(tmp_path, "prompt", DriverConfig())

    assert output == "partial output before failure"


def test_invoke_claude_raises_driver_timeout_error_instead_of_hanging(monkeypatch, tmp_path: Path):
    async def fake_query(*, prompt, options):
        await asyncio.sleep(10)
        yield _result_message("too late")

    monkeypatch.setattr("harness.driver.query", fake_query)

    with pytest.raises(DriverTimeoutError, match="逾時"):
        invoke_claude(tmp_path, "prompt", DriverConfig(per_call_timeout_seconds=0.01))


from harness.driver import run_loop
from harness.gates import GateDecision


def test_run_loop_stops_on_success(monkeypatch, tmp_path: Path):
    (tmp_path / "migration").mkdir()
    calls = {"invoke": 0}

    def fake_invoke(run_dir, prompt, config):
        calls["invoke"] += 1
        return "ok"

    decisions = [
        GateDecision(Outcome.CONTINUE, "still going"),
        GateDecision(Outcome.SUCCESS, "done"),
    ]

    def fake_evaluate_gate(state):
        return decisions.pop(0)

    monkeypatch.setattr("harness.driver.invoke_claude", fake_invoke)
    monkeypatch.setattr("harness.driver.evaluate_gate", fake_evaluate_gate)
    monkeypatch.setattr("harness.driver.read_run_state", lambda run_dir: object())

    result = run_loop(tmp_path, "e2e", DriverConfig(max_turns=5, max_wallclock_seconds=60))

    assert result.outcome == Outcome.SUCCESS
    assert result.turns_used == 2
    assert calls["invoke"] == 2


def test_run_loop_writes_pilot_signoff_then_continues(monkeypatch, tmp_path: Path):
    (tmp_path / "migration").mkdir()

    def fake_invoke(run_dir, prompt, config):
        return "ok"

    decisions = [
        GateDecision(Outcome.CONTINUE, "auto sign", write_pilot_signoff=True),
        GateDecision(Outcome.SUCCESS, "done"),
    ]

    def fake_evaluate_gate(state):
        return decisions.pop(0)

    monkeypatch.setattr("harness.driver.invoke_claude", fake_invoke)
    monkeypatch.setattr("harness.driver.evaluate_gate", fake_evaluate_gate)
    monkeypatch.setattr("harness.driver.read_run_state", lambda run_dir: object())

    result = run_loop(tmp_path, "e2e", DriverConfig(max_turns=5, max_wallclock_seconds=60))

    assert result.outcome == Outcome.SUCCESS
    assert (tmp_path / "migration" / "convert" / "pilot-signoff.txt").exists()


def test_run_loop_stops_at_max_turns(monkeypatch, tmp_path: Path):
    (tmp_path / "migration").mkdir()
    monkeypatch.setattr("harness.driver.invoke_claude", lambda *a, **k: "ok")
    monkeypatch.setattr("harness.driver.evaluate_gate", lambda state: GateDecision(Outcome.CONTINUE, "loop forever"))
    monkeypatch.setattr("harness.driver.read_run_state", lambda run_dir: object())

    result = run_loop(tmp_path, "e2e", DriverConfig(max_turns=3, max_wallclock_seconds=60))

    assert result.outcome == Outcome.ERROR
    assert "max_turns" in result.last_reason
    assert result.turns_used == 3


def test_run_loop_rejects_unknown_session_mode(tmp_path: Path):
    (tmp_path / "migration").mkdir()

    with pytest.raises(ValueError, match="session_mode"):
        run_loop(tmp_path, "e2e", DriverConfig(session_mode="not-a-real-mode"))


class _FakeClient:
    """單一 session 貫穿整個 run_loop 的假 client，用來驗證 persistent 模式
    只 connect 一次、之後每輪用同一個 client 重複 query()/receive_response()——
    不是每輪都重新建立一個新的 _FakeClient。"""

    instances: list["_FakeClient"] = []

    def __init__(self, options=None):
        self.options = options
        self.query_calls: list[str] = []
        self.connected = False
        self.disconnected = False
        _FakeClient.instances.append(self)

    async def __aenter__(self):
        self.connected = True
        return self

    async def __aexit__(self, exc_type, exc, tb):
        self.disconnected = True
        return False

    async def query(self, prompt: str) -> None:
        self.query_calls.append(prompt)

    async def receive_response(self):
        yield _result_message(f"result-{len(self.query_calls)}")


def test_run_loop_persistent_reuses_one_client_across_turns(monkeypatch, tmp_path: Path):
    (tmp_path / "migration").mkdir()
    _FakeClient.instances = []

    decisions = [
        GateDecision(Outcome.CONTINUE, "still going"),
        GateDecision(Outcome.CONTINUE, "still going"),
        GateDecision(Outcome.SUCCESS, "done"),
    ]

    monkeypatch.setattr("harness.driver.ClaudeSDKClient", _FakeClient)
    monkeypatch.setattr("harness.driver.evaluate_gate", lambda state: decisions.pop(0))
    monkeypatch.setattr("harness.driver.read_run_state", lambda run_dir: object())

    result = run_loop(
        tmp_path, "e2e",
        DriverConfig(max_turns=5, max_wallclock_seconds=60, session_mode="persistent"),
    )

    assert result.outcome == Outcome.SUCCESS
    assert result.turns_used == 3
    # 只建立了一個 client（一次 connect），三輪 query() 都打在同一個 client 上
    assert len(_FakeClient.instances) == 1
    client = _FakeClient.instances[0]
    assert client.connected is True
    assert client.disconnected is True
    assert len(client.query_calls) == 3


def test_run_loop_returns_error_on_timeout_instead_of_crashing(monkeypatch, tmp_path: Path):
    # regression test (found via real end-to-end validation in Task 9): a
    # single claude call that legitimately takes longer than
    # per_call_timeout_seconds (e.g. migration-convert dispatching three
    # subagents per unit) must produce a graceful Outcome.ERROR, not an
    # uncaught timeout that crashes the whole harness process.
    (tmp_path / "migration").mkdir()

    def fake_invoke_that_times_out(run_dir, prompt, config):
        raise DriverTimeoutError("claude query() 逾時（超過 per_call_timeout_seconds=1800 秒）")

    monkeypatch.setattr("harness.driver.invoke_claude", fake_invoke_that_times_out)
    monkeypatch.setattr("harness.driver.evaluate_gate", lambda state: GateDecision(Outcome.CONTINUE, "unused"))
    monkeypatch.setattr("harness.driver.read_run_state", lambda run_dir: object())

    result = run_loop(tmp_path, "e2e", DriverConfig(max_turns=5, max_wallclock_seconds=60))

    assert result.outcome == Outcome.ERROR
    assert "逾時" in result.last_reason
    assert result.turns_used == 1
