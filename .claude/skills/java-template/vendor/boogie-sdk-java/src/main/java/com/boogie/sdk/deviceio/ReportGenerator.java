package com.boogie.sdk.deviceio;

import com.boogie.sdk.core.DeviceIoException;
import org.apache.pdfbox.pdmodel.PDDocument;
import org.apache.pdfbox.pdmodel.PDPage;
import org.apache.pdfbox.pdmodel.PDPageContentStream;
import org.apache.pdfbox.pdmodel.font.PDType1Font;
import org.apache.pdfbox.pdmodel.font.Standard14Fonts;
import org.apache.poi.ss.usermodel.Row;
import org.apache.poi.ss.usermodel.Sheet;
import org.apache.poi.xssf.usermodel.XSSFWorkbook;

import java.io.IOException;
import java.io.OutputStream;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;

/**
 * ReportGenerator stub. See boogie-sdk-api.md section 5.3 (deviceio).
 * Skeleton only — implemented during the Phase 1 TDD loop for the `deviceio` module.
 */
public class ReportGenerator {
    private static final float LEADING = 16f;
    private static final float MARGIN = 40f;

    public void generateExcel(List<Map<String, Object>> data, Path template, Path outFile) {
        try (XSSFWorkbook workbook = new XSSFWorkbook()) {
            Sheet sheet = workbook.createSheet();

            List<String> headers = data.isEmpty()
                    ? List.of()
                    : new ArrayList<>(data.get(0).keySet());

            Row headerRow = sheet.createRow(0);
            for (int c = 0; c < headers.size(); c++) {
                headerRow.createCell(c).setCellValue(headers.get(c));
            }

            int rowIndex = 1;
            for (Map<String, Object> record : data) {
                Row row = sheet.createRow(rowIndex++);
                int c = 0;
                for (String header : headers) {
                    Object value = record.get(header);
                    writeCell(row, c++, value);
                }
            }

            try (OutputStream out = Files.newOutputStream(outFile)) {
                workbook.write(out);
            }
        } catch (IOException e) {
            throw new DeviceIoException("failed to generate excel report: " + outFile, e);
        }
    }

    private static void writeCell(Row row, int column, Object value) {
        var cell = row.createCell(column);
        if (value == null) {
            cell.setBlank();
        } else if (value instanceof Number number) {
            cell.setCellValue(number.doubleValue());
        } else if (value instanceof Boolean bool) {
            cell.setCellValue(bool);
        } else {
            cell.setCellValue(String.valueOf(value));
        }
    }

    public void generatePdf(List<Map<String, Object>> data, Path template, Path outFile) {
        try (PDDocument document = new PDDocument()) {
            PDPage page = new PDPage();
            document.addPage(page);
            var font = new PDType1Font(Standard14Fonts.FontName.HELVETICA);

            try (PDPageContentStream stream = new PDPageContentStream(document, page)) {
                float y = page.getMediaBox().getHeight() - MARGIN;
                stream.beginText();
                stream.setFont(font, 11);
                stream.newLineAtOffset(MARGIN, y);

                List<String> headers = data.isEmpty()
                        ? List.of()
                        : new ArrayList<>(data.get(0).keySet());
                stream.showText(String.join(" | ", headers));

                for (Map<String, Object> record : data) {
                    stream.newLineAtOffset(0, -LEADING);
                    List<String> values = new ArrayList<>();
                    for (String header : headers) {
                        values.add(String.valueOf(record.get(header)));
                    }
                    stream.showText(String.join(" | ", values));
                }

                stream.endText();
            }

            document.save(outFile.toFile());
        } catch (IOException e) {
            throw new DeviceIoException("failed to generate pdf report: " + outFile, e);
        }
    }
}
