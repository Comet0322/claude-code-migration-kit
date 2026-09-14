"""Tests for mask_util. See boogie-sdk-api.md (this skill's library doc) section 5.1.

The design doc only gives the function signatures (mask_id_number, mask_phone,
mask_card_number all take and return `str`); the exact masking convention is
not specified there, so this test file is the source of truth for it. Picked
conventions (output length always equals input length; masked characters are
literal `*`):

- `mask_phone`: TW mobile numbers, 10 digits. Keep the first 4 and last 3
  digits visible, mask the middle 3: "0912345678" -> "0912***678".
- `mask_id_number`: TW national ID, 10 chars (1 letter + 9 digits). Keep the
  first character and the last 3 digits visible, mask the middle 6:
  "A123456789" -> "A******789".
- `mask_card_number`: 16-digit card numbers. Follow the common PCI-style
  convention of only ever revealing the last 4 digits, masking everything
  before them: "4111111111111111" -> "************1111".
"""

from __future__ import annotations

from boogie_sdk.crypto.mask_util import mask_card_number, mask_id_number, mask_phone


# -- mask_phone ---------------------------------------------------------


def test_mask_phone_keeps_first_4_and_last_3_digits() -> None:
    assert mask_phone("0912345678") == "0912***678"


def test_mask_phone_generalizes_across_numbers() -> None:
    assert mask_phone("0987654321") == "0987***321"


def test_mask_phone_preserves_length() -> None:
    phone = "0912345678"
    assert len(mask_phone(phone)) == len(phone)


def test_mask_phone_never_reveals_masked_digits() -> None:
    masked = mask_phone("0912345678")
    assert masked[4:7] == "***"


# -- mask_id_number -------------------------------------------------------


def test_mask_id_number_keeps_first_char_and_last_3_digits() -> None:
    assert mask_id_number("A123456789") == "A******789"


def test_mask_id_number_generalizes_across_ids() -> None:
    assert mask_id_number("B234567890") == "B******890"


def test_mask_id_number_preserves_length() -> None:
    id_no = "A123456789"
    assert len(mask_id_number(id_no)) == len(id_no)


# -- mask_card_number -------------------------------------------------------


def test_mask_card_number_reveals_only_last_4_digits() -> None:
    assert mask_card_number("4111111111111111") == "************1111"


def test_mask_card_number_generalizes_across_numbers() -> None:
    assert mask_card_number("5500005555555559") == "************5559"


def test_mask_card_number_preserves_length() -> None:
    card = "4111111111111111"
    assert len(mask_card_number(card)) == len(card)


def test_mask_card_number_does_not_reveal_any_of_the_first_12_digits() -> None:
    masked = mask_card_number("4111111111111111")
    assert masked[:12] == "*" * 12
