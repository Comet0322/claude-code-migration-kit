"""Tests for CertManager. See boogie-sdk-api.md (this skill's library doc) section 5.1.

The design doc only pins down the method signatures:

    load_cert(path: Path) -> Certificate
    get_expiry_date(cert_id: str) -> datetime
    is_rotation_due(cert_id: str) -> bool

`load_cert` takes only a filesystem path (real PEM-encoded X.509 data, since
this module is implemented with real crypto primitives), so `Certificate.
cert_id` must be *derived* by the implementation from the certificate itself
(e.g. a fingerprint or serial number) rather than supplied by the caller.
These tests treat cert_id as opaque and only assert:

- it is a non-empty string,
- it is stable across repeated loads of the same certificate file,
- it can be used to look up the expiry date / rotation status afterwards.

Rotation-due convention: this suite does not pin an exact "days before
expiry" threshold (that's an implementation choice). It only asserts the two
unambiguous ends of the spectrum: an already-expired certificate must always
be reported as rotation-due, and a certificate expiring far in the future
(2 years out) must never be, for any reasonable threshold.
"""

from __future__ import annotations

import datetime
from pathlib import Path

import pytest
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.x509.oid import NameOID

from boogie_sdk.core.errors import NotFoundError
from boogie_sdk.crypto.cert_manager import CertManager, Certificate


def _self_signed_pem(
    common_name: str,
    not_before: datetime.datetime,
    not_after: datetime.datetime,
) -> bytes:
    key = ec.generate_private_key(ec.SECP256R1())
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, common_name)])
    cert = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(not_before)
        .not_valid_after(not_after)
        .sign(key, hashes.SHA256())
    )
    return cert.public_bytes(encoding=serialization.Encoding.PEM)


def _as_utc_naive(dt: datetime.datetime) -> datetime.datetime:
    if dt.tzinfo is not None:
        return dt.astimezone(datetime.timezone.utc).replace(tzinfo=None)
    return dt


@pytest.fixture
def manager() -> CertManager:
    return CertManager()


@pytest.fixture
def valid_cert_path(tmp_path: Path) -> Path:
    now = datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0)
    pem = _self_signed_pem(
        "valid.example.com",
        now - datetime.timedelta(days=1),
        now + datetime.timedelta(days=730),  # expires 2 years out
    )
    path = tmp_path / "valid.pem"
    path.write_bytes(pem)
    return path


@pytest.fixture
def expired_cert_path(tmp_path: Path) -> Path:
    now = datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0)
    pem = _self_signed_pem(
        "expired.example.com",
        now - datetime.timedelta(days=730),
        now - datetime.timedelta(days=1),  # expired yesterday
    )
    path = tmp_path / "expired.pem"
    path.write_bytes(pem)
    return path


def test_load_cert_returns_certificate_with_subject_and_expiry(
    manager: CertManager, valid_cert_path: Path
) -> None:
    now = datetime.datetime.now(datetime.timezone.utc)

    cert = manager.load_cert(valid_cert_path)

    assert isinstance(cert, Certificate)
    assert isinstance(cert.cert_id, str) and cert.cert_id != ""
    assert "valid.example.com" in cert.subject
    assert _as_utc_naive(cert.expires_at) > _as_utc_naive(now)


def test_load_cert_is_idempotent_for_same_file(
    manager: CertManager, valid_cert_path: Path
) -> None:
    first = manager.load_cert(valid_cert_path)
    second = manager.load_cert(valid_cert_path)

    assert first.cert_id == second.cert_id
    assert _as_utc_naive(first.expires_at) == _as_utc_naive(second.expires_at)


def test_load_cert_different_files_get_different_cert_ids(
    manager: CertManager, valid_cert_path: Path, expired_cert_path: Path
) -> None:
    valid = manager.load_cert(valid_cert_path)
    expired = manager.load_cert(expired_cert_path)

    assert valid.cert_id != expired.cert_id


def test_get_expiry_date_matches_loaded_certificate(
    manager: CertManager, valid_cert_path: Path
) -> None:
    cert = manager.load_cert(valid_cert_path)

    expiry = manager.get_expiry_date(cert.cert_id)

    assert _as_utc_naive(expiry) == _as_utc_naive(cert.expires_at)


def test_get_expiry_date_for_unknown_cert_id_raises_not_found_error(
    manager: CertManager,
) -> None:
    with pytest.raises(NotFoundError):
        manager.get_expiry_date("no-such-cert-id")


def test_is_rotation_due_false_for_far_future_expiry(
    manager: CertManager, valid_cert_path: Path
) -> None:
    cert = manager.load_cert(valid_cert_path)

    assert manager.is_rotation_due(cert.cert_id) is False


def test_is_rotation_due_true_for_already_expired_certificate(
    manager: CertManager, expired_cert_path: Path
) -> None:
    cert = manager.load_cert(expired_cert_path)

    assert manager.is_rotation_due(cert.cert_id) is True


def test_is_rotation_due_for_unknown_cert_id_raises_not_found_error(
    manager: CertManager,
) -> None:
    with pytest.raises(NotFoundError):
        manager.is_rotation_due("no-such-cert-id")
