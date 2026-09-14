package com.boogie.sdk.deviceio;

import java.time.LocalTime;

public record Shift(String name, LocalTime start, LocalTime end) {
}
