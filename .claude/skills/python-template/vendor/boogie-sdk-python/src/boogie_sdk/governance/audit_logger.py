"""AuditLogger stub. See boogie-sdk-api.md (this skill's library doc) section 5.5 (governance).

Skeleton only — implemented during the Phase 1 TDD loop for the `governance` module.
"""

from __future__ import annotations


class AuditLogger:
    def __init__(self) -> None:
        self.records: list[dict] = []

    def record(self, actor: str, action: str, resource: str, result: str) -> None:
        self.records.append(
            {
                "actor": actor,
                "action": action,
                "resource": resource,
                "result": result,
            }
        )
