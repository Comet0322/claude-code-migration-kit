package com.boogie.sdk.core;

/** Raised by infra module clients (http, db, cache, queue, storage, discovery, scheduler). */
public class InfraException extends PlatformException {
    public InfraException(String message) {
        super(message);
    }

    public InfraException(String message, Throwable cause) {
        super(message, cause);
    }
}
