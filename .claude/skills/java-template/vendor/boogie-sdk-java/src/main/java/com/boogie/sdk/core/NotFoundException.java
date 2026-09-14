package com.boogie.sdk.core;

/** Raised when a requested resource does not exist. */
public class NotFoundException extends PlatformException {
    public NotFoundException(String message) {
        super(message);
    }

    public NotFoundException(String message, Throwable cause) {
        super(message, cause);
    }
}
