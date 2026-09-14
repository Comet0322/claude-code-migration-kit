package com.boogie.sdk.crypto;

import com.boogie.sdk.core.CryptoException;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.time.Instant;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.fail;

/**
 * Tests for TokenClient. See boogie-sdk-api.md section 5.1 (crypto).
 *
 * issueToken/verifyToken's exact wire format is not pinned down by the
 * design doc beyond the method signatures, so this test file documents the
 * conventions it expects the implementation to follow (the implementer must
 * satisfy these -- they are the source of truth):
 *
 * - issueToken(claims) returns an opaque String token that embeds the given
 *   claims plus a tamper-evident signature (JWT-like: e.g. HMAC-signed
 *   base64url header/payload/signature).
 * - verifyToken(token) returns a Claims whose values() equals the claims
 *   map that was originally issued, when the token is untouched.
 * - Expiration convention (JWT-style "exp" claim): if the issued claims map
 *   includes an "exp" key, its value is a Unix timestamp in seconds
 *   (a Long, though a plain Integer must also be accepted) -- NOT
 *   milliseconds. verifyToken must treat the token as expired, and raise
 *   CryptoException, once exp is at or before the current time.
 * - A tampered token (any character flipped) or a structurally invalid
 *   token string passed to verifyToken raises CryptoException rather than
 *   returning garbage or leaking a lower-level parsing/JSON exception.
 */
class TokenClientTest {

    private TokenClient client;

    @BeforeEach
    void setUp() {
        client = new TokenClient();
    }

    @Test
    void issueTokenReturnsNonEmptyString() {
        String token = client.issueToken(Map.of("sub", "user-1"));
        assertNotEquals("", token);
    }

    @Test
    void issueThenVerifyRoundTrip() {
        Map<String, Object> claimsIn = Map.of("sub", "user-1", "role", "admin");
        String token = client.issueToken(claimsIn);

        Claims claimsOut = client.verifyToken(token);

        assertEquals(claimsIn, claimsOut.values());
    }

    @Test
    void verifyTokenWithFutureExpirySucceeds() {
        Map<String, Object> claimsIn = Map.of(
                "sub", "user-1",
                "exp", Instant.now().getEpochSecond() + 3600L);
        String token = client.issueToken(claimsIn);

        Claims claimsOut = client.verifyToken(token);

        assertEquals("user-1", claimsOut.values().get("sub"));
    }

    @Test
    void verifyExpiredTokenRaisesCryptoException() {
        Map<String, Object> claimsIn = Map.of(
                "sub", "user-1",
                "exp", Instant.now().getEpochSecond() - 3600L);
        String token = client.issueToken(claimsIn);

        assertThrows(CryptoException.class, () -> client.verifyToken(token));
    }

    @Test
    void verifyTamperedTokenRaisesCryptoException() {
        String token = client.issueToken(Map.of("sub", "user-1"));

        // Flip a character in the middle of the token (not the last character
        // of any base64url component) to corrupt the signature/payload. The
        // last character of a base64url(no-pad) group can carry unused
        // padding bits that a naive decoder ignores, so tampering it has a
        // small chance of decoding back to the same bytes -- a middle
        // character always changes a full 6-bit group and can't collide.
        int index = token.length() / 2;
        char original = token.charAt(index);
        char replacement = original != 'a' ? 'a' : 'b';
        String tampered = token.substring(0, index) + replacement + token.substring(index + 1);

        assertThrows(CryptoException.class, () -> client.verifyToken(tampered));
    }

    @Test
    void verifyStructurallyInvalidTokenRaisesCryptoException() {
        assertThrows(CryptoException.class, () -> client.verifyToken("not-a-real-token"));
    }

    @Test
    void verifyNeverLeaksRawLowerLevelException() {
        try {
            client.verifyToken("###garbage###");
            fail("expected verifyToken to raise for garbage input");
        } catch (CryptoException expected) {
            // ok
        } catch (Exception unexpected) {
            fail("verifyToken must wrap low-level errors in CryptoException, but raised "
                    + unexpected.getClass().getName() + " instead");
        }
    }
}
