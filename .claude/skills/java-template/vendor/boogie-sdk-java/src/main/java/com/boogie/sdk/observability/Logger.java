package com.boogie.sdk.observability;

import java.util.LinkedHashMap;
import java.util.Map;
import java.util.function.Consumer;

/**
 * Logger stub. See boogie-sdk-api.md section 5.4 (observability).
 *
 * <p>Additive beyond the design doc (test-writer stage, mirroring the
 * Python port's {@code Logger}): two constructors — {@link
 * #Logger(Consumer)} taking an explicit sink, and a no-arg {@link
 * #Logger()} documented to fall back to a default sink that prints a
 * JSON-ish line to stdout (a simple manual/{@code toString()}-based
 * string build — no JSON library is available or needed).
 */
public class Logger {

    private final Consumer<Map<String, Object>> sink;

    public Logger() {
        this(Logger::defaultSink);
    }

    public Logger(Consumer<Map<String, Object>> sink) {
        this.sink = sink;
    }

    public void info(String msg, Map<String, Object> fields) {
        dispatch("info", msg, fields, null, false);
    }

    public void warn(String msg, Map<String, Object> fields) {
        dispatch("warn", msg, fields, null, false);
    }

    public void error(String msg, Throwable t, Map<String, Object> fields) {
        dispatch("error", msg, fields, t, true);
    }

    private void dispatch(
            String level, String msg, Map<String, Object> fields, Throwable t, boolean includeExc) {
        Map<String, Object> record = new LinkedHashMap<>();
        record.put("level", level);
        record.put("msg", msg);
        if (fields != null) {
            record.putAll(fields);
        }
        if (includeExc) {
            record.put("exc", t == null ? null : safeValueToString(t));
        }
        try {
            sink.accept(record);
        } catch (Throwable ignored) {
            // The logger must never throw regardless of what's in `fields` or what the
            // sink does with it (e.g. a field whose toString() throws, or a circular
            // map) — best effort only, never propagate.
        }
    }

    private static void defaultSink(Map<String, Object> record) {
        System.out.println(safeToString(record));
    }

    private static String safeToString(Map<String, Object> record) {
        StringBuilder sb = new StringBuilder("{");
        boolean first = true;
        for (Map.Entry<String, Object> entry : record.entrySet()) {
            if (!first) {
                sb.append(", ");
            }
            first = false;
            sb.append(entry.getKey()).append('=').append(safeValueToString(entry.getValue()));
        }
        return sb.append('}').toString();
    }

    private static String safeValueToString(Object value) {
        try {
            return String.valueOf(value);
        } catch (Throwable t) {
            return "<unprintable:" + t.getClass().getSimpleName() + ">";
        }
    }
}
