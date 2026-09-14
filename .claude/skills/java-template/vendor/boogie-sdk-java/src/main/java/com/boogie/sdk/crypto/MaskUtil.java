package com.boogie.sdk.crypto;

/**
 * MaskUtil. See boogie-sdk-api.md section 5.1 (crypto).
 *
 * Masking conventions (output length always equals input length; masked
 * characters are literal '*'), as pinned down by MaskUtilTest:
 * - maskPhone: keep the first 4 and last 3 characters visible, mask the rest.
 * - maskIdNumber: keep the first character and the last 3 characters
 *   visible, mask the rest.
 * - maskCardNumber: keep only the last 4 characters visible, mask the rest.
 *
 * Defensive fallback: if an input is too short to have both a visible
 * prefix and suffix without overlapping, the whole string is masked (still
 * preserving length) instead of throwing.
 */
public final class MaskUtil {
    private MaskUtil() {
    }

    public static String maskIdNumber(String id) {
        return maskMiddle(id, 1, 3);
    }

    public static String maskPhone(String phone) {
        return maskMiddle(phone, 4, 3);
    }

    public static String maskCardNumber(String card) {
        return maskMiddle(card, 0, 4);
    }

    private static String maskMiddle(String value, int keepStart, int keepEnd) {
        int length = value.length();
        if (length <= keepStart + keepEnd) {
            // Too short to reveal both ends without overlap -- mask
            // everything rather than let substring() throw.
            return "*".repeat(length);
        }
        int maskedLength = length - keepStart - keepEnd;
        return value.substring(0, keepStart)
                + "*".repeat(maskedLength)
                + value.substring(length - keepEnd);
    }
}
