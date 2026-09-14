package com.boogie.sdk.core;

/** Raised by crypto module clients. */
public class CryptoException extends PlatformException {
    public CryptoException(String message) {
        super(message);
    }

    public CryptoException(String message, Throwable cause) {
        super(message, cause);
    }
}
