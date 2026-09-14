package com.boogie.sdk.deviceio;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.CsvSource;

import java.time.Instant;
import java.time.LocalDate;
import java.time.LocalTime;
import java.time.ZoneOffset;

import static org.junit.jupiter.api.Assertions.assertEquals;

/**
 * Tests for ShiftCalendar. See boogie-sdk-api.md section 5.3 (deviceio).
 *
 * <p>Concrete 3-shift schedule convention invented for this fake (the
 * design doc only specifies the API shape, not an actual schedule),
 * mirroring the already-built Python port's {@code ShiftCalendar}:
 *
 * <ul>
 *   <li><b>Day</b>: 08:00 (inclusive) - 16:00 (exclusive)
 *   <li><b>Evening</b>: 16:00 (inclusive) - 00:00 (exclusive, i.e. midnight)
 *   <li><b>Night</b>: 00:00 (inclusive) - 08:00 (exclusive)
 * </ul>
 *
 * <p>Every day uses this same fixed 3-shift pattern (no weekends/holidays
 * special-casing). Boundaries are <b>start-inclusive, end-exclusive</b>: the
 * instant exactly on a shift's start time belongs to that shift; the
 * instant exactly on a shift's end time belongs to the <i>next</i> shift,
 * not the one ending.
 *
 * <p><b>UTC reference zone (explicit design choice):</b> {@code
 * currentShift(Instant)} must compare an absolute point in time ({@link
 * Instant}) against each {@link Shift}'s wall-clock {@link LocalTime}
 * bounds, which requires picking a time zone to render that instant's
 * time-of-day in. This fake fixes that zone to <b>UTC</b> (via {@code
 * at.atZone(ZoneOffset.UTC).toLocalTime()}) rather than the JVM's default
 * zone, so the schedule is deterministic regardless of where tests (or the
 * implementation) run. {@code boundariesFor(day)} returns the same fixed
 * {@link ShiftBoundary} (day + all 3 {@link Shift}s) for any given calendar
 * day, independent of zone.
 */
class ShiftCalendarTest {

    private static final LocalDate SOME_DAY = LocalDate.of(2026, 9, 14);

    private ShiftCalendar calendar;

    @BeforeEach
    void setUp() {
        calendar = new ShiftCalendar();
    }

    private static Instant utcInstant(int hour, int minute, int second) {
        return SOME_DAY.atTime(hour, minute, second).toInstant(ZoneOffset.UTC);
    }

    // -- boundariesFor -----------------------------------------------------------

    @Test
    void boundariesForReturnsThreeShiftsForTheDay() {
        ShiftBoundary boundary = calendar.boundariesFor(SOME_DAY);

        assertEquals(SOME_DAY, boundary.day());
        assertEquals(java.util.List.of("Day", "Evening", "Night"),
                boundary.shifts().stream().map(Shift::name).toList());
    }

    @Test
    void boundariesForHasExpectedStartEndTimes() {
        ShiftBoundary boundary = calendar.boundariesFor(SOME_DAY);
        var byName = boundary.shifts().stream()
                .collect(java.util.stream.Collectors.toMap(Shift::name, s -> s));

        assertEquals(LocalTime.of(8, 0), byName.get("Day").start());
        assertEquals(LocalTime.of(16, 0), byName.get("Day").end());
        assertEquals(LocalTime.of(16, 0), byName.get("Evening").start());
        assertEquals(LocalTime.of(0, 0), byName.get("Evening").end());
        assertEquals(LocalTime.of(0, 0), byName.get("Night").start());
        assertEquals(LocalTime.of(8, 0), byName.get("Night").end());
    }

    // -- currentShift: interior points -------------------------------------------

    @ParameterizedTest
    @CsvSource({
            "8, 0, Day",
            "12, 30, Day",
            "15, 59, Day",
            "16, 0, Evening",
            "20, 0, Evening",
            "23, 59, Evening",
            "0, 0, Night",
            "3, 0, Night",
            "7, 59, Night",
    })
    void currentShiftForInteriorAndBoundaryMinutes(int hour, int minute, String expectedName) {
        Instant at = utcInstant(hour, minute, 0);

        Shift shift = calendar.currentShift(at);

        assertEquals(expectedName, shift.name());
    }

    // -- currentShift: exact boundary instants -----------------------------------

    @Test
    void currentShiftExactlyAtDayStartIsDayShift() {
        assertEquals("Day", calendar.currentShift(utcInstant(8, 0, 0)).name());
    }

    @Test
    void currentShiftExactlyAtEveningStartIsEveningShift() {
        assertEquals("Evening", calendar.currentShift(utcInstant(16, 0, 0)).name());
    }

    @Test
    void currentShiftExactlyAtMidnightIsNightShift() {
        assertEquals("Night", calendar.currentShift(utcInstant(0, 0, 0)).name());
    }

    @Test
    void currentShiftJustBeforeDayStartIsNightShift() {
        assertEquals("Night", calendar.currentShift(utcInstant(7, 59, 59)).name());
    }

    @Test
    void currentShiftJustBeforeEveningStartIsDayShift() {
        assertEquals("Day", calendar.currentShift(utcInstant(15, 59, 59)).name());
    }
}
