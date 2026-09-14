package com.boogie.sdk.crypto;

import com.boogie.sdk.core.NotFoundException;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

import java.io.IOException;
import java.nio.file.Path;
import java.time.Instant;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;
import java.util.concurrent.TimeUnit;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNotEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

/**
 * Tests for CertManager. See boogie-sdk-api.md section 5.1 (crypto).
 *
 * loadCert(Path) accepts only a filesystem path to real PEM-encoded X.509
 * certificate data (this module is implemented with real crypto primitives:
 * java.security.cert.CertificateFactory), so Certificate.certId() must be
 * *derived* by the implementation from the certificate itself (e.g. a
 * fingerprint or serial number) rather than supplied by the caller. These
 * tests treat certId as an opaque string and only assert: it is non-empty,
 * stable across repeated loads of the same certificate file, distinct
 * across different certs, and usable afterward to look up expiry date /
 * rotation status.
 *
 * Test fixtures: real self-signed X.509 certificates are generated with the
 * JDK's own `keytool` CLI (invoked via ProcessBuilder into a @TempDir and
 * exported with -rfc as PEM). This avoids both the fragile/module-restricted
 * sun.security.x509 internals and any new Maven/test dependency -- keytool
 * ships with every JDK install (java.home/bin/keytool), which is why this
 * approach was chosen over hand-building a PEM with only
 * java.security.cert.CertificateFactory.
 *
 * Rotation-due convention: this suite does not pin an exact "days before
 * expiry" threshold (that is an implementation choice). It only asserts the
 * two unambiguous ends: an already-expired certificate must always be
 * reported as rotation-due, and a certificate expiring ~2 years out must
 * never be, for any reasonable threshold.
 */
class CertManagerTest {

    @TempDir
    static Path sharedTempDir;

    static Path validCertPath;
    static Path otherValidCertPath;
    static Path expiredCertPath;

    private CertManager manager;

    @BeforeAll
    static void generateFixtureCertificates() throws IOException, InterruptedException {
        // Valid: started yesterday, expires ~2 years (731 days) later.
        validCertPath = generateSelfSignedCertPem(sharedTempDir, "valid", "valid.example.com", "-1d", 731);
        otherValidCertPath = generateSelfSignedCertPem(sharedTempDir, "other", "other.example.com", "-1d", 731);
        // Expired: started ~2.7 years ago, expired yesterday.
        expiredCertPath = generateSelfSignedCertPem(sharedTempDir, "expired", "expired.example.com", "-1000d", 999);
    }

    @BeforeEach
    void setUp() {
        manager = new CertManager();
    }

    private static Path generateSelfSignedCertPem(
            Path dir, String alias, String commonName, String startDate, int validityDays)
            throws IOException, InterruptedException {
        Path keystore = dir.resolve(alias + "-keystore.p12");
        Path pem = dir.resolve(alias + ".pem");

        runKeytool(
                "-genkeypair", "-alias", alias,
                "-keyalg", "EC", "-groupname", "secp256r1", "-sigalg", "SHA256withECDSA",
                "-validity", String.valueOf(validityDays), "-startdate", startDate,
                "-keystore", keystore.toString(), "-storetype", "PKCS12",
                "-storepass", "changeit", "-keypass", "changeit",
                "-dname", "CN=" + commonName);
        runKeytool(
                "-exportcert", "-alias", alias,
                "-keystore", keystore.toString(), "-storepass", "changeit",
                "-rfc", "-file", pem.toString());

        return pem;
    }

    private static void runKeytool(String... args) throws IOException, InterruptedException {
        String keytoolPath = Path.of(System.getProperty("java.home"), "bin", "keytool").toString();
        List<String> command = new ArrayList<>();
        command.add(keytoolPath);
        command.addAll(Arrays.asList(args));

        ProcessBuilder pb = new ProcessBuilder(command);
        pb.redirectErrorStream(true);
        Process process = pb.start();
        String output = new String(process.getInputStream().readAllBytes());
        boolean finished = process.waitFor(30, TimeUnit.SECONDS);
        if (!finished) {
            process.destroyForcibly();
            throw new IllegalStateException("keytool timed out: " + String.join(" ", args));
        }
        if (process.exitValue() != 0) {
            throw new IllegalStateException("keytool failed (exit=" + process.exitValue() + "): " + output);
        }
    }

    @Test
    void loadCertReturnsCertificateWithSubjectAndFutureExpiry() {
        Certificate cert = manager.loadCert(validCertPath);

        assertNotNull(cert.certId());
        assertFalse(cert.certId().isEmpty());
        assertTrue(cert.subject().contains("valid.example.com"));
        assertTrue(cert.expiresAt().isAfter(Instant.now()));
    }

    @Test
    void loadCertIsIdempotentForSameFile() {
        Certificate first = manager.loadCert(validCertPath);
        Certificate second = manager.loadCert(validCertPath);

        assertEquals(first.certId(), second.certId());
        assertEquals(first.expiresAt(), second.expiresAt());
    }

    @Test
    void loadCertDifferentFilesGetDifferentCertIds() {
        Certificate valid = manager.loadCert(validCertPath);
        Certificate other = manager.loadCert(otherValidCertPath);

        assertNotEquals(valid.certId(), other.certId());
    }

    @Test
    void getExpiryDateMatchesLoadedCertificate() {
        Certificate cert = manager.loadCert(validCertPath);

        assertEquals(cert.expiresAt(), manager.getExpiryDate(cert.certId()));
    }

    @Test
    void getExpiryDateForUnknownCertIdRaisesNotFoundException() {
        assertThrows(NotFoundException.class, () -> manager.getExpiryDate("no-such-cert-id"));
    }

    @Test
    void isRotationDueFalseForFarFutureExpiry() {
        Certificate cert = manager.loadCert(validCertPath);

        assertFalse(manager.isRotationDue(cert.certId()));
    }

    @Test
    void isRotationDueTrueForAlreadyExpiredCertificate() {
        Certificate cert = manager.loadCert(expiredCertPath);

        assertTrue(manager.isRotationDue(cert.certId()));
    }

    @Test
    void isRotationDueForUnknownCertIdRaisesNotFoundException() {
        assertThrows(NotFoundException.class, () -> manager.isRotationDue("no-such-cert-id"));
    }
}
