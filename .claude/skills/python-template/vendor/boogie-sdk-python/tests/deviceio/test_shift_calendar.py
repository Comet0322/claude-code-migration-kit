"""Tests for ShiftCalendar. See boogie-sdk-api.md (this skill's library doc) section 5.3
(deviceio).

Concrete 3-shift schedule convention invented for this fake (the design doc
only specifies the API shape, not an actual schedule):

- **Day**: 08:00 (inclusive) – 16:00 (exclusive)
- **Evening**: 16:00 (inclusive) – 00:00 (exclusive, i.e. midnight)
- **Night**: 00:00 (inclusive) – 08:00 (exclusive)

Every day uses this same fixed 3-shift pattern (no weekends/holidays
special-casing). Boundaries are **start-inclusive, end-exclusive**: the
instant exactly on a shift's start time belongs to that shift; the instant
exactly on a shift's end time belongs to the *next* shift, not the one
ending. `current_shift(at)` uses only the time-of-day component of `at` to
pick a shift (the calendar's schedule is the same every day), while
`boundaries_for(day)` returns the `ShiftBoundary` (day + all 3 `Shift`s) for
a given calendar day.
"""

from __future__ import annotations

from datetime import date, datetime, time

import pytest

from boogie_sdk.deviceio.shift_calendar import Shift, ShiftBoundary, ShiftCalendar


@pytest.fixture
def calendar() -> ShiftCalendar:
    return ShiftCalendar()


SOME_DAY = date(2026, 9, 14)


# -- boundaries_for -----------------------------------------------------------


def test_boundaries_for_returns_three_shifts_for_the_day(
    calendar: ShiftCalendar,
) -> None:
    boundary = calendar.boundaries_for(SOME_DAY)

    assert isinstance(boundary, ShiftBoundary)
    assert boundary.day == SOME_DAY
    assert [s.name for s in boundary.shifts] == ["Day", "Evening", "Night"]


def test_boundaries_for_has_expected_start_end_times(calendar: ShiftCalendar) -> None:
    boundary = calendar.boundaries_for(SOME_DAY)
    shifts_by_name = {s.name: s for s in boundary.shifts}

    assert shifts_by_name["Day"].start == time(8, 0)
    assert shifts_by_name["Day"].end == time(16, 0)
    assert shifts_by_name["Evening"].start == time(16, 0)
    assert shifts_by_name["Evening"].end == time(0, 0)
    assert shifts_by_name["Night"].start == time(0, 0)
    assert shifts_by_name["Night"].end == time(8, 0)


# -- current_shift: interior points -------------------------------------------


@pytest.mark.parametrize(
    ("hour", "minute", "expected_name"),
    [
        (8, 0, "Day"),
        (12, 30, "Day"),
        (15, 59, "Day"),
        (16, 0, "Evening"),
        (20, 0, "Evening"),
        (23, 59, "Evening"),
        (0, 0, "Night"),
        (3, 0, "Night"),
        (7, 59, "Night"),
    ],
)
def test_current_shift_for_interior_and_boundary_minutes(
    calendar: ShiftCalendar, hour: int, minute: int, expected_name: str
) -> None:
    at = datetime.combine(SOME_DAY, time(hour, minute))

    shift = calendar.current_shift(at)

    assert isinstance(shift, Shift)
    assert shift.name == expected_name


# -- current_shift: exact boundary instants -----------------------------------


def test_current_shift_exactly_at_day_start_is_day_shift(
    calendar: ShiftCalendar,
) -> None:
    at = datetime.combine(SOME_DAY, time(8, 0, 0))
    assert calendar.current_shift(at).name == "Day"


def test_current_shift_exactly_at_evening_start_is_evening_shift(
    calendar: ShiftCalendar,
) -> None:
    at = datetime.combine(SOME_DAY, time(16, 0, 0))
    assert calendar.current_shift(at).name == "Evening"


def test_current_shift_exactly_at_midnight_is_night_shift(
    calendar: ShiftCalendar,
) -> None:
    at = datetime.combine(SOME_DAY, time(0, 0, 0))
    assert calendar.current_shift(at).name == "Night"


def test_current_shift_just_before_day_start_is_night_shift(
    calendar: ShiftCalendar,
) -> None:
    at = datetime.combine(SOME_DAY, time(7, 59, 59))
    assert calendar.current_shift(at).name == "Night"


def test_current_shift_just_before_evening_start_is_day_shift(
    calendar: ShiftCalendar,
) -> None:
    at = datetime.combine(SOME_DAY, time(15, 59, 59))
    assert calendar.current_shift(at).name == "Day"
