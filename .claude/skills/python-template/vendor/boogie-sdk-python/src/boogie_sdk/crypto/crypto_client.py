"""CryptoClient stub. See boogie-sdk-api.md (this skill's library doc) section 5.1 (crypto).

Real cryptographic primitives (AES-256-GCM, SHA-256/512, HMAC-SHA256, and
Ed25519 sign/verify) backed by the `cryptography` package. Key material is
simulated "key management": each `CryptoClient` instance keeps private
in-memory dicts mapping an opaque `key_id` to real key material, lazily
generated the first time a given id is used and reused thereafter. There is
no persistence across process restarts -- this is a training fake, not a
real KMS.
"""

from __future__ import annotations

import hmac as hmac_module
import os
from enum import Enum

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from boogie_sdk.core.errors import CryptoError

_AES_KEY_BYTES = 32  # AES-256
_GCM_NONCE_BYTES = 12
_HMAC_KEY_BYTES = 32


class HashAlgo(Enum):
    SHA256 = "sha256"
    SHA512 = "sha512"


_HASH_ALGO_MAP = {
    HashAlgo.SHA256: hashes.SHA256,
    HashAlgo.SHA512: hashes.SHA512,
}


class CryptoClient:
    def __init__(self) -> None:
        self._aes_keys: dict[str, bytes] = {}
        self._sign_keys: dict[str, Ed25519PrivateKey] = {}
        self._hmac_keys: dict[str, bytes] = {}

    # -- key material (lazily created, reused) -------------------------------

    def _aes_key_for(self, key_id: str) -> bytes:
        key = self._aes_keys.get(key_id)
        if key is None:
            key = AESGCM.generate_key(bit_length=_AES_KEY_BYTES * 8)
            self._aes_keys[key_id] = key
        return key

    def _sign_key_for(self, key_id: str) -> Ed25519PrivateKey:
        key = self._sign_keys.get(key_id)
        if key is None:
            key = Ed25519PrivateKey.generate()
            self._sign_keys[key_id] = key
        return key

    def _hmac_key_for(self, key_id: str) -> bytes:
        key = self._hmac_keys.get(key_id)
        if key is None:
            key = os.urandom(_HMAC_KEY_BYTES)
            self._hmac_keys[key_id] = key
        return key

    # -- AES-GCM --------------------------------------------------------------

    def encrypt_aes(self, plaintext: bytes, key_id: str) -> bytes:
        try:
            key = self._aes_key_for(key_id)
            nonce = os.urandom(_GCM_NONCE_BYTES)
            ciphertext = AESGCM(key).encrypt(nonce, plaintext, None)
            return nonce + ciphertext
        except Exception as exc:  # pragma: no cover - defensive
            raise CryptoError("encrypt_aes failed") from exc

    def decrypt_aes(self, ciphertext: bytes, key_id: str) -> bytes:
        try:
            if len(ciphertext) < _GCM_NONCE_BYTES:
                raise ValueError("ciphertext too short to contain a nonce")
            key = self._aes_key_for(key_id)
            nonce, actual_ciphertext = (
                ciphertext[:_GCM_NONCE_BYTES],
                ciphertext[_GCM_NONCE_BYTES:],
            )
            return AESGCM(key).decrypt(nonce, actual_ciphertext, None)
        except CryptoError:
            raise
        except Exception as exc:
            raise CryptoError("decrypt_aes failed") from exc

    # -- sign / verify ---------------------------------------------------------

    def sign(self, data: bytes, key_id: str) -> bytes:
        try:
            key = self._sign_key_for(key_id)
            return key.sign(data)
        except Exception as exc:  # pragma: no cover - defensive
            raise CryptoError("sign failed") from exc

    def verify(self, data: bytes, signature: bytes, key_id: str) -> bool:
        key = self._sign_key_for(key_id)
        public_key: Ed25519PublicKey = key.public_key()
        try:
            public_key.verify(signature, data)
            return True
        except InvalidSignature:
            return False
        except Exception as exc:  # pragma: no cover - defensive
            raise CryptoError("verify failed") from exc

    # -- hash / hmac -------------------------------------------------------

    def hash(self, data: bytes, algo: HashAlgo) -> bytes:
        try:
            algo_cls = _HASH_ALGO_MAP[algo]
        except KeyError as exc:
            raise CryptoError(f"unsupported hash algorithm: {algo!r}") from exc
        try:
            digest = hashes.Hash(algo_cls())
            digest.update(data)
            return digest.finalize()
        except Exception as exc:  # pragma: no cover - defensive
            raise CryptoError("hash failed") from exc

    def hmac(self, data: bytes, key_id: str) -> bytes:
        try:
            key = self._hmac_key_for(key_id)
            return hmac_module.new(key, data, "sha256").digest()
        except Exception as exc:  # pragma: no cover - defensive
            raise CryptoError("hmac failed") from exc
