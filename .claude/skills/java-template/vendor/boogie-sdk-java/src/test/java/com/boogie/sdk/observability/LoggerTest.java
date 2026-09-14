package com.boogie.sdk.observability;

import org.junit.jupiter.api.Test;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.function.Consumer;

import static org.junit.jupiter.api.Assertions.assertDoesNotThrow;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

/**
 * Tests for Logger. See boogie-sdk-api.md section 5.4 (observability).
 *
 * <p>The design doc only gives the method shapes ({@code info(msg,
 * fields)}, {@code warn(msg, fields)}, {@code error(msg, t, fields)}) —
 * there is no real log aggregator behind this fake, so this test file
 * pins down the testable convention, mirroring the Python port's
 * {@code Logger} ({@code boogie-sdk/python/src/boogie_sdk/observability/logger.py}):
 *
 * <p><b>Additive convention beyond the design doc:</b> {@code Logger}
 * gets two constructors — {@code Logger(Consumer<Map<String, Object>>
 * sink)} and a no-arg {@code Logger()}. When a sink is supplied, every
 * call to {@code info}/{@code warn}/{@code error} builds a record {@code
 * Map<String, Object>} and passes it to the sink. The record always has:
 *
 * <ul>
 *   <li>{@code "level"}: one of the literal strings {@code "info"},
 *       {@code "warn"}, {@code "error"}, matching the method called.
 *   <li>{@code "msg"}: the {@code msg} argument, unmodified.
 *   <li>every entry of the {@code fields} map, merged directly into the
 *       top level of the record (so {@code logger.info("x",
 *       Map.of("userId", 1))} produces a record containing
 *       {@code "userId" -> 1}).
 * </ul>
 *
 * <p>For {@code error()}, the optional {@code Throwable t} is captured
 * under the dedicated key {@code "exc"} — as {@code t.toString()} when a
 * throwable is given, or {@code null} when {@code t} is {@code null}.
 * This mirrors the Python port's {@code exc} handling and keeps {@code
 * error()}'s record shape consistent with {@code info}/{@code warn} when
 * no throwable is passed.
 *
 * <p>With no sink given (the no-arg constructor), the class must still be
 * usable standalone, falling back to some default behavior (e.g. printing
 * a JSON-ish line to stdout via a manual/{@code toString()}-based string
 * build — no JSON library is available or needed). This file does not
 * test that default path in detail since it isn't
 * deterministic/observable without capturing stdout; it only pins down
 * that omitting the sink must not itself prevent logging.
 *
 * <p>Both constructors and all three logging methods currently throw
 * {@link UnsupportedOperationException} (skeleton stage) — every test
 * below is expected to fail with that exception until the `implementer`
 * stage fills in real bodies; that failure mode is expected/fine per the
 * TDD pipeline.
 */
class LoggerTest {

    private static Logger loggerWithSink(List<Map<String, Object>> records) {
        Consumer<Map<String, Object>> sink = records::add;
        return new Logger(sink);
    }

    @Test
    void infoCallsSinkWithLevelInfoAndMsg() {
        List<Map<String, Object>> records = new ArrayList<>();
        Logger logger = loggerWithSink(records);

        logger.info("hello", Map.of());

        assertEquals(1, records.size());
        assertEquals("info", records.get(0).get("level"));
        assertEquals("hello", records.get(0).get("msg"));
    }

    @Test
    void warnCallsSinkWithLevelWarn() {
        List<Map<String, Object>> records = new ArrayList<>();
        Logger logger = loggerWithSink(records);

        logger.warn("careful", Map.of());

        assertEquals("warn", records.get(0).get("level"));
        assertEquals("careful", records.get(0).get("msg"));
    }

    @Test
    void errorCallsSinkWithLevelError() {
        List<Map<String, Object>> records = new ArrayList<>();
        Logger logger = loggerWithSink(records);

        logger.error("boom", null, Map.of());

        assertEquals("error", records.get(0).get("level"));
        assertEquals("boom", records.get(0).get("msg"));
    }

    @Test
    void fieldsAreMergedIntoTheRecord() {
        List<Map<String, Object>> records = new ArrayList<>();
        Logger logger = loggerWithSink(records);

        logger.info("request handled", Map.of("requestId", "abc123", "statusCode", 200));

        Map<String, Object> record = records.get(0);
        assertEquals("abc123", record.get("requestId"));
        assertEquals(200, record.get("statusCode"));
    }

    @Test
    void fieldsAreMergedForWarnAndErrorToo() {
        List<Map<String, Object>> records = new ArrayList<>();
        Logger logger = loggerWithSink(records);

        logger.warn("retrying", Map.of("attempt", 2));
        logger.error("gave up", null, Map.of("attempt", 3));

        assertEquals(2, records.get(0).get("attempt"));
        assertEquals(3, records.get(1).get("attempt"));
    }

    @Test
    void errorWithoutThrowableRecordsNullForExcKey() {
        List<Map<String, Object>> records = new ArrayList<>();
        Logger logger = loggerWithSink(records);

        logger.error("no exception here", null, Map.of());

        assertTrue(records.get(0).containsKey("exc"));
        assertNull(records.get(0).get("exc"));
    }

    @Test
    void errorWithThrowableCapturesItAsAString() {
        List<Map<String, Object>> records = new ArrayList<>();
        Logger logger = loggerWithSink(records);

        logger.error("failed", new IllegalStateException("bad value"), Map.of());

        Object exc = records.get(0).get("exc");
        assertTrue(exc instanceof String);
        assertTrue(((String) exc).contains("bad value"));
    }

    @Test
    void infoAndWarnDoNotPopulateAnExcKey() {
        List<Map<String, Object>> records = new ArrayList<>();
        Logger logger = loggerWithSink(records);

        logger.info("hi", Map.of());
        logger.warn("careful", Map.of());

        assertFalse(records.get(0).containsKey("exc"));
        assertFalse(records.get(1).containsKey("exc"));
    }

    @Test
    void multipleCallsEachProduceTheirOwnRecord() {
        List<Map<String, Object>> records = new ArrayList<>();
        Logger logger = loggerWithSink(records);

        logger.info("first", Map.of());
        logger.info("second", Map.of());

        assertEquals(2, records.size());
        assertEquals("first", records.get(0).get("msg"));
        assertEquals("second", records.get(1).get("msg"));
    }

    @Test
    void loggerWithoutSinkDoesNotThrowWhenLogging() {
        Logger logger = new Logger();

        assertDoesNotThrow(() -> logger.info("standalone", Map.of()));
        assertDoesNotThrow(() -> logger.warn("standalone", Map.of()));
        assertDoesNotThrow(() -> logger.error("standalone", null, Map.of()));
    }
}
