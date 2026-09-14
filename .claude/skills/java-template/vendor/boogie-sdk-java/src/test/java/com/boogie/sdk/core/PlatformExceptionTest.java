package com.boogie.sdk.core;

import static org.junit.jupiter.api.Assertions.assertInstanceOf;

import org.junit.jupiter.api.Test;

class PlatformExceptionTest {

    @Test
    void allExceptionsArePlatformExceptions() {
        assertInstanceOf(PlatformException.class, new CryptoException("boom"));
        assertInstanceOf(PlatformException.class, new DeviceIoException("boom"));
        assertInstanceOf(PlatformException.class, new InfraException("boom"));
        assertInstanceOf(PlatformException.class, new NotFoundException("boom"));
        assertInstanceOf(PlatformException.class, new RateLimitExceededException("boom"));
        assertInstanceOf(PlatformException.class, new ValidationException("boom"));
    }
}
