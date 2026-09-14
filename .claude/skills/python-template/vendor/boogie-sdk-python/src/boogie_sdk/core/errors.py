"""Exception hierarchy shared by every boogie_sdk module.

See boogie-sdk-api.md (this skill's library doc) section 4 (共用慣例).
"""


class PlatformError(Exception):
    """Base class for all boogie_sdk errors."""


class InfraError(PlatformError):
    """Raised by infra module clients (http, db, cache, queue, storage, discovery, scheduler)."""


class CryptoError(PlatformError):
    """Raised by crypto module clients."""


class ValidationError(PlatformError):
    """Raised when input data fails validation."""


class DeviceIoError(PlatformError):
    """Raised by deviceio module clients."""


class NotFoundError(PlatformError):
    """Raised when a requested resource does not exist."""


class RateLimitExceededError(PlatformError):
    """Raised when a rate limiter rejects an acquisition."""
