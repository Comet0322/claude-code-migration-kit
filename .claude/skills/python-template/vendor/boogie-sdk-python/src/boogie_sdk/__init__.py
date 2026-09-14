"""boogie-sdk: simulated all-in-one internal platform library (training use only).

All infra-facing clients are in-memory fakes — see docs/boogie-sdk-api.md.
"""

from boogie_sdk.config.config import BoogieConfig
from boogie_sdk.core.errors import (
    CryptoError,
    DeviceIoError,
    InfraError,
    NotFoundError,
    PlatformError,
    RateLimitExceededError,
    ValidationError,
)
from boogie_sdk.sdk import BoogieSdk

__all__ = [
    "BoogieSdk",
    "BoogieConfig",
    "PlatformError",
    "InfraError",
    "CryptoError",
    "ValidationError",
    "DeviceIoError",
    "NotFoundError",
    "RateLimitExceededError",
]
