package com.boogie.sdk.deviceio;

import com.boogie.sdk.core.ValidationException;
import org.apache.commons.csv.CSVFormat;
import org.apache.commons.csv.CSVPrinter;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

import java.io.IOException;
import java.io.Writer;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

/**
 * Tests for FlatFileParser. See boogie-sdk-api.md section 5.3 (deviceio).
 *
 * <p>Conventions invented for this module (the design doc only specifies
 * {@code <T> List<T> parse(Path file, RecordSchema<T> schema)}
 * generically), mirroring the already-built Python port's {@code
 * FlatFileParser}:
 *
 * <ul>
 *   <li><b>Flat-file format is CSV</b> — a very common legacy interchange
 *       format — parsed via Apache Commons CSV ({@code
 *       org.apache.commons:commons-csv}) rather than a hand-rolled comma
 *       splitter, per this module's explicit "real, well-established
 *       libraries" convention (a hand-rolled comma-in-quotes parsing bug was
 *       already found and fixed for the `infra` module's SQL parameter
 *       parser — this module deliberately avoids repeating that mistake).
 *       The first line is treated as a header row; each subsequent row is
 *       handed to {@code schema.parseRow(raw)} as a {@code
 *       Map<String, String>} keyed by header name (the same shape {@code
 *       CSVFormat.Builder.setHeader()} + record-to-map conversion
 *       produces).
 *   <li><b>Malformed-row handling: {@code parse} throws {@link
 *       ValidationException} on the first row whose {@code
 *       schema.parseRow} call throws.</b> This module does not silently
 *       skip bad data nor silently collect partial results — a flat-file
 *       feed with a corrupt row aborts the whole parse so the caller
 *       notices immediately. (An alternative would be to skip bad rows or
 *       collect per-row errors; this fake picks "raise immediately, no
 *       partial results returned" and documents it here so the implementer
 *       matches this exact behavior.)
 *   <li>This file's own fixture CSVs are written using {@code
 *       CSVPrinter} (also Commons CSV) rather than hand-built strings, so
 *       quoting/escaping edge cases in the fixtures themselves are handled
 *       by the same well-established library the implementer is expected
 *       to use.
 * </ul>
 */
class FlatFileParserTest {

    /** Minimal RecordSchema implementation used across these tests. */
    record DeviceReading(String deviceId, double value) {
    }

    private static class DeviceReadingSchema implements RecordSchema<DeviceReading> {
        @Override
        public DeviceReading parseRow(Map<String, String> raw) {
            return new DeviceReading(raw.get("device_id"), Double.parseDouble(raw.get("value")));
        }
    }

    private FlatFileParser parser;

    @BeforeEach
    void setUp() {
        parser = new FlatFileParser();
    }

    private static Path writeCsv(Path dir, String[] header, List<String[]> rows) throws IOException {
        Path file = dir.resolve("readings.csv");
        try (Writer writer = Files.newBufferedWriter(file, StandardCharsets.UTF_8);
             CSVPrinter printer = new CSVPrinter(writer, CSVFormat.DEFAULT.builder().setHeader(header).build())) {
            for (String[] row : rows) {
                printer.printRecord((Object[]) row);
            }
        }
        return file;
    }

    // -- happy path -------------------------------------------------------------

    @Test
    void parseReturnsTypedRecordsForEachDataRow(@TempDir Path tempDir) throws IOException {
        Path file = writeCsv(tempDir, new String[] {"device_id", "value"}, List.of(
                new String[] {"dev-1", "12.5"},
                new String[] {"dev-2", "7.0"}));

        List<DeviceReading> records = parser.parse(file, new DeviceReadingSchema());

        assertEquals(List.of(
                new DeviceReading("dev-1", 12.5),
                new DeviceReading("dev-2", 7.0)), records);
    }

    @Test
    void parsePreservesRowOrder(@TempDir Path tempDir) throws IOException {
        Path file = writeCsv(tempDir, new String[] {"device_id", "value"}, List.of(
                new String[] {"z", "1"},
                new String[] {"a", "2"},
                new String[] {"m", "3"}));

        List<DeviceReading> records = parser.parse(file, new DeviceReadingSchema());

        assertEquals(List.of("z", "a", "m"), records.stream().map(DeviceReading::deviceId).toList());
    }

    @Test
    void parseHeaderOnlyFileReturnsEmptyList(@TempDir Path tempDir) throws IOException {
        Path file = writeCsv(tempDir, new String[] {"device_id", "value"}, List.of());

        List<DeviceReading> records = parser.parse(file, new DeviceReadingSchema());

        assertTrue(records.isEmpty());
    }

    @Test
    void parsePassesRawMapKeyedByHeaderToSchema(@TempDir Path tempDir) throws IOException {
        Path file = writeCsv(tempDir, new String[] {"device_id", "value"}, List.<String[]>of(
                new String[] {"dev-9", "3.5"}));

        List<Map<String, String>> seenRows = new ArrayList<>();
        RecordSchema<Void> recordingSchema = raw -> {
            seenRows.add(Map.copyOf(raw));
            return null;
        };

        parser.parse(file, recordingSchema);

        assertEquals(List.of(Map.of("device_id", "dev-9", "value", "3.5")), seenRows);
    }

    @Test
    void parseHandlesCommaInsideQuotedField(@TempDir Path tempDir) throws IOException {
        // The exact "comma-in-quotes" edge case a hand-rolled splitter tends to
        // get wrong — Commons CSV handles it correctly.
        Path file = writeCsv(tempDir, new String[] {"device_id", "value"}, List.<String[]>of(
                new String[] {"dev-1, line A", "1.0"}));

        List<Map<String, String>> seenRows = new ArrayList<>();
        RecordSchema<Void> recordingSchema = raw -> {
            seenRows.add(Map.copyOf(raw));
            return null;
        };

        parser.parse(file, recordingSchema);

        assertEquals("dev-1, line A", seenRows.get(0).get("device_id"));
    }

    // -- malformed rows -----------------------------------------------------------

    @Test
    void parseThrowsValidationExceptionOnMalformedRow(@TempDir Path tempDir) throws IOException {
        Path file = writeCsv(tempDir, new String[] {"device_id", "value"}, List.of(
                new String[] {"dev-1", "12.5"},
                new String[] {"dev-2", "not-a-number"}));

        assertThrows(ValidationException.class, () -> parser.parse(file, new DeviceReadingSchema()));
    }

    @Test
    void parseStopsAtFirstMalformedRowWithoutPartialResultsLeaking(@TempDir Path tempDir) throws IOException {
        // Even though dev-1 parses fine before the bad row, a failed parse
        // throws rather than returning a partial list — the caller gets
        // nothing back. We can't inspect a return value here (the call
        // throws), so this test just re-confirms the exception propagates
        // rather than a partial list being handed back some other way.
        Path file = writeCsv(tempDir, new String[] {"device_id", "value"}, List.of(
                new String[] {"dev-1", "12.5"},
                new String[] {"dev-2", "garbage"}));

        assertThrows(ValidationException.class, () -> parser.parse(file, new DeviceReadingSchema()));
    }
}
