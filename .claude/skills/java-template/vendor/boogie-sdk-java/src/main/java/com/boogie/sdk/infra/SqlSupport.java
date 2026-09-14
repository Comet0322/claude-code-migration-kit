package com.boogie.sdk.infra;

import java.sql.Connection;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.ResultSetMetaData;
import java.sql.SQLException;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * Shared helper for {@link DbClient} and {@link DbSession}: translates
 * {@code :name}-style named parameters embedded in SQL text into
 * positional JDBC {@code ?} placeholders, binds a {@code Map<String,
 * Object>} of parameter values against them, and converts a
 * {@link ResultSet} into {@link Row}s.
 *
 * The parser is intentionally simple: it scans for tokens of the form
 * {@code :identifier} (a colon followed by letters, digits, or
 * underscores) and does not attempt to special-case most SQL syntax edge
 * cases — sufficient for the fixture SQL this module is exercised
 * against. It does, however, track single-quoted string-literal context
 * (including the {@code ''} escaped-quote form) so a {@code :letter}
 * sequence inside a string literal (e.g. {@code 'Status:Active'} or a
 * Windows path like {@code 'C:Windows'}) is never mistaken for a bind
 * parameter — misreading one there would silently desynchronize the
 * parameter count/order versus what the JDBC driver's own parser expects
 * for the emitted {@code ?} placeholders, binding real values to the
 * wrong placeholders with no immediate error. It also copies a {@code ::}
 * cast-syntax pair through unchanged, rather than treating the second
 * colon as the start of a parameter.
 */
final class SqlSupport {

    private SqlSupport() {
    }

    record Translated(String sql, List<String> paramNames) {
    }

    static Translated translate(String sql) {
        StringBuilder translated = new StringBuilder();
        List<String> paramNames = new ArrayList<>();
        int length = sql.length();
        int i = 0;
        boolean inString = false;
        while (i < length) {
            char c = sql.charAt(i);
            if (inString) {
                translated.append(c);
                if (c == '\'') {
                    if (i + 1 < length && sql.charAt(i + 1) == '\'') {
                        translated.append('\'');
                        i += 2;
                        continue;
                    }
                    inString = false;
                }
                i++;
                continue;
            }
            if (c == '\'') {
                inString = true;
                translated.append(c);
                i++;
                continue;
            }
            if (c == ':' && i + 1 < length && sql.charAt(i + 1) == ':') {
                translated.append("::");
                i += 2;
                continue;
            }
            if (c == ':' && i + 1 < length && (Character.isLetter(sql.charAt(i + 1)) || sql.charAt(i + 1) == '_')) {
                int start = i + 1;
                int end = start;
                while (end < length && (Character.isLetterOrDigit(sql.charAt(end)) || sql.charAt(end) == '_')) {
                    end++;
                }
                paramNames.add(sql.substring(start, end));
                translated.append('?');
                i = end;
            } else {
                translated.append(c);
                i++;
            }
        }
        return new Translated(translated.toString(), paramNames);
    }

    static PreparedStatement prepare(Connection connection, String sql, Map<String, Object> params) throws SQLException {
        Translated translated = translate(sql);
        PreparedStatement statement = connection.prepareStatement(translated.sql());
        List<String> paramNames = translated.paramNames();
        for (int i = 0; i < paramNames.size(); i++) {
            statement.setObject(i + 1, params.get(paramNames.get(i)));
        }
        return statement;
    }

    static List<Row> toRows(ResultSet resultSet) throws SQLException {
        List<Row> rows = new ArrayList<>();
        ResultSetMetaData metaData = resultSet.getMetaData();
        int columnCount = metaData.getColumnCount();
        while (resultSet.next()) {
            Map<String, Object> values = new LinkedHashMap<>();
            for (int col = 1; col <= columnCount; col++) {
                values.put(metaData.getColumnLabel(col).toLowerCase(java.util.Locale.ROOT), resultSet.getObject(col));
            }
            rows.add(new Row(values));
        }
        return rows;
    }
}
