package com.boogie.sdk.examples.etldemo;

import com.boogie.sdk.BoogieSdk;
import com.boogie.sdk.infra.Message;

import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;

/**
 * Upload (Load) stage of the ETL demo.
 *
 * <p>See `boogie-sdk-api.md` (this skill's library doc) section 7 (migration cheat
 * sheet). Covers both writing the transformed batch out and producing the
 * summary report -- both are "output" concerns.
 */
final class Upload {

    private static final Path OUTPUT_DIR = resolveOutputDir();

    /**
     * Resolves {@code target/etl-demo-output/} next to wherever this
     * class's compiled {@code .class} file actually lives, rather than a
     * plain relative path. {@code exec:java} runs in-process, so the JVM's
     * working directory stays wherever {@code mvn} itself was launched
     * from (which may be the repo root, not
     * {@code .claude/skills/java-template/vendor/boogie-sdk-java/}) --
     * a relative {@code Path.of("target", ...)} would otherwise land in
     * the wrong {@code target/} depending on the caller's cwd.
     */
    private static Path resolveOutputDir() {
        try {
            Path classesDir = Path.of(
                    Upload.class.getProtectionDomain().getCodeSource().getLocation().toURI());
            // classesDir is .../boogie-sdk-java/target/classes -> its parent is target/.
            return classesDir.getParent().resolve("etl-demo-output");
        } catch (Exception e) {
            // Fallback: relative to the current working directory.
            return Path.of("target", "etl-demo-output");
        }
    }

    private Upload() {
    }

    /**
     * Load stage: publish the transformed batch to object storage, then
     * announce completion on a queue for whatever downstream system cares.
     *
     * <p>No cheat-sheet line covers object storage/pub-sub directly (they
     * are infra primitives a legacy Delphi/VB6 job usually didn't have at
     * all -- it just wrote a file to a shared drive); this is the "what
     * you get for free once you're on boogie-sdk" half of the story.
     */
    static void upload(BoogieSdk sdk, String batchId, List<Map<String, Object>> okRows) {
        byte[] payload = buildBatchPayload(batchId, okRows);
        sdk.objectStorage().upload("etl-demo-reports", "batches/" + batchId + "/transformed.json", payload);
        sdk.logger().info("uploaded transformed batch to object storage",
                Map.of("batchId", batchId, "rowCount", okRows.size()));

        sdk.queue().subscribe("etl.batch.completed", (Message message) ->
                System.out.printf("    [downstream consumer] received on %s: %s%n",
                        message.topic(), new String(message.body(), StandardCharsets.UTF_8)));

        sdk.queue().publish("etl.batch.completed",
                ("{\"batchId\":\"%s\",\"rowCount\":%d}".formatted(batchId, okRows.size()))
                        .getBytes(StandardCharsets.UTF_8));
    }

    /**
     * Hand-builds a small JSON-ish payload for the transformed batch. No
     * JSON library is a dependency of this project (see {@code
     * Logger.safeToString} for the same convention elsewhere in
     * boogie-sdk) -- fine for this fixed, known shape of data.
     */
    private static byte[] buildBatchPayload(String batchId, List<Map<String, Object>> okRows) {
        StringBuilder json = new StringBuilder();
        json.append("{\"batchId\":\"").append(batchId).append("\",\"rows\":[");
        for (int i = 0; i < okRows.size(); i++) {
            if (i > 0) {
                json.append(',');
            }
            Map<String, Object> row = okRows.get(i);
            json.append("{\"deviceId\":\"").append(row.get("deviceId"))
                    .append("\",\"readingValue\":").append(row.get("readingValue"))
                    .append(",\"maskedPhone\":\"").append(row.get("maskedPhone")).append("\"}");
        }
        json.append("]}");
        return json.toString().getBytes(StandardCharsets.UTF_8);
    }

    /**
     * Report stage.
     *
     * <p>Cheat sheet: Excel COM 自動化(`TExcelApplication`)產報表 -&gt;
     * `sdk.deviceIo().reportGenerator()`. No COM, no Excel installed on the
     * box required -- this writes a real {@code .xlsx} via Apache POI
     * under the hood.
     */
    static Path buildReport(
            BoogieSdk sdk, String batchId, List<Map<String, Object>> okRows, List<Map<String, Object>> failedRows)
            throws Exception {
        Files.createDirectories(OUTPUT_DIR);

        List<Map<String, Object>> summaryRows = new ArrayList<>(okRows.size() + failedRows.size());
        summaryRows.addAll(okRows);
        summaryRows.addAll(failedRows);

        Path outFile = OUTPUT_DIR.resolve("etl_report_" + batchId + ".xlsx");
        // `template` isn't consulted by the current fake implementation,
        // but the API requires a Path -- pass a placeholder, same as real
        // call sites do.
        sdk.deviceIo().reportGenerator().generateExcel(summaryRows, Path.of("unused-template.xlsx"), outFile);
        return outFile;
    }
}
