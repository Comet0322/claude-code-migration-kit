package com.boogie.sdk.core;

/** Raised when input data fails validation. */
public class ValidationException extends PlatformException {
    public ValidationException(String message) {
        super(message);
    }

    public ValidationException(String message, Throwable cause) {
        super(message, cause);
    }
}
