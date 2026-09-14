"""Tests for TokenClient. See boogie-sdk-api.md (this skill's library doc) section 5.1.

`issue_token`/`verify_token` sign is not fully pinned down by the design doc
beyond the method signatures, so this test file documents the conventions it
expects the implementation to follow (the implementer must satisfy these):

- `issue_token(claims)` returns an opaque `str` token that embeds the given
  claims plus a tamper-evident signature (HMAC/JWT-like).
- `verify_token(token)` returns a `Claims` whose `.values` equals the claims
  dict that was originally issued, when the token is untouched.
- If a tampered token (any single character flipped) or a structurally
  invalid token string is passed to `verify_token`, it raises `CryptoError`
  rather than returning garbage or leaking a lower-level parsing exception.
- Expiration convention: if the issued claims dict includes an `"exp"` key
  (an int/float Unix timestamp), `verify_token` must treat the token as
  expired -- and raise `CryptoError` -- once `exp` is in the past. This
  mirrors common JWT `exp` semantics and is the convention these tests are
  written against.
"""

from __future__ import annotations

import time

import pytest

from boogie_sdk.core.errors import CryptoError
from boogie_sdk.crypto.token_client import Claims, TokenClient


@pytest.fixture
def client() -> TokenClient:
    return TokenClient()


def test_claims_default_values_is_empty_dict() -> None:
    assert Claims().values == {}


def test_issue_token_returns_string(client: TokenClient) -> None:
    token = client.issue_token({"sub": "user-1"})
    assert isinstance(token, str)
    assert token != ""


def test_issue_then_verify_round_trip(client: TokenClient) -> None:
    claims_in = {"sub": "user-1", "role": "admin"}
    token = client.issue_token(claims_in)

    claims_out = client.verify_token(token)

    assert isinstance(claims_out, Claims)
    assert claims_out.values == claims_in


def test_verify_token_with_future_expiry_succeeds(client: TokenClient) -> None:
    claims_in = {"sub": "user-1", "exp": time.time() + 3600}
    token = client.issue_token(claims_in)

    claims_out = client.verify_token(token)

    assert claims_out.values["sub"] == "user-1"


def test_verify_expired_token_raises_crypto_error(client: TokenClient) -> None:
    claims_in = {"sub": "user-1", "exp": time.time() - 3600}
    token = client.issue_token(claims_in)

    with pytest.raises(CryptoError):
        client.verify_token(token)


def test_verify_tampered_token_raises_crypto_error(client: TokenClient) -> None:
    token = client.issue_token({"sub": "user-1"})

    # Flip the last character to corrupt the signature/payload.
    last = token[-1]
    replacement = "a" if last != "a" else "b"
    tampered = token[:-1] + replacement

    with pytest.raises(CryptoError):
        client.verify_token(tampered)


def test_verify_structurally_invalid_token_raises_crypto_error(
    client: TokenClient,
) -> None:
    with pytest.raises(CryptoError):
        client.verify_token("not-a-real-token")


def test_verify_never_leaks_raw_lower_level_exception(client: TokenClient) -> None:
    try:
        client.verify_token("###garbage###")
        pytest.fail("expected verify_token to raise for garbage input")
    except CryptoError:
        pass
    except Exception as exc:  # pragma: no cover - explicit failure path
        pytest.fail(
            "verify_token must wrap low-level errors in CryptoError, "
            f"but raised {type(exc).__name__} instead"
        )
