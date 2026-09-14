package com.boogie.sdk.governance;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.util.List;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

/**
 * Tests for AuditLogger. See boogie-sdk-api.md section 5.5 (governance).
 *
 * <p>The design doc only documents {@code record(actor, action, resource,
 * result)} as a fire-and-forget {@code void} method, with no way to read
 * back what was recorded and no real audit sink behind this fake. This
 * test file pins down the additive, testable convention invented to make
 * the fake observable, mirroring the already-built Python port's {@code
 * records} list and this codebase's own {@code Tracer.FinishedSpan}
 * nested-record pattern:
 *
 * <ul>
 *   <li><b>{@code AuditLogger.AuditRecord(String actor, String action,
 *       String resource, String result)}</b> (additive nested record, not
 *       in the design doc) and <b>{@code records()}</b> (additive getter):
 *       one {@code AuditRecord} is appended, capturing exactly the four
 *       arguments passed in, every time {@code record(...)} is called, in
 *       call order. The list is never cleared or deduplicated — repeated
 *       identical calls append repeated identical entries.
 * </ul>
 *
 * <p>{@code record}/{@code records} currently throw {@link
 * UnsupportedOperationException} (skeleton stage) — every test below is
 * expected to fail with that exception until the `implementer` stage
 * fills in real bodies; that failure mode is expected/fine per the TDD
 * pipeline.
 */
class AuditLoggerTest {

    private AuditLogger logger;

    @BeforeEach
    void setUp() {
        logger = new AuditLogger();
    }

    @Test
    void newLoggerHasNoRecords() {
        assertTrue(logger.records().isEmpty());
    }

    @Test
    void recordAppendsOneAuditRecord() {
        logger.record("alice", "delete", "invoice-42", "success");

        List<AuditLogger.AuditRecord> records = logger.records();
        assertEquals(1, records.size());
        assertEquals(new AuditLogger.AuditRecord("alice", "delete", "invoice-42", "success"), records.get(0));
    }

    @Test
    void multipleRecordCallsAreKeptInCallOrder() {
        logger.record("alice", "delete", "invoice-42", "success");
        logger.record("bob", "update", "invoice-43", "denied");

        List<AuditLogger.AuditRecord> records = logger.records();
        assertEquals(2, records.size());
        assertEquals("alice", records.get(0).actor());
        assertEquals("bob", records.get(1).actor());
    }

    @Test
    void repeatedIdenticalCallsAppendRepeatedEntriesWithoutDeduplication() {
        logger.record("alice", "read", "invoice-42", "success");
        logger.record("alice", "read", "invoice-42", "success");

        assertEquals(2, logger.records().size());
    }
}
