package com.company.corplib.logging;

import java.io.PrintStream;
import java.io.PrintWriter;
import java.io.StringWriter;
import java.time.Instant;
import java.util.LinkedHashMap;
import java.util.Map;

/**
 * Minimal real implementation for migration-kit test infrastructure.
 * Writes one JSON object per line to stdout. Not a description of the
 * real company log-collector wire format, just enough to be genuinely
 * compilable and runnable.
 */
public final class Loggers {

    private Loggers() {
    }

    public static Logger get(Class<?> cls) {
        return new Logger(cls.getName());
    }

    public static class Logger {
        private final String name;
        private final PrintStream out = System.out;

        Logger(String name) {
            this.name = name;
        }

        public void info(String message, Map<String, Object> fields) {
            write("INFO", message, fields, null);
        }

        public void error(String message, Map<String, Object> fields) {
            write("ERROR", message, fields, null);
        }

        public void error(String message, Map<String, Object> fields, Throwable ex) {
            write("ERROR", message, fields, ex);
        }

        private void write(String level, String message, Map<String, Object> fields, Throwable ex) {
            Map<String, Object> payload = new LinkedHashMap<>();
            payload.put("timestamp", Instant.now().toString());
            payload.put("level", level);
            payload.put("logger", name);
            payload.put("message", message);
            if (fields != null) {
                payload.putAll(fields);
            }
            if (ex != null) {
                StringWriter sw = new StringWriter();
                ex.printStackTrace(new PrintWriter(sw));
                payload.put("exc_info", sw.toString());
            }
            out.println(toJson(payload));
        }

        private static String toJson(Map<String, Object> payload) {
            StringBuilder sb = new StringBuilder("{");
            boolean first = true;
            for (Map.Entry<String, Object> e : payload.entrySet()) {
                if (!first) {
                    sb.append(',');
                }
                first = false;
                sb.append('"').append(escape(e.getKey())).append("\":");
                Object v = e.getValue();
                if (v == null) {
                    sb.append("null");
                } else if (v instanceof Number || v instanceof Boolean) {
                    sb.append(v);
                } else {
                    sb.append('"').append(escape(String.valueOf(v))).append('"');
                }
            }
            sb.append('}');
            return sb.toString();
        }

        private static String escape(String s) {
            return s.replace("\\", "\\\\").replace("\"", "\\\"").replace("\n", "\\n");
        }
    }
}
