package com.boogie.sdk.core;

/** Raised by deviceio module clients. */
public class DeviceIoException extends PlatformException {
    public DeviceIoException(String message) {
        super(message);
    }

    public DeviceIoException(String message, Throwable cause) {
        super(message, cause);
    }
}
