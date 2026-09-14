package com.boogie.sdk.examples.etldemo;

import com.boogie.sdk.infra.DbClient;
import com.boogie.sdk.infra.Row;

import java.io.IOException;
import java.io.InputStream;
import java.io.UncheckedIOException;
import java.nio.charset.StandardCharsets;
import java.util.List;
import java.util.Map;

/**
 * Download (Extract) stage of the ETL demo.
 *
 * <p>See `boogie-sdk-api.md` (this skill's library doc) section 7 (migration cheat
 * sheet). This is where a legacy job would have hit its source system
 * directly.
 *
 * <p>Unlike {@link Process}/{@link Upload} (which don't touch the database
 * at all), this stage is SQL-driven: the actual SQL statements live as
 * plain {@code .sql} files under {@code src/main/resources/.../etldemo/sql/}
 * rather than being embedded as string literals here, mirroring how a real
 * migrated job would keep its SQL maintainable/reviewable on its own
 * instead of scattered through code. {@link Main} owns the database
 * connection ({@code sdk.db()}) and hands it to {@link #download} -- this
 * class only ever touches the {@link DbClient} it's given, it never reaches
 * back into the wider {@code BoogieSdk} facade.
 */
final class Download {

    /**
     * "Sensor readings" seed data, standing in for whatever a legacy
     * plant-floor batch job used to read out of its Access/SQL Server table
     * every night. SENSOR-05 is deliberately bad data (a non-numeric
     * reading) so the demo can show a single row failing without taking
     * the whole batch down with it.
     */
    private static final List<String[]> SEED_READINGS = List.of(
            new String[] {"SENSOR-01", "0912345678", "23.5", "2026-09-15 01:15:00"},
            new String[] {"SENSOR-02", "0922334455", "24.1", "2026-09-15 01:20:00"},
            new String[] {"SENSOR-03", "0933445566", "22.8", "2026-09-15 01:30:00"},
            new String[] {"SENSOR-04", "0944556677", "23.9", "2026-09-15 01:40:00"},
            new String[] {"SENSOR-05", "0955667788", "ERR", "2026-09-15 01:45:00"},
            new String[] {"SENSOR-06", "0966778899", "23.2", "2026-09-15 01:50:00"});

    private Download() {
    }

    private static String loadSql(String fileName) {
        try (InputStream in = Download.class.getResourceAsStream("sql/" + fileName)) {
            if (in == null) {
                throw new IllegalStateException("missing SQL resource: sql/" + fileName);
            }
            return new String(in.readAllBytes(), StandardCharsets.UTF_8);
        } catch (IOException e) {
            throw new UncheckedIOException("failed to load SQL resource: sql/" + fileName, e);
        }
    }

    /**
     * Extract stage.
     *
     * <p>Cheat sheet: 直接組 SQL 字串操作 {@code ADODB.Connection}/
     * {@code TADOConnection} -&gt; {@code sdk.db().query(...)}/{@code
     * execute(...)}.
     *
     * <p>In a real migration the table would already exist in the target
     * DB; here we create + seed it first so the example is runnable with
     * zero setup. {@code db.transaction(...)} mirrors how a legacy job
     * would wrap its own multi-row insert in a manual BEGIN/COMMIT to
     * avoid a partial write.
     */
    static List<Row> download(DbClient db) {
        db.execute(loadSql("create_table.sql"), Map.of());

        String insertSql = loadSql("insert_reading.sql");
        db.transaction(session -> {
            for (String[] reading : SEED_READINGS) {
                session.execute(
                        insertSql,
                        Map.of(
                                "deviceId", reading[0],
                                "contactPhone", reading[1],
                                "readingValue", reading[2],
                                "recordedAt", reading[3]));
            }
            return null;
        });

        return db.query(loadSql("select_all.sql"), Map.of());
    }
}
