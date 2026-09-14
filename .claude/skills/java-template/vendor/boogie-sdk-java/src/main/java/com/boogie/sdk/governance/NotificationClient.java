package com.boogie.sdk.governance;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;

/**
 * NotificationClient stub. See boogie-sdk-api.md section 5.5 (governance).
 * Skeleton only — implemented during the Phase 1 TDD loop for the `governance` module.
 *
 * <p>Additive members beyond the design doc's method-only sketch, needed
 * for the governance test suite to compile (see NotificationClientTest for
 * the full conventions they establish, mirroring the already-built Python
 * port's {@code sent_emails}/{@code sent_ims}/{@code sent_sms} introspection
 * lists and this codebase's own {@code Tracer.FinishedSpan} nested-record
 * pattern): each {@code sendXxx} call appends one entry to the
 * corresponding introspection list below, in call order, and never clears
 * it.
 */
public class NotificationClient {

    public record SentEmail(String to, String subject, String body) {
    }

    public record SentIm(String channel, String message) {
    }

    public record SentSms(String phone, String message) {
    }

    private final List<SentEmail> sentEmails = Collections.synchronizedList(new ArrayList<>());
    private final List<SentIm> sentIms = Collections.synchronizedList(new ArrayList<>());
    private final List<SentSms> sentSms = Collections.synchronizedList(new ArrayList<>());

    public void sendEmail(String to, String subject, String body) {
        sentEmails.add(new SentEmail(to, subject, body));
    }

    public void sendIm(String channel, String message) {
        sentIms.add(new SentIm(channel, message));
    }

    public void sendSms(String phone, String message) {
        sentSms.add(new SentSms(phone, message));
    }

    public List<SentEmail> sentEmails() {
        return new ArrayList<>(sentEmails);
    }

    public List<SentIm> sentIms() {
        return new ArrayList<>(sentIms);
    }

    public List<SentSms> sentSms() {
        return new ArrayList<>(sentSms);
    }
}
