package com.boogie.sdk.core;

/** Base class for all boogie-sdk exceptions. See boogie-sdk-api.md section 4. */
public class PlatformException extends RuntimeException {
    public PlatformException(String message) {
        super(message);
    }

    public PlatformException(String message, Throwable cause) {
        super(message, cause);
    }
}
