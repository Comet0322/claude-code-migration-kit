"""SpcAnalyzer stub. See boogie-sdk-api.md (this skill's library doc) section 5.3 (deviceio).

Skeleton only — implemented during the Phase 1 TDD loop for the `deviceio` module.
"""

from __future__ import annotations

from dataclasses import dataclass

from boogie_sdk.core.errors import ValidationError


@dataclass(frozen=True)
class ControlLimits:
    center: float
    upper: float
    lower: float


class SpcAnalyzer:
    def __init__(self) -> None:
        self._samples: list[float] = []

    def add_sample(self, value: float) -> None:
        self._samples.append(value)

    def control_limits(self) -> ControlLimits:
        if not self._samples:
            raise ValidationError("Cannot compute control limits with zero samples")

        n = len(self._samples)
        mean = sum(self._samples) / n
        variance = sum((x - mean) ** 2 for x in self._samples) / n
        stdev = variance**0.5

        return ControlLimits(
            center=mean,
            upper=mean + 3 * stdev,
            lower=mean - 3 * stdev,
        )

    def is_out_of_control(self) -> bool:
        if not self._samples:
            raise ValidationError("Cannot evaluate control state with zero samples")

        limits = self.control_limits()
        latest = self._samples[-1]
        return latest > limits.upper or latest < limits.lower
