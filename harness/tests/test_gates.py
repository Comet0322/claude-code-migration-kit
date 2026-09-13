from harness.gates import Outcome, evaluate_gate
from harness.state import RunState, UnitState


def _base_state(**overrides) -> RunState:
    from pathlib import Path
    defaults = dict(run_dir=Path("/tmp/run"))
    defaults.update(overrides)
    return RunState(**defaults)


def test_needs_human_when_decision_log_says_so():
    state = _base_state(decision_log_last_status="needs-human")

    decision = evaluate_gate(state)

    assert decision.outcome == Outcome.NEEDS_HUMAN
    assert "decision-log" in decision.reason


def test_continue_and_auto_signoff_when_pilot_clean():
    state = _base_state(
        pilot_manifest_exists=True,
        pilot_signoff_exists=False,
        unit_states={
            "A": UnitState("A", "pass", {}, ""),
            "B": UnitState("B", "excluded", {}, ""),
        },
        rulebook_amendments_pending=False,
    )
    # pilot-manifest.tsv 需要真的存在讓 _pilot_unit_ids 讀得到
    import tempfile
    from pathlib import Path
    with tempfile.TemporaryDirectory() as tmp:
        run_dir = Path(tmp)
        migration_dir = run_dir / "migration"
        migration_dir.mkdir()
        (migration_dir / "pilot-manifest.tsv").write_text("A\tx\ty\nB\tx\ty\n", encoding="utf-8")
        state.run_dir = run_dir

        decision = evaluate_gate(state)

    assert decision.outcome == Outcome.CONTINUE
    assert decision.write_pilot_signoff is True


def test_needs_human_when_pilot_not_clean():
    import tempfile
    from pathlib import Path
    state = _base_state(
        pilot_manifest_exists=True,
        pilot_signoff_exists=False,
        unit_states={"A": UnitState("A", "fail-test", {}, "")},
    )
    with tempfile.TemporaryDirectory() as tmp:
        run_dir = Path(tmp)
        migration_dir = run_dir / "migration"
        migration_dir.mkdir()
        (migration_dir / "pilot-manifest.tsv").write_text("A\tx\ty\n", encoding="utf-8")
        state.run_dir = run_dir

        decision = evaluate_gate(state)

    assert decision.outcome == Outcome.NEEDS_HUMAN


def test_success_when_manifest_all_done_and_integration_pass():
    state = _base_state(
        manifest_rows=[{"unit_id": "A", "source_path": "x", "target_path": "y"}],
        unit_states={"A": UnitState("A", "pass", {}, "")},
        integration_status="pass",
    )

    decision = evaluate_gate(state)

    assert decision.outcome == Outcome.SUCCESS


def test_needs_human_when_integration_fails():
    state = _base_state(
        manifest_rows=[{"unit_id": "A", "source_path": "x", "target_path": "y"}],
        unit_states={"A": UnitState("A", "pass", {}, "")},
        integration_status="fail",
    )

    decision = evaluate_gate(state)

    assert decision.outcome == Outcome.NEEDS_HUMAN


def test_continue_when_nothing_terminal_yet():
    state = _base_state()

    decision = evaluate_gate(state)

    assert decision.outcome == Outcome.CONTINUE
