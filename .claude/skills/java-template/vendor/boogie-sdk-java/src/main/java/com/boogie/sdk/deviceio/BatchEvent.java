package com.boogie.sdk.deviceio;

import java.time.Instant;

public record BatchEvent(String batchId, String status, Instant at) {
}
