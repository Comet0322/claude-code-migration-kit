package com.boogie.sdk.crypto;

import java.time.Instant;

public record Certificate(String certId, String subject, Instant expiresAt) {
}
