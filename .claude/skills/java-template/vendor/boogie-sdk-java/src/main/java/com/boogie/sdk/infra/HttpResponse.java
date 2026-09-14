package com.boogie.sdk.infra;

import java.util.Map;

public record HttpResponse(int statusCode, Map<String, String> headers, byte[] body) {
}
