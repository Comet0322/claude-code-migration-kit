package com.boogie.sdk.crypto;

import com.boogie.sdk.core.CryptoException;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.util.HexFormat;

import static org.junit.jupiter.api.Assertions.assertArrayEquals;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNotEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

/**
 * Tests for CryptoClient. See boogie-sdk-api.md section 5.1 (crypto).
 *
 * CryptoClient is implemented with real crypto primitives (AES-GCM via
 * javax.crypto.Cipher, SHA-256/SHA-512 via java.security.MessageDigest,
 * HMAC-SHA256 via javax.crypto.Mac, and a real asymmetric sign/verify
 * scheme), not a fake. Key material is simulated in-memory and keyed off an
 * opaque `keyId` string: the client is expected to lazily create the key
 * material the first time a given keyId is used and reuse that same key
 * material for that keyId on later calls, within the same CryptoClient
 * instance.
 */
class CryptoClientTest {

    // Well-known reference digests -- also catches an incorrect algorithm
    // choice (e.g. accidentally hashing with MD5, or truncating SHA-512).
    private static final String SHA256_EMPTY =
            "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855";
    private static final String SHA256_ABC =
            "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad";
    private static final String SHA512_ABC =
            "ddaf35a193617abacc417349ae20413112e6fa4e89a97ea20a9eeee64b55d39"
                    + "a2192992a274fc1a836ba3c23a3feebbd454d4423643ce80e2a9ac94fa54ca49f";

    private CryptoClient client;

    @BeforeEach
    void setUp() {
        client = new CryptoClient();
    }

    // -- encryptAes / decryptAes ---------------------------------------

    @Test
    void encryptAesOutputDiffersFromPlaintext() {
        byte[] plaintext = "top secret payload".getBytes();
        byte[] ciphertext = client.encryptAes(plaintext, "k1");

        assertNotEquals(new String(ciphertext), new String(plaintext));
        assertFalse(indexOf(ciphertext, plaintext) >= 0, "ciphertext must not contain the raw plaintext");
    }

    @Test
    void encryptAesIsNondeterministicForSamePlaintextAndKey() {
        byte[] plaintext = "same message every time".getBytes();

        byte[] first = client.encryptAes(plaintext, "k1");
        byte[] second = client.encryptAes(plaintext, "k1");

        // A correct AES-GCM implementation uses a fresh random nonce/IV per
        // call, so two encryptions of the same plaintext under the same key
        // must not produce identical ciphertext.
        assertFalse(java.util.Arrays.equals(first, second));
    }

    @Test
    void encryptDecryptRoundTrip() {
        byte[] plaintext = "round trip me".getBytes();
        byte[] ciphertext = client.encryptAes(plaintext, "k1");

        assertArrayEquals(plaintext, client.decryptAes(ciphertext, "k1"));
    }

    @Test
    void encryptDecryptRoundTripEmptyPlaintext() {
        byte[] ciphertext = client.encryptAes(new byte[0], "k1");

        assertArrayEquals(new byte[0], client.decryptAes(ciphertext, "k1"));
    }

    @Test
    void keyIdIsLazilyCreatedAndReused() {
        // A brand-new keyId should just work (no explicit key material
        // passed in, no pre-registration step) and the same keyId should
        // decrypt what it encrypted.
        byte[] ciphertext = client.encryptAes("hello".getBytes(), "brand-new-key-id");
        assertArrayEquals("hello".getBytes(), client.decryptAes(ciphertext, "brand-new-key-id"));

        // Using the keyId again later still reuses the same underlying key.
        byte[] ciphertext2 = client.encryptAes("hello again".getBytes(), "brand-new-key-id");
        assertArrayEquals("hello again".getBytes(), client.decryptAes(ciphertext2, "brand-new-key-id"));
    }

    @Test
    void decryptWithWrongKeyIdRaisesCryptoException() {
        byte[] ciphertext = client.encryptAes("secret".getBytes(), "key-a");

        assertThrows(CryptoException.class, () -> client.decryptAes(ciphertext, "key-b"));
    }

    @Test
    void decryptWithCorruptedCiphertextRaisesCryptoException() {
        byte[] ciphertext = client.encryptAes("secret payload".getBytes(), "k1");
        byte[] corrupted = ciphertext.clone();
        corrupted[corrupted.length - 1] ^= 0xFF; // flip the last byte (breaks the GCM auth tag)

        assertThrows(CryptoException.class, () -> client.decryptAes(corrupted, "k1"));
    }

    @Test
    void decryptNeverLeaksRawCryptographyException() {
        byte[] ciphertext = client.encryptAes("secret payload".getBytes(), "k1");
        byte[] truncated = java.util.Arrays.copyOf(ciphertext, ciphertext.length - 1);

        try {
            client.decryptAes(truncated, "k1");
            org.junit.jupiter.api.Assertions.fail("expected decryptAes to raise for truncated ciphertext");
        } catch (CryptoException expected) {
            // ok
        } catch (Exception unexpected) {
            org.junit.jupiter.api.Assertions.fail(
                    "decryptAes must wrap low-level crypto errors in CryptoException, but raised "
                            + unexpected.getClass().getName() + " instead");
        }
    }

    // -- sign / verify ---------------------------------------------------

    @Test
    void signReturnsNonEmptyBytes() {
        byte[] signature = client.sign("data to sign".getBytes(), "sign-key");
        assertTrue(signature.length > 0);
    }

    @Test
    void signVerifyRoundTrip() {
        byte[] data = "important message".getBytes();
        byte[] signature = client.sign(data, "sign-key");

        assertTrue(client.verify(data, signature, "sign-key"));
    }

    @Test
    void verifyTamperedDataReturnsFalse() {
        byte[] data = "important message".getBytes();
        byte[] signature = client.sign(data, "sign-key");

        assertFalse(client.verify("important MESSAGE".getBytes(), signature, "sign-key"));
    }

    @Test
    void verifyTamperedSignatureReturnsFalse() {
        byte[] data = "important message".getBytes();
        byte[] signature = client.sign(data, "sign-key").clone();
        signature[0] ^= 0xFF;

        assertFalse(client.verify(data, signature, "sign-key"));
    }

    @Test
    void verifyWithWrongKeyIdReturnsFalse() {
        byte[] data = "important message".getBytes();
        byte[] signature = client.sign(data, "key-a");

        assertFalse(client.verify(data, signature, "key-b"));
    }

    @Test
    void signKeyIdIsLazilyCreatedAndReused() {
        byte[] data = "payload".getBytes();
        byte[] signature1 = client.sign(data, "fresh-sign-key");
        byte[] signature2 = client.sign(data, "fresh-sign-key");

        // Same key reused -> both signatures verify against the same keyId.
        assertTrue(client.verify(data, signature1, "fresh-sign-key"));
        assertTrue(client.verify(data, signature2, "fresh-sign-key"));
    }

    // -- hash --------------------------------------------------------------

    @Test
    void hashSha256MatchesKnownVectorForEmptyInput() {
        byte[] digest = client.hash(new byte[0], HashAlgo.SHA256);
        assertEquals(SHA256_EMPTY, HexFormat.of().formatHex(digest));
    }

    @Test
    void hashSha256MatchesKnownVectorForAbc() {
        byte[] digest = client.hash("abc".getBytes(), HashAlgo.SHA256);
        assertEquals(SHA256_ABC, HexFormat.of().formatHex(digest));
    }

    @Test
    void hashSha512MatchesKnownVectorForAbc() {
        byte[] digest = client.hash("abc".getBytes(), HashAlgo.SHA512);
        assertEquals(SHA512_ABC, HexFormat.of().formatHex(digest));
    }

    @Test
    void hashIsDeterministic() {
        assertArrayEquals(
                client.hash("repeat me".getBytes(), HashAlgo.SHA256),
                client.hash("repeat me".getBytes(), HashAlgo.SHA256));
    }

    @Test
    void hashDiffersBetweenAlgorithms() {
        assertFalse(java.util.Arrays.equals(
                client.hash("abc".getBytes(), HashAlgo.SHA256),
                client.hash("abc".getBytes(), HashAlgo.SHA512)));
    }

    // -- hmac ----------------------------------------------------------

    @Test
    void hmacReturnsNonEmptyBytes() {
        byte[] mac = client.hmac("message".getBytes(), "hmac-key");
        assertTrue(mac.length > 0);
    }

    @Test
    void hmacIsDeterministicForSameKeyAndData() {
        byte[] mac1 = client.hmac("message".getBytes(), "hmac-key");
        byte[] mac2 = client.hmac("message".getBytes(), "hmac-key");
        assertArrayEquals(mac1, mac2);
    }

    @Test
    void hmacDiffersForDifferentData() {
        byte[] mac1 = client.hmac("message one".getBytes(), "hmac-key");
        byte[] mac2 = client.hmac("message two".getBytes(), "hmac-key");
        assertFalse(java.util.Arrays.equals(mac1, mac2));
    }

    @Test
    void hmacDiffersForDifferentKeyId() {
        byte[] mac1 = client.hmac("message".getBytes(), "hmac-key-a");
        byte[] mac2 = client.hmac("message".getBytes(), "hmac-key-b");
        assertFalse(java.util.Arrays.equals(mac1, mac2));
    }

    private static int indexOf(byte[] haystack, byte[] needle) {
        if (needle.length == 0) {
            return 0;
        }
        outer:
        for (int i = 0; i <= haystack.length - needle.length; i++) {
            for (int j = 0; j < needle.length; j++) {
                if (haystack[i + j] != needle[j]) {
                    continue outer;
                }
            }
            return i;
        }
        return -1;
    }
}
