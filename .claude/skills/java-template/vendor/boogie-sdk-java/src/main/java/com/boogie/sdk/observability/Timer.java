package com.boogie.sdk.observability;

public interface Timer {
    void record(double durationSeconds);
}
