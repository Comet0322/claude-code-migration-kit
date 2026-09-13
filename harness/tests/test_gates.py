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
        pilot_unit_ids=["A", "B"],
        pilot_signoff_exists=False,
        unit_states={
            "A": UnitState("A", "pass", {}, ""),
            "B": UnitState("B", "excluded", {}, ""),
        },
        rulebook_amendments_pending=False,
    )

    decision = evaluate_gate(state)

    assert decision.outcome == Outcome.CONTINUE
    assert decision.write_pilot_signoff is True


def test_needs_human_when_pilot_not_clean():
    state = _base_state(
        pilot_unit_ids=["A"],
        pilot_signoff_exists=False,
        unit_states={"A": UnitState("A", "fail-test", {}, "")},
    )

    decision = evaluate_gate(state)

    assert decision.outcome == Outcome.NEEDS_HUMAN


def test_continue_when_pilot_unit_still_pending_with_no_state_file_and_nothing_failed():
    # regression test (found via real end-to-end validation in Task 9, not
    # just unit-level review): a unit listed in manifest.tsv's `pilot`
    # column with no state file yet (still pending — migration-convert may
    # not have been invoked for it at all yet) must NOT be silently treated
    # as "clean" (must not auto-signoff), but it also must NOT be treated as
    # "dirty, needs a human" — nothing has actually gone wrong,
    # migration-convert just hasn't finished (or started) processing it. The
    # correct action is to keep looping so the next `claude -p` turn lets
    # the router call migration-convert. Only an actual FAILURE status
    # should stop for human review — see test_needs_human_when_pilot_not_clean
    # above for that case (unit "A" has status "fail-test").
    state = _base_state(
        pilot_unit_ids=["A", "B"],
        pilot_signoff_exists=False,
        unit_states={"A": UnitState("A", "pass", {}, "")},  # B has no entry at all
    )

    decision = evaluate_gate(state)

    assert decision.outcome == Outcome.CONTINUE
    assert decision.write_pilot_signoff is False


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
