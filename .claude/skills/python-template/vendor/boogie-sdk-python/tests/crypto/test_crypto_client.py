"""Tests for CryptoClient. See boogie-sdk-api.md (this skill's library doc) section 5.1.

CryptoClient is implemented with real crypto primitives (AES-GCM, SHA256/512,
HMAC, and an asymmetric sign/verify scheme), not a fake. Key material is
simulated in-memory and keyed off an opaque `key_id` string: the client is
expected to lazily create/derive a key the first time a given key_id is used
and reuse the same key material for that key_id on later calls (within the
same CryptoClient instance).
"""

from __future__ import annotations

import pytest

from boogie_sdk.core.errors import CryptoError
from boogie_sdk.crypto.crypto_client import CryptoClient, HashAlgo

# Well-known reference digests, used to also catch an incorrect algorithm
# choice (e.g. accidentally hashing with MD5 or truncating).
SHA256_EMPTY = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
SHA256_ABC = "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
SHA512_ABC = (
    "ddaf35a193617abacc417349ae20413112e6fa4e89a97ea20a9eeee64b55d39"
    "a2192992a274fc1a836ba3c23a3feebbd454d4423643ce80e2a9ac94fa54ca49f"
)


@pytest.fixture
def client() -> CryptoClient:
    return CryptoClient()


# -- encrypt_aes / decrypt_aes -----------------------------------------------


def test_encrypt_aes_output_differs_from_plaintext(client: CryptoClient) -> None:
    plaintext = b"top secret payload"
    ciphertext = client.encrypt_aes(plaintext, key_id="k1")

    assert isinstance(ciphertext, bytes)
    assert ciphertext != plaintext
    assert plaintext not in ciphertext


def test_encrypt_aes_is_nondeterministic_for_same_plaintext_and_key(
    client: CryptoClient,
) -> None:
    plaintext = b"same message every time"

    first = client.encrypt_aes(plaintext, key_id="k1")
    second = client.encrypt_aes(plaintext, key_id="k1")

    # A correct AES-GCM implementation uses a fresh random nonce/IV per call,
    # so two encryptions of the same plaintext under the same key must not
    # produce identical ciphertext.
    assert first != second


def test_encrypt_decrypt_round_trip(client: CryptoClient) -> None:
    plaintext = b"round trip me"
    ciphertext = client.encrypt_aes(plaintext, key_id="k1")

    assert client.decrypt_aes(ciphertext, key_id="k1") == plaintext


def test_encrypt_decrypt_round_trip_empty_plaintext(client: CryptoClient) -> None:
    ciphertext = client.encrypt_aes(b"", key_id="k1")

    assert client.decrypt_aes(ciphertext, key_id="k1") == b""


def test_key_id_is_lazily_created_and_reused(client: CryptoClient) -> None:
    # A brand-new key_id should just work (no explicit key material passed
    # in, no pre-registration step) and the same key_id should decrypt what
    # it encrypted.
    ciphertext = client.encrypt_aes(b"hello", key_id="brand-new-key-id")
    assert client.decrypt_aes(ciphertext, key_id="brand-new-key-id") == b"hello"

    # Using the key_id again later still reuses the same underlying key.
    ciphertext2 = client.encrypt_aes(b"hello again", key_id="brand-new-key-id")
    assert client.decrypt_aes(ciphertext2, key_id="brand-new-key-id") == b"hello again"


def test_decrypt_with_wrong_key_id_raises_crypto_error(client: CryptoClient) -> None:
    ciphertext = client.encrypt_aes(b"secret", key_id="key-a")

    with pytest.raises(CryptoError):
        client.decrypt_aes(ciphertext, key_id="key-b")


def test_decrypt_with_corrupted_ciphertext_raises_crypto_error(
    client: CryptoClient,
) -> None:
    ciphertext = client.encrypt_aes(b"secret payload", key_id="k1")
    corrupted = bytearray(ciphertext)
    corrupted[-1] ^= 0xFF  # flip the last byte (breaks the GCM auth tag)

    with pytest.raises(CryptoError):
        client.decrypt_aes(bytes(corrupted), key_id="k1")


def test_decrypt_never_leaks_raw_cryptography_exception(client: CryptoClient) -> None:
    ciphertext = client.encrypt_aes(b"secret payload", key_id="k1")
    corrupted = bytes(ciphertext)[:-1]  # truncated ciphertext

    try:
        client.decrypt_aes(corrupted, key_id="k1")
        pytest.fail("expected decrypt_aes to raise for truncated ciphertext")
    except CryptoError:
        pass
    except Exception as exc:  # pragma: no cover - explicit failure path
        pytest.fail(
            "decrypt_aes must wrap low-level crypto errors in CryptoError, "
            f"but raised {type(exc).__name__} instead"
        )


# -- sign / verify ------------------------------------------------------------


def test_sign_returns_bytes(client: CryptoClient) -> None:
    signature = client.sign(b"data to sign", key_id="sign-key")
    assert isinstance(signature, bytes)
    assert len(signature) > 0


def test_sign_verify_round_trip(client: CryptoClient) -> None:
    data = b"important message"
    signature = client.sign(data, key_id="sign-key")

    assert client.verify(data, signature, key_id="sign-key") is True


def test_verify_tampered_data_returns_false(client: CryptoClient) -> None:
    data = b"important message"
    signature = client.sign(data, key_id="sign-key")

    assert client.verify(b"important MESSAGE", signature, key_id="sign-key") is False


def test_verify_tampered_signature_returns_false(client: CryptoClient) -> None:
    data = b"important message"
    signature = bytearray(client.sign(data, key_id="sign-key"))
    signature[0] ^= 0xFF

    assert client.verify(data, bytes(signature), key_id="sign-key") is False


def test_verify_with_wrong_key_id_returns_false(client: CryptoClient) -> None:
    data = b"important message"
    signature = client.sign(data, key_id="key-a")

    assert client.verify(data, signature, key_id="key-b") is False


def test_sign_key_id_is_lazily_created_and_reused(client: CryptoClient) -> None:
    data = b"payload"
    signature1 = client.sign(data, key_id="fresh-sign-key")
    signature2 = client.sign(data, key_id="fresh-sign-key")

    # Same key reused -> both signatures verify against the same key_id.
    assert client.verify(data, signature1, key_id="fresh-sign-key") is True
    assert client.verify(data, signature2, key_id="fresh-sign-key") is True


# -- hash -----------------------------------------------------------------


def test_hash_sha256_matches_known_vector_for_empty_input(client: CryptoClient) -> None:
    digest = client.hash(b"", HashAlgo.SHA256)
    assert digest.hex() == SHA256_EMPTY


def test_hash_sha256_matches_known_vector_for_abc(client: CryptoClient) -> None:
    digest = client.hash(b"abc", HashAlgo.SHA256)
    assert digest.hex() == SHA256_ABC


def test_hash_sha512_matches_known_vector_for_abc(client: CryptoClient) -> None:
    digest = client.hash(b"abc", HashAlgo.SHA512)
    assert digest.hex() == SHA512_ABC


def test_hash_is_deterministic(client: CryptoClient) -> None:
    assert client.hash(b"repeat me", HashAlgo.SHA256) == client.hash(
        b"repeat me", HashAlgo.SHA256
    )


def test_hash_differs_between_algorithms(client: CryptoClient) -> None:
    assert client.hash(b"abc", HashAlgo.SHA256) != client.hash(b"abc", HashAlgo.SHA512)


# -- hmac -------------------------------------------------------------------


def test_hmac_returns_bytes(client: CryptoClient) -> None:
    mac = client.hmac(b"message", key_id="hmac-key")
    assert isinstance(mac, bytes)
    assert len(mac) > 0


def test_hmac_is_deterministic_for_same_key_and_data(client: CryptoClient) -> None:
    mac1 = client.hmac(b"message", key_id="hmac-key")
    mac2 = client.hmac(b"message", key_id="hmac-key")
    assert mac1 == mac2


def test_hmac_differs_for_different_data(client: CryptoClient) -> None:
    mac1 = client.hmac(b"message one", key_id="hmac-key")
    mac2 = client.hmac(b"message two", key_id="hmac-key")
    assert mac1 != mac2


def test_hmac_differs_for_different_key_id(client: CryptoClient) -> None:
    mac1 = client.hmac(b"message", key_id="hmac-key-a")
    mac2 = client.hmac(b"message", key_id="hmac-key-b")
    assert mac1 != mac2
