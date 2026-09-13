package com.company.corplib.db;

import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.ResultSetMetaData;
import java.sql.SQLException;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * Minimal real implementation for migration-kit test infrastructure.
 * Backed by SQLite instead of the real MS SQL Server the domain skills
 * describe — enough to make generated code actually compile, run, and
 * be tested against. Not production code.
 */
public class Database {

    private final String dsn;

    private Database(String dsn) {
        this.dsn = dsn;
    }

    public static Database fromEnv() {
        String dsn = System.getenv("CORPLIB_DB_DSN");
        if (dsn == null || dsn.isBlank()) {
            dsn = "corplib.sqlite3";
        }
        return new Database(dsn);
    }

    private Connection connect() throws SQLException {
        return DriverManager.getConnection("jdbc:sqlite:" + dsn);
    }

    public Session session() {
        try {
            return new Session(connect());
        } catch (SQLException e) {
            throw new RuntimeException(e);
        }
    }

    public Transaction transaction() {
        try {
            Connection conn = connect();
            conn.setAutoCommit(false);
            return new Transaction(conn);
        } catch (SQLException e) {
            throw new RuntimeException(e);
        }
    }

    /** `:name` placeholders translate to `?` in declaration order. */
    public static class Session implements AutoCloseable {
        final Connection conn;

        Session(Connection conn) {
            this.conn = conn;
        }

        public List<Map<String, Object>> fetchAll(String sql, Map<String, Object> params) {
            try (PreparedStatement ps = prepare(sql, params);
                 ResultSet rs = ps.executeQuery()) {
                ResultSetMetaData meta = rs.getMetaData();
                List<Map<String, Object>> rows = new ArrayList<>();
                while (rs.next()) {
                    Map<String, Object> row = new LinkedHashMap<>();
                    for (int i = 1; i <= meta.getColumnCount(); i++) {
                        row.put(meta.getColumnLabel(i), rs.getObject(i));
                    }
                    rows.add(row);
                }
                return rows;
            } catch (SQLException e) {
                throw new RuntimeException(e);
            }
        }

        public Map<String, Object> fetchOne(String sql, Map<String, Object> params) {
            List<Map<String, Object>> rows = fetchAll(sql, params);
            return rows.isEmpty() ? null : rows.get(0);
        }

        public void execute(String sql, Map<String, Object> params) {
            try (PreparedStatement ps = prepare(sql, params)) {
                ps.executeUpdate();
            } catch (SQLException e) {
                throw new RuntimeException(e);
            }
        }

        private PreparedStatement prepare(String sql, Map<String, Object> params) throws SQLException {
            List<String> order = new ArrayList<>();
            StringBuilder translated = new StringBuilder();
            int i = 0;
            while (i < sql.length()) {
                char c = sql.charAt(i);
                if (c == ':') {
                    int j = i + 1;
                    while (j < sql.length() && (Character.isLetterOrDigit(sql.charAt(j)) || sql.charAt(j) == '_')) {
                        j++;
                    }
                    order.add(sql.substring(i + 1, j));
                    translated.append('?');
                    i = j;
                } else {
                    translated.append(c);
                    i++;
                }
            }
            PreparedStatement ps = conn.prepareStatement(translated.toString());
            for (int k = 0; k < order.size(); k++) {
                ps.setObject(k + 1, params == null ? null : params.get(order.get(k)));
            }
            return ps;
        }

        @Override
        public void close() {
            try {
                conn.close();
            } catch (SQLException ignored) {
            }
        }
    }

    public static class Transaction extends Session {
        private boolean committed = false;

        Transaction(Connection conn) {
            super(conn);
        }

        public void commit() {
            try {
                conn.commit();
                committed = true;
            } catch (SQLException e) {
                throw new RuntimeException(e);
            }
        }

        @Override
        public void close() {
            try {
                if (!committed) {
                    conn.rollback();
                }
            } catch (SQLException ignored) {
            } finally {
                super.close();
            }
        }
    }
}
