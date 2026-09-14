package com.boogie.sdk.deviceio;

import java.time.Instant;
import java.time.LocalDate;
import java.time.LocalTime;
import java.time.ZoneOffset;
import java.util.List;

/**
 * ShiftCalendar stub. See boogie-sdk-api.md section 5.3 (deviceio).
 * Skeleton only — implemented during the Phase 1 TDD loop for the `deviceio` module.
 */
public class ShiftCalendar {

    private static final Shift DAY = new Shift("Day", LocalTime.of(8, 0), LocalTime.of(16, 0));
    private static final Shift EVENING = new Shift("Evening", LocalTime.of(16, 0), LocalTime.MIDNIGHT);
    private static final Shift NIGHT = new Shift("Night", LocalTime.MIDNIGHT, LocalTime.of(8, 0));
    private static final List<Shift> SHIFTS = List.of(DAY, EVENING, NIGHT);

    public Shift currentShift(Instant at) {
        LocalTime timeOfDay = at.atZone(ZoneOffset.UTC).toLocalTime();
        for (Shift shift : SHIFTS) {
            if (contains(shift, timeOfDay)) {
                return shift;
            }
        }
        throw new IllegalStateException("no shift matches time-of-day " + timeOfDay);
    }

    private static boolean contains(Shift shift, LocalTime timeOfDay) {
        boolean afterOrAtStart = !timeOfDay.isBefore(shift.start());
        boolean beforeEnd = shift.end().equals(LocalTime.MIDNIGHT)
                ? true
                : timeOfDay.isBefore(shift.end());
        return afterOrAtStart && beforeEnd;
    }

    public ShiftBoundary boundariesFor(LocalDate day) {
        return new ShiftBoundary(day, SHIFTS);
    }
}
