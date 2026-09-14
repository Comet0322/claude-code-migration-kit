package com.boogie.sdk.deviceio;

import java.util.Map;

public record DeviceEvent(String name, Map<String, Object> payload) {
}
