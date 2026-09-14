package com.boogie.sdk.deviceio;

import java.util.Map;

public record DeviceCommand(String name, Map<String, Object> args) {
}
