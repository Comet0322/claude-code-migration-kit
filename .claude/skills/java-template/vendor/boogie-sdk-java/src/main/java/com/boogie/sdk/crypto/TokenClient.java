package com.boogie.sdk.crypto;

import com.boogie.sdk.core.CryptoException;

import javax.crypto.KeyGenerator;
import javax.crypto.Mac;
import javax.crypto.SecretKey;
import java.nio.charset.StandardCharsets;
import java.security.GeneralSecurityException;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.time.Instant;
import java.util.Base64;
import java.util.LinkedHashMap;
import java.util.Map;

/**
 * TokenClient. See boogie-sdk-api.md section 5.1 (crypto).
 *
 * JWT-like, HMAC-signed opaque token: base64url(header) + "." +
 * base64url(payload) + "." + base64url(signature), where the signature is
 * HmacSHA256 over "header.payload" using a key private to this client
 * instance.
 *
 * The payload carries the claims map encoded with a small hand-rolled,
 * line-oriented text format (deliberately NOT Java object serialization --
 * {@code ObjectInputStream.readObject()} is a dangerous pattern to
 * demonstrate even where it happens to be safe, and there is no JSON library
 * available as a dependency here). Each claim is one line of
 * {@code key\ttype\tvalue}, with '\\', tab and newline backslash-escaped
 * inside the key/value text; supported value types are {@code String},
 * {@code Long}, {@code Integer}, and {@code Boolean} (the ones the crypto
 * test suite actually exercises).
 *
 * verifyToken always checks the HMAC signature over the raw
 * header/payload bytes BEFORE decoding the payload -- the decoder never runs
 * on unauthenticated input.
 *
 * "exp" convention: Unix epoch seconds (Long, though a plain Integer must
 * also be accepted); verifyToken raises CryptoException once exp is at or
 * before "now". Any tampering, truncation, or structurally invalid token
 * also raises CryptoException instead of leaking a lower-level exception.
 */
public class TokenClient {

    private static final String HEADER = base64Url("BOOGIE-HS256".getBytes(StandardCharsets.UTF_8));

    private final SecretKey signingKey;

    public TokenClient() {
        try {
            this.signingKey = KeyGenerator.getInstance("HmacSHA256").generateKey();
        } catch (NoSuchAlgorithmException e) {
            throw new CryptoException("failed to initialize token signing key", e);
        }
    }

    public String issueToken(Map<String, Object> claims) {
        try {
            String payload = base64Url(encodeClaims(claims));
            String signingInput = HEADER + "." + payload;
            String signature = base64Url(hmac(signingInput.getBytes(StandardCharsets.UTF_8)));
            return signingInput + "." + signature;
        } catch (CryptoException e) {
            throw e;
        } catch (Exception e) {
            throw new CryptoException("failed to issue token", e);
        }
    }

    public Claims verifyToken(String token) {
        try {
            String[] parts = token.split("\\.", -1);
            if (parts.length != 3 || parts[0].isEmpty() || parts[1].isEmpty() || parts[2].isEmpty()) {
                throw new CryptoException("structurally invalid token");
            }

            // Signature MUST be verified before the payload is decoded --
            // never decode unauthenticated bytes.
            String signingInput = parts[0] + "." + parts[1];
            byte[] expectedSignature = hmac(signingInput.getBytes(StandardCharsets.UTF_8));
            byte[] providedSignature = Base64.getUrlDecoder().decode(parts[2]);
            if (!MessageDigest.isEqual(expectedSignature, providedSignature)) {
                throw new CryptoException("token signature is invalid");
            }

            byte[] payloadBytes = Base64.getUrlDecoder().decode(parts[1]);
            Map<String, Object> claims = decodeClaims(new String(payloadBytes, StandardCharsets.UTF_8));

            Object exp = claims.get("exp");
            if (exp instanceof Number expNumber && expNumber.longValue() <= Instant.now().getEpochSecond()) {
                throw new CryptoException("token has expired");
            }

            return new Claims(claims);
        } catch (CryptoException e) {
            throw e;
        } catch (Exception e) {
            throw new CryptoException("failed to verify token", e);
        }
    }

    private byte[] hmac(byte[] data) throws GeneralSecurityException {
        Mac mac = Mac.getInstance("HmacSHA256");
        mac.init(signingKey);
        return mac.doFinal(data);
    }

    private static String base64Url(byte[] data) {
        return Base64.getUrlEncoder().withoutPadding().encodeToString(data);
    }

    // -- hand-rolled claims encoding (no JSON lib, no object serialization) --

    private static byte[] encodeClaims(Map<String, Object> claims) {
        StringBuilder sb = new StringBuilder();
        for (Map.Entry<String, Object> entry : claims.entrySet()) {
            String key = entry.getKey();
            Object value = entry.getValue();
            char typeTag;
            String rawValue;
            if (value instanceof String s) {
                typeTag = 's';
                rawValue = s;
            } else if (value instanceof Long l) {
                typeTag = 'l';
                rawValue = l.toString();
            } else if (value instanceof Integer i) {
                typeTag = 'i';
                rawValue = i.toString();
            } else if (value instanceof Boolean b) {
                typeTag = 'b';
                rawValue = b.toString();
            } else {
                throw new CryptoException(
                        "unsupported claim value type for key '" + key + "': "
                                + (value == null ? "null" : value.getClass().getName()));
            }
            sb.append(escape(key)).append('\t').append(typeTag).append('\t').append(escape(rawValue)).append('\n');
        }
        return sb.toString().getBytes(StandardCharsets.UTF_8);
    }

    private static Map<String, Object> decodeClaims(String encoded) {
        Map<String, Object> claims = new LinkedHashMap<>();
        if (encoded.isEmpty()) {
            return claims;
        }
        for (String line : encoded.split("\n", -1)) {
            if (line.isEmpty()) {
                continue;
            }
            String[] fields = line.split("\t", 3);
            if (fields.length != 3) {
                throw new CryptoException("malformed claim line in token payload");
            }
            String key = unescape(fields[0]);
            char typeTag = fields[1].isEmpty() ? '\0' : fields[1].charAt(0);
            String rawValue = unescape(fields[2]);

            Object value = switch (typeTag) {
                case 's' -> rawValue;
                case 'l' -> Long.parseLong(rawValue);
                case 'i' -> Integer.parseInt(rawValue);
                case 'b' -> Boolean.parseBoolean(rawValue);
                default -> throw new CryptoException("unknown claim type tag: " + fields[1]);
            };
            claims.put(key, value);
        }
        return claims;
    }

    private static String escape(String raw) {
        StringBuilder sb = new StringBuilder(raw.length());
        for (int i = 0; i < raw.length(); i++) {
            char c = raw.charAt(i);
            switch (c) {
                case '\\' -> sb.append("\\\\");
                case '\t' -> sb.append("\\t");
                case '\n' -> sb.append("\\n");
                default -> sb.append(c);
            }
        }
        return sb.toString();
    }

    private static String unescape(String escaped) {
        StringBuilder sb = new StringBuilder(escaped.length());
        for (int i = 0; i < escaped.length(); i++) {
            char c = escaped.charAt(i);
            if (c == '\\' && i + 1 < escaped.length()) {
                char next = escaped.charAt(++i);
                switch (next) {
                    case '\\' -> sb.append('\\');
                    case 't' -> sb.append('\t');
                    case 'n' -> sb.append('\n');
                    default -> {
                        sb.append('\\');
                        sb.append(next);
                    }
                }
            } else {
                sb.append(c);
            }
        }
        return sb.toString();
    }
}
