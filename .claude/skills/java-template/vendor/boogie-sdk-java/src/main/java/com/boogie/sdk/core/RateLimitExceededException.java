package com.boogie.sdk.core;

/** Raised when a rate limiter rejects an acquisition. */
public class RateLimitExceededException extends PlatformException {
    public RateLimitExceededException(String message) {
        super(message);
    }

    public RateLimitExceededException(String message, Throwable cause) {
        super(message, cause);
    }
}
