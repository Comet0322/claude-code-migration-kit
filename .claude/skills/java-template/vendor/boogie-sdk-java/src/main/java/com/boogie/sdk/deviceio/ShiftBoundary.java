package com.boogie.sdk.deviceio;

import java.time.LocalDate;
import java.util.List;

public record ShiftBoundary(LocalDate day, List<Shift> shifts) {
}
