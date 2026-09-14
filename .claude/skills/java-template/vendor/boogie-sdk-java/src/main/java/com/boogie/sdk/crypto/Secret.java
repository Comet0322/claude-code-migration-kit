package com.boogie.sdk.crypto;

import java.util.Map;

public record Secret(String path, Map<String, String> data) {
}
