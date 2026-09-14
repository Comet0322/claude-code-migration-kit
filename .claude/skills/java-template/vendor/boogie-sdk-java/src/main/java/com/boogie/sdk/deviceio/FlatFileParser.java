package com.boogie.sdk.deviceio;

import com.boogie.sdk.core.ValidationException;
import org.apache.commons.csv.CSVFormat;
import org.apache.commons.csv.CSVParser;
import org.apache.commons.csv.CSVRecord;

import java.io.IOException;
import java.io.Reader;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * FlatFileParser stub. See boogie-sdk-api.md section 5.3 (deviceio).
 * Skeleton only — implemented during the Phase 1 TDD loop for the `deviceio` module.
 */
public class FlatFileParser {
    public <T> List<T> parse(Path file, RecordSchema<T> schema) {
        List<T> results = new ArrayList<>();
        try (Reader reader = Files.newBufferedReader(file, StandardCharsets.UTF_8);
             CSVParser parser = CSVFormat.DEFAULT.builder()
                     .setHeader()
                     .setSkipHeaderRecord(true)
                     .build()
                     .parse(reader)) {
            for (CSVRecord record : parser) {
                Map<String, String> raw = new LinkedHashMap<>(record.toMap());
                try {
                    results.add(schema.parseRow(raw));
                } catch (RuntimeException e) {
                    throw new ValidationException("failed to parse row " + record.getRecordNumber(), e);
                }
            }
        } catch (IOException e) {
            throw new ValidationException("failed to read flat file: " + file, e);
        }
        return results;
    }
}
