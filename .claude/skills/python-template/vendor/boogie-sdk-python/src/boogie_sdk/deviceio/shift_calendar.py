"""ShiftCalendar stub. See boogie-sdk-api.md (this skill's library doc) section 5.3 (deviceio).

Skeleton only — implemented during the Phase 1 TDD loop for the `deviceio` module.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time


@dataclass(frozen=True)
class Shift:
    name: str
    start: time
    end: time


@dataclass(frozen=True)
class ShiftBoundary:
    day: date
    shifts: list[Shift]


_DAY = Shift(name="Day", start=time(8, 0), end=time(16, 0))
_EVENING = Shift(name="Evening", start=time(16, 0), end=time(0, 0))
_NIGHT = Shift(name="Night", start=time(0, 0), end=time(8, 0))

_SHIFTS: list[Shift] = [_DAY, _EVENING, _NIGHT]


class ShiftCalendar:
    def current_shift(self, at: datetime) -> Shift:
        t = at.time()
        if _DAY.start <= t < _DAY.end:
            return _DAY
        if _EVENING.start <= t:
            return _EVENING
        # t < _NIGHT.end (i.e. before 08:00) or exactly midnight
        return _NIGHT

    def boundaries_for(self, day: date) -> ShiftBoundary:
        return ShiftBoundary(day=day, shifts=list(_SHIFTS))
