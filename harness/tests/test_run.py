from pathlib import Path

from harness.gates import Outcome
from harness.driver import DriverResult
from harness.run import main


def test_main_wires_provisioning_driver_and_evaluate(monkeypatch, tmp_path: Path):
    calls = []

    def fake_create_run_dir(fixture_name, mode, runs_root):
        calls.append(("create_run_dir", fixture_name, mode))
        run_dir = tmp_path / "runs" / "fake-run"
        run_dir.mkdir(parents=True)
        (run_dir / "migration").mkdir()
        return run_dir

    def fake_provision_e2e(fixture_name, run_dir, fixtures_root, templates_root):
        calls.append(("provision_e2e", fixture_name))

    def fake_run_loop(run_dir, mode, config):
        calls.append(("run_loop", mode))
        return DriverResult(Outcome.SUCCESS, 2, "ok", "")

    def fake_read_run_state(run_dir):
        calls.append(("read_run_state",))
        from harness.state import RunState
        return RunState(run_dir=run_dir)

    def fake_load_test_config(fixture_name, fixtures_root):
        return {"expected_outcome": "success", "expected_units": {}}

    written = {}

    def fake_build_eval_report(*a, **k):
        return "report text"

    def fake_append_history(*a, **k):
        written["history"] = True

    monkeypatch.setattr("harness.run.create_run_dir", fake_create_run_dir)
    monkeypatch.setattr("harness.run.provision_e2e", fake_provision_e2e)
    monkeypatch.setattr("harness.run.run_loop", fake_run_loop)
    monkeypatch.setattr("harness.run.read_run_state", fake_read_run_state)
    monkeypatch.setattr("harness.run.load_test_config", fake_load_test_config)
    monkeypatch.setattr("harness.run.build_eval_report", fake_build_eval_report)
    monkeypatch.setattr("harness.run.append_history", fake_append_history)

    exit_code = main(["--fixture", "dept200-vb6", "--mode", "e2e",
                       "--fixtures-root", str(tmp_path / "fixtures"),
                       "--templates-root", str(tmp_path / "templates"),
                       "--runs-root", str(tmp_path / "runs"),
                       "--history-path", str(tmp_path / "history.tsv")])

    assert exit_code == 0
    assert ("provision_e2e", "dept200-vb6") in calls
    assert ("run_loop", "e2e") in calls
    assert written["history"] is True
    assert (tmp_path / "runs" / "fake-run" / "eval-report.md").read_text(encoding="utf-8") == "report text"
