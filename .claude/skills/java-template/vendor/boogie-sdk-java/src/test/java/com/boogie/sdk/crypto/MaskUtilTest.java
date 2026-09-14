package com.boogie.sdk.crypto;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertEquals;

/**
 * Tests for MaskUtil. See boogie-sdk-api.md section 5.1 (crypto).
 *
 * The design doc only gives the method signatures (maskIdNumber, maskPhone,
 * maskCardNumber all take and return String); the exact masking convention
 * is not specified there, so this test file is the source of truth for it.
 * Picked conventions (output length always equals input length; masked
 * characters are literal '*'):
 *
 * - maskPhone: TW mobile numbers, 10 digits. Keep the first 4 and last 3
 *   digits visible, mask the middle 3: "0912345678" -> "0912***678".
 * - maskIdNumber: TW national ID, 10 chars (1 letter + 9 digits). Keep the
 *   first character and the last 3 digits visible, mask the middle 6:
 *   "A123456789" -> "A******789".
 * - maskCardNumber: 16-digit card numbers. Follow the common PCI-style
 *   convention of only ever revealing the last 4 digits, masking everything
 *   before them: "4111111111111111" -> "************1111".
 */
class MaskUtilTest {

    // -- maskPhone -----------------------------------------------------

    @Test
    void maskPhoneKeepsFirst4AndLast3Digits() {
        assertEquals("0912***678", MaskUtil.maskPhone("0912345678"));
    }

    @Test
    void maskPhoneGeneralizesAcrossNumbers() {
        assertEquals("0987***321", MaskUtil.maskPhone("0987654321"));
    }

    @Test
    void maskPhonePreservesLength() {
        String phone = "0912345678";
        assertEquals(phone.length(), MaskUtil.maskPhone(phone).length());
    }

    @Test
    void maskPhoneNeverRevealsMaskedDigits() {
        String masked = MaskUtil.maskPhone("0912345678");
        assertEquals("***", masked.substring(4, 7));
    }

    // -- maskIdNumber --------------------------------------------------

    @Test
    void maskIdNumberKeepsFirstCharAndLast3Digits() {
        assertEquals("A******789", MaskUtil.maskIdNumber("A123456789"));
    }

    @Test
    void maskIdNumberGeneralizesAcrossIds() {
        assertEquals("B******890", MaskUtil.maskIdNumber("B234567890"));
    }

    @Test
    void maskIdNumberPreservesLength() {
        String id = "A123456789";
        assertEquals(id.length(), MaskUtil.maskIdNumber(id).length());
    }

    // -- maskCardNumber --------------------------------------------------

    @Test
    void maskCardNumberRevealsOnlyLast4Digits() {
        assertEquals("************1111", MaskUtil.maskCardNumber("4111111111111111"));
    }

    @Test
    void maskCardNumberGeneralizesAcrossNumbers() {
        assertEquals("************5559", MaskUtil.maskCardNumber("5500005555555559"));
    }

    @Test
    void maskCardNumberPreservesLength() {
        String card = "4111111111111111";
        assertEquals(card.length(), MaskUtil.maskCardNumber(card).length());
    }

    @Test
    void maskCardNumberDoesNotRevealAnyOfTheFirst12Digits() {
        String masked = MaskUtil.maskCardNumber("4111111111111111");
        assertEquals("*".repeat(12), masked.substring(0, 12));
    }
}
