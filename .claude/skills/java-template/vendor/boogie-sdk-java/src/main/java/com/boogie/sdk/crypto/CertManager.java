package com.boogie.sdk.crypto;

import com.boogie.sdk.core.CryptoException;
import com.boogie.sdk.core.NotFoundException;

import java.io.ByteArrayInputStream;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.security.cert.CertificateException;
import java.security.cert.CertificateFactory;
import java.security.cert.X509Certificate;
import java.time.Duration;
import java.time.Instant;
import java.util.HexFormat;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

/**
 * CertManager. See boogie-sdk-api.md section 5.1 (crypto).
 *
 * loadCert(Path) parses real PEM-encoded X.509 data via
 * java.security.cert.CertificateFactory. certId is derived from the
 * certificate itself (SHA-256 fingerprint of the DER encoding), not supplied
 * by the caller, so re-loading the same file is idempotent and different
 * certs get different ids.
 *
 * "Rotation due" uses a 30-day-before-expiry threshold; the test suite only
 * pins the unambiguous ends (already expired -> true, ~2 years out -> false)
 * so the exact threshold is an implementation choice.
 */
public class CertManager {

    private static final Duration ROTATION_THRESHOLD = Duration.ofDays(30);

    private final Map<String, Certificate> certsById = new ConcurrentHashMap<>();

    public Certificate loadCert(Path path) {
        try {
            byte[] bytes = Files.readAllBytes(path);
            CertificateFactory factory = CertificateFactory.getInstance("X.509");
            X509Certificate cert = (X509Certificate) factory.generateCertificate(new ByteArrayInputStream(bytes));

            MessageDigest digest = MessageDigest.getInstance("SHA-256");
            String certId = HexFormat.of().formatHex(digest.digest(cert.getEncoded()));
            String subject = cert.getSubjectX500Principal().getName();
            Instant expiresAt = cert.getNotAfter().toInstant();

            Certificate result = new Certificate(certId, subject, expiresAt);
            certsById.put(certId, result);
            return result;
        } catch (IOException | CertificateException | NoSuchAlgorithmException | ClassCastException e) {
            throw new CryptoException("failed to load certificate from " + path, e);
        }
    }

    public Instant getExpiryDate(String certId) {
        return findCert(certId).expiresAt();
    }

    public boolean isRotationDue(String certId) {
        Certificate cert = findCert(certId);
        return !cert.expiresAt().isAfter(Instant.now().plus(ROTATION_THRESHOLD));
    }

    private Certificate findCert(String certId) {
        Certificate cert = certsById.get(certId);
        if (cert == null) {
            throw new NotFoundException("unknown certId: " + certId);
        }
        return cert;
    }
}
