package com.boogie.sdk.crypto;

import com.boogie.sdk.core.CryptoException;

import javax.crypto.Cipher;
import javax.crypto.KeyGenerator;
import javax.crypto.Mac;
import javax.crypto.SecretKey;
import javax.crypto.spec.GCMParameterSpec;
import java.security.GeneralSecurityException;
import java.security.KeyPair;
import java.security.KeyPairGenerator;
import java.security.SecureRandom;
import java.security.Signature;
import java.util.Arrays;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

/**
 * CryptoClient. See boogie-sdk-api.md section 5.1 (crypto).
 *
 * "Key management" is simulated in-memory: each instance keeps private maps
 * from opaque keyId -> real key material, lazily generated on first use and
 * reused thereafter for that keyId.
 */
public class CryptoClient {

    private static final int GCM_IV_LENGTH_BYTES = 12;
    private static final int GCM_TAG_LENGTH_BITS = 128;

    private final Map<String, SecretKey> aesKeys = new ConcurrentHashMap<>();
    private final Map<String, SecretKey> hmacKeys = new ConcurrentHashMap<>();
    private final Map<String, KeyPair> signKeys = new ConcurrentHashMap<>();
    private final SecureRandom random = new SecureRandom();

    public byte[] encryptAes(byte[] plaintext, String keyId) {
        try {
            SecretKey key = aesKeys.computeIfAbsent(keyId, id -> generateAesKey());
            byte[] iv = new byte[GCM_IV_LENGTH_BYTES];
            random.nextBytes(iv);

            Cipher cipher = Cipher.getInstance("AES/GCM/NoPadding");
            cipher.init(Cipher.ENCRYPT_MODE, key, new GCMParameterSpec(GCM_TAG_LENGTH_BITS, iv));
            byte[] encrypted = cipher.doFinal(plaintext);

            byte[] out = new byte[iv.length + encrypted.length];
            System.arraycopy(iv, 0, out, 0, iv.length);
            System.arraycopy(encrypted, 0, out, iv.length, encrypted.length);
            return out;
        } catch (CryptoException e) {
            throw e;
        } catch (Exception e) {
            throw new CryptoException("AES encryption failed", e);
        }
    }

    public byte[] decryptAes(byte[] ciphertext, String keyId) {
        try {
            if (ciphertext == null || ciphertext.length < GCM_IV_LENGTH_BYTES) {
                throw new CryptoException("ciphertext too short to contain an IV");
            }
            SecretKey key = aesKeys.computeIfAbsent(keyId, id -> generateAesKey());
            byte[] iv = Arrays.copyOfRange(ciphertext, 0, GCM_IV_LENGTH_BYTES);
            byte[] encrypted = Arrays.copyOfRange(ciphertext, GCM_IV_LENGTH_BYTES, ciphertext.length);

            Cipher cipher = Cipher.getInstance("AES/GCM/NoPadding");
            cipher.init(Cipher.DECRYPT_MODE, key, new GCMParameterSpec(GCM_TAG_LENGTH_BITS, iv));
            return cipher.doFinal(encrypted);
        } catch (CryptoException e) {
            throw e;
        } catch (Exception e) {
            throw new CryptoException("AES decryption failed", e);
        }
    }

    public byte[] sign(byte[] data, String keyId) {
        try {
            KeyPair keyPair = signKeys.computeIfAbsent(keyId, id -> generateSignKeyPair());
            Signature signature = Signature.getInstance("Ed25519");
            signature.initSign(keyPair.getPrivate());
            signature.update(data);
            return signature.sign();
        } catch (Exception e) {
            throw new CryptoException("signing failed", e);
        }
    }

    public boolean verify(byte[] data, byte[] signature, String keyId) {
        try {
            KeyPair keyPair = signKeys.computeIfAbsent(keyId, id -> generateSignKeyPair());
            Signature verifier = Signature.getInstance("Ed25519");
            verifier.initVerify(keyPair.getPublic());
            verifier.update(data);
            return verifier.verify(signature);
        } catch (Exception e) {
            // A malformed/tampered signature or mismatched key is an expected
            // "not valid" outcome, not an internal error -- report false
            // rather than throwing.
            return false;
        }
    }

    public byte[] hash(byte[] data, HashAlgo algo) {
        try {
            String algorithm = switch (algo) {
                case SHA256 -> "SHA-256";
                case SHA512 -> "SHA-512";
            };
            return java.security.MessageDigest.getInstance(algorithm).digest(data);
        } catch (GeneralSecurityException e) {
            throw new CryptoException("hashing failed", e);
        }
    }

    public byte[] hmac(byte[] data, String keyId) {
        try {
            SecretKey key = hmacKeys.computeIfAbsent(keyId, id -> generateHmacKey());
            Mac mac = Mac.getInstance("HmacSHA256");
            mac.init(key);
            return mac.doFinal(data);
        } catch (Exception e) {
            throw new CryptoException("hmac failed", e);
        }
    }

    private static SecretKey generateAesKey() {
        try {
            KeyGenerator generator = KeyGenerator.getInstance("AES");
            generator.init(256);
            return generator.generateKey();
        } catch (GeneralSecurityException e) {
            throw new CryptoException("failed to generate AES key material", e);
        }
    }

    private static SecretKey generateHmacKey() {
        try {
            KeyGenerator generator = KeyGenerator.getInstance("HmacSHA256");
            return generator.generateKey();
        } catch (GeneralSecurityException e) {
            throw new CryptoException("failed to generate HMAC key material", e);
        }
    }

    private static KeyPair generateSignKeyPair() {
        try {
            KeyPairGenerator generator = KeyPairGenerator.getInstance("Ed25519");
            return generator.generateKeyPair();
        } catch (GeneralSecurityException e) {
            throw new CryptoException("failed to generate signing key material", e);
        }
    }
}
