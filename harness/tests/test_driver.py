import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from harness.driver import DriverConfig, invoke_claude
from harness.gates import Outcome


def test_invoke_claude_builds_command_and_parses_result(monkeypatch, tmp_path: Path):
    captured = {}

    def fake_run(cmd, cwd, capture_output, text, timeout):
        captured["cmd"] = cmd
        captured["cwd"] = cwd
        captured["timeout"] = timeout
        return SimpleNamespace(
            stdout=json.dumps({"result": "done", "is_error": False}),
            stderr="",
            returncode=0,
        )

    monkeypatch.setattr("harness.driver.subprocess.run", fake_run)

    output = invoke_claude(tmp_path, "跑 migration skill", DriverConfig())

    assert output == "done"
    assert captured["cmd"][0] == "claude"
    assert "-p" in captured["cmd"]
    assert "跑 migration skill" in captured["cmd"]
    assert "--output-format" in captured["cmd"]
    assert "json" in captured["cmd"]
    assert "--permission-mode" in captured["cmd"]
    assert "acceptEdits" in captured["cmd"]
    assert "--allowedTools" in captured["cmd"]
    assert "Bash,Edit,Write,Read,Glob,Grep,Skill,Task" in captured["cmd"]
    assert captured["cwd"] == tmp_path


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
    assert (tmp_path / "migration" / "pilot-signoff.txt").exists()


def test_run_loop_stops_at_max_turns(monkeypatch, tmp_path: Path):
    (tmp_path / "migration").mkdir()
    monkeypatch.setattr("harness.driver.invoke_claude", lambda *a, **k: "ok")
    monkeypatch.setattr("harness.driver.evaluate_gate", lambda state: GateDecision(Outcome.CONTINUE, "loop forever"))
    monkeypatch.setattr("harness.driver.read_run_state", lambda run_dir: object())

    result = run_loop(tmp_path, "e2e", DriverConfig(max_turns=3, max_wallclock_seconds=60))

    assert result.outcome == Outcome.ERROR
    assert "max_turns" in result.last_reason
    assert result.turns_used == 3
