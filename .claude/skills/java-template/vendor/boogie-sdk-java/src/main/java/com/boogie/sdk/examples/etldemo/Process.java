package com.boogie.sdk.examples.etldemo;

import com.boogie.sdk.BoogieSdk;
import com.boogie.sdk.crypto.MaskUtil;
import com.boogie.sdk.infra.Row;
import com.boogie.sdk.observability.Counter;

import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.HexFormat;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * Process (Transform) stage of the ETL demo.
 *
 * <p>See `boogie-sdk-api.md` (this skill's library doc) section 7 (migration cheat
 * sheet).
 */
final class Process {

    /** AES key id used to encrypt the raw phone number at rest. */
    private static final String KEY_ID = "etl-demo-pii";

    private Process() {
    }

    /** Holds the two outcomes of {@link #process}: successful rows and failed rows. */
    record TransformResult(List<Map<String, Object>> ok, List<Map<String, Object>> failed) {
    }

    /**
     * Transform stage: apply the per-row transform to every downloaded row.
     *
     * <p>A bad row is caught, logged, notified, and audited -- then the
     * batch keeps going. This mirrors what new hires are told to expect
     * from a migrated legacy job: one malformed record from a flaky sensor
     * should never crash the whole nightly run.
     */
    static TransformResult process(BoogieSdk sdk, List<Row> rows, String batchId) {
        List<Map<String, Object>> okRows = new ArrayList<>();
        List<Map<String, Object>> failedRows = new ArrayList<>();

        Counter processedCounter = sdk.metrics().counter("etl.rows.processed");
        Counter failedCounter = sdk.metrics().counter("etl.rows.failed");

        for (Row row : rows) {
            String deviceId = (String) row.values().get("device_id");
            String contactPhone = (String) row.values().get("contact_phone");
            String readingValueRaw = (String) row.values().get("reading_value");
            String recordedAt = (String) row.values().get("recorded_at");

            try {
                // legacy data stored everything as text; this is where a
                // bad value ("ERR") blows up.
                double readingValue = Double.parseDouble(readingValueRaw);

                // Cheat sheet:
                // - 自製 XOR / 簡易加密函式 -> `sdk.crypto().encryptAes(...)`
                //   (the raw phone number gets encrypted at rest, not just
                //   hidden behind a weak cipher).
                // - PII shown in logs/reports uses `MaskUtil.maskPhone(...)`
                //   instead of printing the number in full, the way a
                //   legacy log line often did.
                byte[] encryptedPhone = sdk.crypto().encryptAes(contactPhone.getBytes(StandardCharsets.UTF_8), KEY_ID);

                Map<String, Object> okRow = new LinkedHashMap<>();
                okRow.put("deviceId", deviceId);
                okRow.put("status", "OK");
                okRow.put("readingValue", readingValue);
                okRow.put("maskedPhone", MaskUtil.maskPhone(contactPhone));
                okRow.put("recordedAt", recordedAt);
                okRow.put("note", "encryptedPhoneHex=" + HexFormat.of().formatHex(encryptedPhone));
                okRows.add(okRow);
                processedCounter.increment();
            } catch (NumberFormatException exc) {
                // Cheat sheet: 用 `TStringList.SaveToFile` 寫純文字 log ->
                // `sdk.logger()` (structured, not a flat text file); and
                // this is exactly the kind of failure a legacy job would
                // silently swallow or crash on.
                sdk.logger().error("row transform failed, skipping row and continuing batch", exc,
                        Map.of("batchId", batchId, "deviceId", deviceId, "readingValue", readingValueRaw));

                // Cheat sheet: `CDO.Message`/Indy SMTP 寄信 ->
                // `sdk.notification().sendEmail(...)`.
                sdk.notification().sendEmail(
                        "etl-oncall@example.com",
                        "[ETL] row for %s failed in batch %s".formatted(deviceId, batchId),
                        "device_id=%s reading_value=%s error=%s".formatted(deviceId, readingValueRaw, exc));

                sdk.audit().record("etl_batch_job", "transform_row", "sensor_readings:" + deviceId, "failed");
                failedCounter.increment();

                Map<String, Object> failedRow = new LinkedHashMap<>();
                failedRow.put("deviceId", deviceId);
                failedRow.put("status", "FAILED");
                failedRow.put("readingValue", readingValueRaw);
                failedRow.put("maskedPhone", MaskUtil.maskPhone(contactPhone));
                failedRow.put("recordedAt", recordedAt);
                failedRow.put("note", "error=" + exc.getMessage());
                failedRows.add(failedRow);
            }
        }

        return new TransformResult(okRows, failedRows);
    }
}
