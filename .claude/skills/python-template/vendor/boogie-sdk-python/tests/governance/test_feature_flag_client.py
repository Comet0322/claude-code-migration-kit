"""Tests for FeatureFlagClient. See boogie-sdk-api.md (this skill's library doc)
section 5.5 (governance).

The design doc only documents `is_enabled(flag_key, context=None) -> bool`
with no way to configure a flag's state and no real flag service behind
this fake. This test file pins down the additive, testable conventions
invented to make the fake usable:

- **Constructor**: `FeatureFlagClient(default_enabled: bool = False)`.
  Any flag key that has never been explicitly configured evaluates to
  this default.
- **`set_flag(flag_key: str, enabled: bool) -> None`** (additive, not in
  the design doc): configures a specific flag's value. Once set, that
  flag key's `is_enabled(...)` reflects the configured value regardless
  of the client's `default_enabled`, and can be flipped again by calling
  `set_flag` again with a different value.
- **`context`**: accepted by `is_enabled` per the design-doc signature,
  but this fake has no rule engine — it is simply ignored. Passing any
  `dict` (or `None`) must not raise and must not change the result.
"""

from __future__ import annotations

import pytest

from boogie_sdk.governance.feature_flag_client import FeatureFlagClient


def test_unconfigured_flag_returns_false_by_default() -> None:
    client = FeatureFlagClient()
    assert client.is_enabled("unconfigured-flag") is False


def test_unconfigured_flag_returns_configured_default_enabled() -> None:
    client = FeatureFlagClient(default_enabled=True)
    assert client.is_enabled("unconfigured-flag") is True


def test_set_flag_true_then_is_enabled_reflects_true() -> None:
    client = FeatureFlagClient(default_enabled=False)
    client.set_flag("new-checkout", True)
    assert client.is_enabled("new-checkout") is True


def test_set_flag_false_then_is_enabled_reflects_false() -> None:
    client = FeatureFlagClient(default_enabled=True)
    client.set_flag("kill-switch", False)
    assert client.is_enabled("kill-switch") is False


def test_set_flag_can_be_flipped_back_and_forth() -> None:
    client = FeatureFlagClient()
    client.set_flag("toggle", True)
    assert client.is_enabled("toggle") is True

    client.set_flag("toggle", False)
    assert client.is_enabled("toggle") is False


def test_setting_one_flag_does_not_affect_other_unconfigured_flags() -> None:
    client = FeatureFlagClient(default_enabled=False)
    client.set_flag("flag-a", True)

    assert client.is_enabled("flag-a") is True
    assert client.is_enabled("flag-b") is False


@pytest.mark.parametrize("context", [None, {}, {"user_id": "u1", "region": "us"}])
def test_context_param_is_accepted_without_error_and_does_not_change_result(
    context: dict | None,
) -> None:
    client = FeatureFlagClient(default_enabled=True)
    assert client.is_enabled("some-flag", context=context) is True
