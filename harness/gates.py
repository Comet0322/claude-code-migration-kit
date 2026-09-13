from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from harness.state import RunState


class Outcome(str, Enum):
    CONTINUE = "continue"
    SUCCESS = "success"
    NEEDS_HUMAN = "needs-human"
    ERROR = "error"


@dataclass
class GateDecision:
    outcome: Outcome
    reason: str
    write_pilot_signoff: bool = False


_FAILURE_STATUSES = {"fail-conversion", "fail-test", "rule-gap"}


def evaluate_gate(state: RunState) -> GateDecision:
    if state.decision_log_last_status == "needs-human":
        return GateDecision(
            Outcome.NEEDS_HUMAN,
            "migration-clarify 在 decision-log.md 記錄 needs-human：缺乏客觀依據自決",
        )

    if state.rulebook_amendments_pending and any(
        u.status in _FAILURE_STATUSES for u in state.unit_states.values()
    ):
        return GateDecision(
            Outcome.NEEDS_HUMAN,
            "有 unit 卡在失敗狀態且 rulebook-amendments.md 有待處理項目",
        )

    if state.pilot_unit_ids and not state.pilot_signoff_exists:
        pilot_unit_ids = state.pilot_unit_ids
        pilot_units = [state.unit_states.get(u) for u in pilot_unit_ids]
        any_failed = any(
            u is not None and u.status in _FAILURE_STATUSES for u in pilot_units
        )
        all_terminal_clean = bool(pilot_unit_ids) and all(
            u is not None and u.status in ("pass", "excluded") for u in pilot_units
        )
        if any_failed or (state.rulebook_amendments_pending and not all_terminal_clean):
            return GateDecision(
                Outcome.NEEDS_HUMAN,
                "pilot 裡有 unit 進入失敗狀態，或有待處理 rulebook-amendments，需要人類確認",
            )
        if all_terminal_clean and not state.rulebook_amendments_pending:
            return GateDecision(
                Outcome.CONTINUE,
                "pilot 全數 pass/excluded 且無待處理 rulebook-amendments，自動簽核",
                write_pilot_signoff=True,
            )
        # 還有 pilot unit 停在 pending（migration-convert 可能還沒被呼叫過，
        # 也可能才處理到一半）——這不是「不乾淨」，只是還沒跑完，繼續呼叫
        # 下一輪讓 router 有機會叫 migration-convert 處理，不要在這裡卡住
        # 等人類：只有真的出現失敗狀態或規則缺口待處理才需要人類，見上面
        # 的判斷。
        return GateDecision(
            Outcome.CONTINUE,
            "pilot 還有 unit 停在 pending（尚未被 migration-convert 處理過或處理到一半），繼續下一輪",
        )

    if state.manifest_rows:
        all_done = all(
            state.unit_states.get(row["unit_id"], None) is not None
            and state.unit_states[row["unit_id"]].status in ("pass", "excluded")
            for row in state.manifest_rows
        )
        if all_done:
            if state.integration_status == "pass":
                return GateDecision(Outcome.SUCCESS, "manifest 全數 pass/excluded 且整合檢查 pass")
            if state.integration_status == "fail":
                return GateDecision(Outcome.NEEDS_HUMAN, "整合檢查失敗，需要人類判斷退回哪個 unit")

    return GateDecision(Outcome.CONTINUE, "尚未到終止條件，繼續下一輪")
