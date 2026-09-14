package com.boogie.sdk.governance;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.util.List;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

/**
 * Tests for NotificationClient. See boogie-sdk-api.md section 5.5
 * (governance).
 *
 * <p>The design doc only documents {@code sendEmail}/{@code sendIm}/
 * {@code sendSms} as fire-and-forget {@code void} methods, with no way to
 * observe what was "sent" and no real email/IM/SMS provider behind this
 * fake. This test file pins down the additive, testable convention
 * invented to make the fake observable, mirroring the already-built
 * Python port's {@code sent_emails}/{@code sent_ims}/{@code sent_sms}
 * lists and this codebase's own {@code Tracer.FinishedSpan} nested-record
 * pattern:
 *
 * <ul>
 *   <li><b>{@code NotificationClient.SentEmail(String to, String subject,
 *       String body)}</b>, <b>{@code SentIm(String channel, String
 *       message)}</b>, and <b>{@code SentSms(String phone, String
 *       message)}</b> (additive nested records, not in the design doc):
 *       one instance is appended to the corresponding introspection list
 *       — {@code sentEmails()}, {@code sentIms()}, {@code sentSms()}
 *       (also additive) — every time {@code sendEmail}/{@code sendIm}/
 *       {@code sendSms} is called, in call order, capturing exactly the
 *       arguments passed in.
 *   <li>The three lists are independent: calling one {@code sendXxx}
 *       method never appends to another channel's list.
 * </ul>
 *
 * <p>All {@code sendXxx} methods and all three introspection getters
 * currently throw {@link UnsupportedOperationException} (skeleton stage)
 * — every test below is expected to fail with that exception until the
 * `implementer` stage fills in real bodies; that failure mode is
 * expected/fine per the TDD pipeline.
 */
class NotificationClientTest {

    private NotificationClient client;

    @BeforeEach
    void setUp() {
        client = new NotificationClient();
    }

    @Test
    void newClientHasNoSentMessages() {
        assertTrue(client.sentEmails().isEmpty());
        assertTrue(client.sentIms().isEmpty());
        assertTrue(client.sentSms().isEmpty());
    }

    @Test
    void sendEmailAppendsToSentEmails() {
        client.sendEmail("a@example.com", "hi", "body");

        List<NotificationClient.SentEmail> emails = client.sentEmails();
        assertEquals(1, emails.size());
        assertEquals(new NotificationClient.SentEmail("a@example.com", "hi", "body"), emails.get(0));
    }

    @Test
    void sendImAppendsToSentIms() {
        client.sendIm("#general", "hello");

        List<NotificationClient.SentIm> ims = client.sentIms();
        assertEquals(1, ims.size());
        assertEquals(new NotificationClient.SentIm("#general", "hello"), ims.get(0));
    }

    @Test
    void sendSmsAppendsToSentSms() {
        client.sendSms("+15551234567", "hey");

        List<NotificationClient.SentSms> sms = client.sentSms();
        assertEquals(1, sms.size());
        assertEquals(new NotificationClient.SentSms("+15551234567", "hey"), sms.get(0));
    }

    @Test
    void multipleSendEmailCallsAreRecordedInCallOrder() {
        client.sendEmail("a@example.com", "first", "body-1");
        client.sendEmail("b@example.com", "second", "body-2");

        List<NotificationClient.SentEmail> emails = client.sentEmails();
        assertEquals(2, emails.size());
        assertEquals("first", emails.get(0).subject());
        assertEquals("second", emails.get(1).subject());
    }

    @Test
    void sendingOnOneChannelDoesNotAffectOtherChannels() {
        client.sendEmail("a@example.com", "hi", "body");

        assertEquals(1, client.sentEmails().size());
        assertTrue(client.sentIms().isEmpty());
        assertTrue(client.sentSms().isEmpty());
    }
}
