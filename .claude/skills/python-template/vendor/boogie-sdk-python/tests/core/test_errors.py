from boogie_sdk.core.errors import (
    CryptoError,
    DeviceIoError,
    InfraError,
    NotFoundError,
    PlatformError,
    RateLimitExceededError,
    ValidationError,
)


def test_all_errors_are_platform_errors():
    for cls in (
        CryptoError,
        DeviceIoError,
        InfraError,
        NotFoundError,
        RateLimitExceededError,
        ValidationError,
    ):
        assert issubclass(cls, PlatformError)
        assert isinstance(cls("boom"), PlatformError)
