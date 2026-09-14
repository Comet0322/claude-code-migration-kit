"""CertManager stub. See boogie-sdk-api.md (this skill's library doc) section 5.1 (crypto).

Real X.509 parsing via the `cryptography` package. `cert_id` is derived from
the certificate itself (a SHA-256 fingerprint of the DER-encoded cert), not
supplied by the caller, so loading the same file twice yields the same
`cert_id` and loading different certificates yields different ids. Parsed
certificates are cached in-memory by `cert_id` so `get_expiry_date` /
`is_rotation_due` can look them up afterwards -- this is the simulated
"certificate store" for this training fake.
"""

from __future__ import annotations

import datetime
from dataclasses import dataclass
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.primitives import hashes

from boogie_sdk.core.errors import CryptoError, NotFoundError

# Rotation-due threshold: a certificate expiring within this many days (or
# already expired) is considered due for rotation. The design doc and tests
# don't pin an exact value -- only that an already-expired cert is always
# due, and one expiring 2 years out never is -- so a conventional 30-day
# window is used here.
_ROTATION_DUE_WINDOW = datetime.timedelta(days=30)


@dataclass(frozen=True)
class Certificate:
    cert_id: str
    subject: str
    expires_at: datetime.datetime


class CertManager:
    def __init__(self) -> None:
        self._certs: dict[str, Certificate] = {}

    def load_cert(self, path: Path) -> Certificate:
        try:
            pem_bytes = Path(path).read_bytes()
            cert = x509.load_pem_x509_certificate(pem_bytes)
            cert_id = cert.fingerprint(hashes.SHA256()).hex()
            subject = cert.subject.rfc4514_string()
            expires_at = cert.not_valid_after_utc.replace(tzinfo=None)
        except CryptoError:
            raise
        except Exception as exc:
            raise CryptoError(f"failed to load certificate from {path!r}") from exc

        certificate = Certificate(
            cert_id=cert_id, subject=subject, expires_at=expires_at
        )
        self._certs[cert_id] = certificate
        return certificate

    def _get(self, cert_id: str) -> Certificate:
        try:
            return self._certs[cert_id]
        except KeyError as exc:
            raise NotFoundError(f"no certificate registered for id: {cert_id!r}") from exc

    def get_expiry_date(self, cert_id: str) -> datetime.datetime:
        return self._get(cert_id).expires_at

    def is_rotation_due(self, cert_id: str) -> bool:
        expires_at = self._get(cert_id).expires_at
        now = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
        return expires_at - now <= _ROTATION_DUE_WINDOW
