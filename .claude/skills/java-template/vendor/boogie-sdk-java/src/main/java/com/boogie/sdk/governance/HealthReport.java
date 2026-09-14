package com.boogie.sdk.governance;

import java.util.Map;

public record HealthReport(boolean healthy, Map<String, Boolean> checks) {
}
