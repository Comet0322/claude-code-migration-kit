"""BatchTracker stub. See boogie-sdk-api.md (this skill's library doc) section 5.3 (deviceio).

Skeleton only — implemented during the Phase 1 TDD loop for the `deviceio` module.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from boogie_sdk.core.errors import NotFoundError


@dataclass(frozen=True)
class BatchEvent:
    batch_id: str
    status: str
    at: datetime


class BatchTracker:
    def __init__(self) -> None:
        self._history: dict[str, list[BatchEvent]] = {}

    def create_batch(self, batch_id: str) -> None:
        self._history[batch_id] = [
            BatchEvent(batch_id=batch_id, status="created", at=datetime.now(timezone.utc))
        ]

    def update_status(self, batch_id: str, status: str) -> None:
        if batch_id not in self._history:
            raise NotFoundError(f"Unknown batch_id: {batch_id!r}")
        self._history[batch_id].append(
            BatchEvent(batch_id=batch_id, status=status, at=datetime.now(timezone.utc))
        )

    def get_history(self, batch_id: str) -> list[BatchEvent]:
        if batch_id not in self._history:
            raise NotFoundError(f"Unknown batch_id: {batch_id!r}")
        return list(self._history[batch_id])
