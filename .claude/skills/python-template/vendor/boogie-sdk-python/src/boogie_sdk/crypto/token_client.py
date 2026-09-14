"""TokenClient stub. See boogie-sdk-api.md (this skill's library doc) section 5.1 (crypto).

JWT-like opaque tokens: `base64url(json(claims)).base64url(hmac_sha256(payload))`.
The signing key is simulated key material held in-memory per `TokenClient`
instance (there is only one implicit "signing key_id" for this client, since
the design doc's `issue_token`/`verify_token` signatures don't take one).

Convention (not pinned down by the design doc beyond signatures, so fixed
here per tests/crypto/test_token_client.py):
- If the claims dict contains an `"exp"` key (Unix timestamp, int/float),
  `verify_token` raises `CryptoError` once that time is in the past.
- Any tampering (signature or payload) or structurally invalid token string
  raises `CryptoError` rather than leaking a lower-level parsing exception.
"""

from __future__ import annotations

import base64
import hmac as hmac_module
import json
import os
import time
from dataclasses import dataclass, field
from typing import Any

from boogie_sdk.core.errors import CryptoError

_SECRET_KEY_BYTES = 32


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64url_decode(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)


@dataclass(frozen=True)
class Claims:
    values: dict[str, Any] = field(default_factory=dict)


class TokenClient:
    def __init__(self) -> None:
        self._secret_key = os.urandom(_SECRET_KEY_BYTES)

    def _sign(self, payload_b64: str) -> str:
        mac = hmac_module.new(
            self._secret_key, payload_b64.encode("ascii"), "sha256"
        ).digest()
        return _b64url_encode(mac)

    def issue_token(self, claims: dict[str, Any]) -> str:
        payload = json.dumps(claims, separators=(",", ":"), sort_keys=True).encode(
            "utf-8"
        )
        payload_b64 = _b64url_encode(payload)
        signature_b64 = self._sign(payload_b64)
        return f"{payload_b64}.{signature_b64}"

    def verify_token(self, token: str) -> Claims:
        try:
            payload_b64, signature_b64 = token.split(".")
            expected_signature_b64 = self._sign(payload_b64)
            if not hmac_module.compare_digest(signature_b64, expected_signature_b64):
                raise CryptoError("token signature mismatch")
            payload = json.loads(_b64url_decode(payload_b64))
            if not isinstance(payload, dict):
                raise CryptoError("token payload is not a claims object")
        except CryptoError:
            raise
        except Exception as exc:
            raise CryptoError("malformed token") from exc

        exp = payload.get("exp")
        if exp is not None and float(exp) < time.time():
            raise CryptoError("token has expired")

        return Claims(values=payload)
