"""FeatureFlagClient stub. See boogie-sdk-api.md (this skill's library doc) section 5.5 (governance).

Skeleton only — implemented during the Phase 1 TDD loop for the `governance` module.
"""

from __future__ import annotations

from typing import Any


class FeatureFlagClient:
    def __init__(self, default_enabled: bool = False) -> None:
        self._default_enabled = default_enabled
        self._flags: dict[str, bool] = {}

    def is_enabled(self, flag_key: str, context: dict[str, Any] | None = None) -> bool:
        return self._flags.get(flag_key, self._default_enabled)

    def set_flag(self, flag_key: str, enabled: bool) -> None:
        self._flags[flag_key] = enabled
