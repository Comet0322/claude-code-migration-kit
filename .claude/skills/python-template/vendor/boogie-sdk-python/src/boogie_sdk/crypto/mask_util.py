"""mask_util: module-level masking helpers. See boogie-sdk-api.md section 5.1 (crypto).

Masking conventions (pinned down by tests/crypto/test_mask_util.py, since the
design doc only gives the signatures):

- ``mask_phone``: TW mobile numbers, 10 digits. Keep the first 4 and last 3
  digits visible, mask the middle 3 with literal ``*``.
- ``mask_id_number``: TW national ID, 10 chars (1 letter + 9 digits). Keep the
  first character and the last 3 digits visible, mask the middle 6.
- ``mask_card_number``: 16-digit card numbers. PCI-style convention: only the
  last 4 digits are ever revealed, everything before them is masked.

All three functions preserve the input length (masked characters are ``*``).
"""

from __future__ import annotations


def mask_id_number(id_no: str) -> str:
    return id_no[0] + "*" * 6 + id_no[-3:]


def mask_phone(phone: str) -> str:
    return phone[:4] + "*" * 3 + phone[-3:]


def mask_card_number(card: str) -> str:
    if len(card) <= 4:
        # Too short to safely reveal a trailing 4-digit suffix without
        # exposing the whole number; mask it entirely instead.
        return "*" * len(card)
    return "*" * (len(card) - 4) + card[-4:]
