package com.boogie.sdk.examples.etldemo;

import com.boogie.sdk.BoogieSdk;
import com.boogie.sdk.deviceio.BatchEvent;
import com.boogie.sdk.deviceio.BatchTracker;
import com.boogie.sdk.deviceio.Shift;
import com.boogie.sdk.governance.AuditLogger;
import com.boogie.sdk.governance.NotificationClient;
import com.boogie.sdk.infra.DbClient;
import com.boogie.sdk.infra.Row;
import com.boogie.sdk.observability.Span;
import com.boogie.sdk.observability.Tracer;

import java.nio.file.Path;
import java.time.Instant;
import java.util.List;
import java.util.Map;

/**
 * ETL demo: a "migrated" nightly batch job built on boogie-sdk.
 *
 * <p>The scenario this class tells: imagine this used to be a Delphi/VB6
 * night job that read a {@code .ini} config, hit an Access/SQL Server DB
 * directly via {@code ADODB.Connection}/{@code TADOConnection}, wrote a
 * plaintext log with {@code TStringList.SaveToFile}, produced an Excel
 * report via COM automation ({@code TExcelApplication}), and emailed
 * someone by hand when a row blew up. Every step below is commented with
 * which line of the "migration cheat sheet"
 * (see `boogie-sdk-api.md` (this skill's library doc), section 7) it replaces.
 *
 * <p>This example follows the standard 4-file ETL template shape used
 * across every boogie-sdk example, regardless of language: this file
 * (orchestration + cross-cutting observability), {@link Download}
 * (Extract), {@link Process} (Transform), {@link Upload} (Load + report).
 *
 * <p>Run it from the repo root with:
 *
 * <pre>
 * mvn -f .claude/skills/java-template/vendor/boogie-sdk-java/pom.xml compile exec:java \
 *     -Dexec.mainClass="com.boogie.sdk.examples.etldemo.Main"
 * </pre>
 *
 * <p>It is fully self-contained: {@code sdk.db()} owns a private in-memory
 * H2 database, so {@link Download} creates and seeds its own table before
 * reading it back -- there is no external database to set up. It finishes
 * with exit code 0 and writes a small Excel summary report under
 * {@code target/etl-demo-output/} (a build-output-adjacent location
 * already covered by Maven's normal {@code target/} convention).
 */
public final class Main {

    private Main() {
    }

    public static void main(String[] args) throws Exception {
        BoogieSdk sdk = BoogieSdk.init();
        // `Main` owns the DB connection and hands it to `Download.download`
        // -- `Download` never reaches back into the wider `sdk` facade itself.
        DbClient db = sdk.db();
        BatchTracker batchTracker = sdk.deviceIo().batchTracker();
        Instant now = Instant.now();
        String batchId = "NIGHTLY-%s-%d".formatted(
                now.toString().substring(0, 10).replace("-", ""), sdk.idGenerator().nextId());

        String finalStatus;
        List<Map<String, Object>> okRows;
        List<Map<String, Object>> failedRows;

        // Cheat sheet: `CreateMutex` / 檔案鎖做單例執行保護 has no equivalent
        // needed here (single-process demo) -- but wrapping the whole run in
        // a span is observability a legacy job never had at all.
        try (Span span = sdk.tracer().startSpan("nightly_etl_run")) {
            Shift shift = sdk.deviceIo().shiftCalendar().currentShift(now);
            batchTracker.createBatch(batchId);

            sdk.logger().info("etl run started", Map.of("batchId", batchId, "shift", shift.name()));
            sdk.audit().record("etl_batch_job", "run_start", "batch:" + batchId, "started");

            System.out.printf("=== boogie-sdk ETL demo :: batch %s (shift=%s) ===%n", batchId, shift.name());

            System.out.println("\n-- download --");
            batchTracker.updateStatus(batchId, "extracting");
            List<Row> rows = Download.download(db);
            sdk.logger().info("download complete", Map.of("batchId", batchId, "rowCount", rows.size()));
            System.out.printf("  downloaded %d rows from sdk.db() (sensor_readings)%n", rows.size());

            System.out.println("\n-- process --");
            batchTracker.updateStatus(batchId, "transforming");
            Process.TransformResult result = Process.process(sdk, rows, batchId);
            okRows = result.ok();
            failedRows = result.failed();
            sdk.logger().info("process complete",
                    Map.of("batchId", batchId, "ok", okRows.size(), "failed", failedRows.size()));
            System.out.printf("  %d rows processed OK, %d row(s) failed (see logger.error above)%n",
                    okRows.size(), failedRows.size());

            System.out.println("\n-- upload --");
            batchTracker.updateStatus(batchId, "loading");
            Upload.upload(sdk, batchId, okRows);
            System.out.println("  uploaded batch payload to objectStorage() and published etl.batch.completed");

            Path reportPath = Upload.buildReport(sdk, batchId, okRows, failedRows);
            System.out.println("  wrote Excel summary report to " + reportPath);

            finalStatus = failedRows.isEmpty() ? "completed" : "completed_with_errors";
            batchTracker.updateStatus(batchId, finalStatus);
            sdk.audit().record("etl_batch_job", "run_finish", "batch:" + batchId, finalStatus);
            sdk.logger().info("etl run finished", Map.of("batchId", batchId, "status", finalStatus));
        }

        System.out.printf("%n=== batch %s finished: %s ===%n", batchId, finalStatus);

        System.out.println("\n-- batch_tracker history --");
        for (BatchEvent event : batchTracker.getHistory(batchId)) {
            System.out.printf("  %s  %s%n", event.at(), event.status());
        }

        System.out.println("\n-- metrics snapshot --");
        for (Map.Entry<String, Double> entry : sdk.metrics().snapshot().entrySet()) {
            System.out.printf("  %s = %s%n", entry.getKey(), entry.getValue());
        }

        System.out.println("\n-- tracer spans --");
        for (Tracer.FinishedSpan finishedSpan : sdk.tracer().finishedSpans()) {
            System.out.printf("  %s: %.4fs%n", finishedSpan.name(), finishedSpan.durationSeconds());
        }

        System.out.println("\n-- notifications sent (would-be emails) --");
        for (NotificationClient.SentEmail email : sdk.notification().sentEmails()) {
            System.out.printf("  to=%s subject=%s%n", email.to(), email.subject());
        }

        System.out.println("\n-- audit trail --");
        for (AuditLogger.AuditRecord record : sdk.audit().records()) {
            System.out.printf("  %s%n", record);
        }

        sdk.close();
    }
}
