package com.boogie.sdk.deviceio;

import org.apache.poi.ss.usermodel.Cell;
import org.apache.poi.ss.usermodel.Row;
import org.apache.poi.ss.usermodel.Sheet;
import org.apache.poi.ss.usermodel.Workbook;
import org.apache.poi.xssf.usermodel.XSSFWorkbook;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

/**
 * Tests for ReportGenerator. See boogie-sdk-api.md section 5.3 (deviceio).
 *
 * <p>Unlike the rest of {@code deviceio}, this fake follows the same "fake
 * infra, real output" philosophy as {@code crypto}: there is no real
 * Excel/PDF engine behind it (no COM automation, no print server), but the
 * <i>files it produces are real, valid</i> {@code .xlsx} / {@code .pdf}
 * documents, generated via real, well-established libraries (Apache POI /
 * Apache PDFBox, both added as compile-scope Maven dependencies — see
 * pom.xml) rather than a hand-rolled format writer — far more useful as a
 * training template than a stub that just touches an empty file.
 * Conventions invented for this module, mirroring the already-built Python
 * port's {@code ReportGenerator} (openpyxl/fpdf2-backed):
 *
 * <ul>
 *   <li><b>{@code template} is accepted for API-shape parity but not
 *       applied.</b> Both {@code generateExcel} and {@code generatePdf}
 *       ignore the {@code template} argument entirely and always build a
 *       fresh document from {@code data} via POI/PDFBox. Tests below pass a
 *       {@code template} path that does not even need to exist, to make
 *       this convention unambiguous.
 *   <li><b>{@code generateExcel} layout</b>: row 1 is a header row taken
 *       from the keys of the first map in {@code data} (in insertion
 *       order); each subsequent row holds the values of one map in {@code
 *       data}, in the same column order as the header. Verified here by
 *       round-tripping the output through {@code WorkbookFactory}/{@code
 *       XSSFWorkbook}.
 *   <li><b>{@code generatePdf} verification</b>: PDF content is not deeply
 *       parsed — only that {@code outFile} exists, is non-empty, and
 *       starts with the {@code %PDF-} magic bytes (the standard,
 *       format-defined way to identify a well-formed PDF without a full
 *       parser). One line of text per data row (plus a header line) is
 *       enough.
 * </ul>
 */
class ReportGeneratorTest {

    private final ReportGenerator generator = new ReportGenerator();

    private static List<Map<String, Object>> sampleData() {
        List<Map<String, Object>> data = new ArrayList<>();
        Map<String, Object> row1 = new LinkedHashMap<>();
        row1.put("device_id", "dev-1");
        row1.put("reading", 12.5);
        row1.put("status", "ok");
        data.add(row1);

        Map<String, Object> row2 = new LinkedHashMap<>();
        row2.put("device_id", "dev-2");
        row2.put("reading", 7.0);
        row2.put("status", "warn");
        data.add(row2);

        return data;
    }

    // -- generateExcel -------------------------------------------------------

    @Test
    void generateExcelCreatesOutputFile(@TempDir Path tempDir) throws IOException {
        Path template = tempDir.resolve("template.xlsx"); // deliberately never created
        Path outFile = tempDir.resolve("report.xlsx");

        generator.generateExcel(sampleData(), template, outFile);

        assertTrue(Files.exists(outFile));
        assertTrue(Files.size(outFile) > 0);
    }

    @Test
    void generateExcelWritesHeaderRowFromMapKeys(@TempDir Path tempDir) throws IOException {
        Path template = tempDir.resolve("template.xlsx");
        Path outFile = tempDir.resolve("report.xlsx");

        generator.generateExcel(sampleData(), template, outFile);

        try (Workbook workbook = new XSSFWorkbook(Files.newInputStream(outFile))) {
            Sheet sheet = workbook.getSheetAt(0);
            Row header = sheet.getRow(0);

            assertEquals(List.of("device_id", "reading", "status"), cellStrings(header));
        }
    }

    @Test
    void generateExcelWritesOneRowPerDataMap(@TempDir Path tempDir) throws IOException {
        Path template = tempDir.resolve("template.xlsx");
        Path outFile = tempDir.resolve("report.xlsx");

        generator.generateExcel(sampleData(), template, outFile);

        try (Workbook workbook = new XSSFWorkbook(Files.newInputStream(outFile))) {
            Sheet sheet = workbook.getSheetAt(0);

            Row row1 = sheet.getRow(1);
            assertEquals("dev-1", row1.getCell(0).getStringCellValue());
            assertEquals(12.5, row1.getCell(1).getNumericCellValue());
            assertEquals("ok", row1.getCell(2).getStringCellValue());

            Row row2 = sheet.getRow(2);
            assertEquals("dev-2", row2.getCell(0).getStringCellValue());
            assertEquals(7.0, row2.getCell(1).getNumericCellValue());
            assertEquals("warn", row2.getCell(2).getStringCellValue());

            assertEquals(3, sheet.getPhysicalNumberOfRows());
        }
    }

    @Test
    void generateExcelIgnoresTemplateEvenWhenItExistsWithContent(@TempDir Path tempDir) throws IOException {
        // Even if `template` points at an existing (unrelated) workbook, the
        // output must reflect only `data` — proving `template` is not applied.
        Path template = tempDir.resolve("template.xlsx");
        try (Workbook preExisting = new XSSFWorkbook()) {
            Sheet sheet = preExisting.createSheet();
            Row row = sheet.createRow(0);
            row.createCell(0).setCellValue("should");
            row.createCell(1).setCellValue("not");
            row.createCell(2).setCellValue("appear");
            try (var out = Files.newOutputStream(template)) {
                preExisting.write(out);
            }
        }

        Path outFile = tempDir.resolve("report.xlsx");
        generator.generateExcel(sampleData(), template, outFile);

        try (Workbook workbook = new XSSFWorkbook(Files.newInputStream(outFile))) {
            Sheet sheet = workbook.getSheetAt(0);
            Row header = sheet.getRow(0);

            assertEquals(List.of("device_id", "reading", "status"), cellStrings(header));
        }
    }

    private static List<String> cellStrings(Row row) {
        List<String> values = new ArrayList<>();
        for (Cell cell : row) {
            values.add(cell.getStringCellValue());
        }
        return values;
    }

    // -- generatePdf -----------------------------------------------------------

    @Test
    void generatePdfCreatesNonEmptyValidPdfFile(@TempDir Path tempDir) throws IOException {
        Path template = tempDir.resolve("template.pdf"); // deliberately never created
        Path outFile = tempDir.resolve("report.pdf");

        generator.generatePdf(sampleData(), template, outFile);

        assertTrue(Files.exists(outFile));
        byte[] content = Files.readAllBytes(outFile);
        assertTrue(content.length > 0);
        assertTrue(startsWithPdfMagic(content));
    }

    @Test
    void generatePdfIgnoresTemplateArgument(@TempDir Path tempDir) throws IOException {
        Path template = tempDir.resolve("template.pdf");
        Files.write(template, "not a real pdf at all".getBytes());

        Path outFile = tempDir.resolve("report.pdf");
        generator.generatePdf(sampleData(), template, outFile);

        byte[] content = Files.readAllBytes(outFile);
        assertTrue(startsWithPdfMagic(content));
    }

    private static boolean startsWithPdfMagic(byte[] content) {
        byte[] magic = "%PDF-".getBytes();
        if (content.length < magic.length) {
            return false;
        }
        for (int i = 0; i < magic.length; i++) {
            if (content[i] != magic[i]) {
                return false;
            }
        }
        return true;
    }
}
