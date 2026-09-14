package com.boogie.sdk.infra;

import com.boogie.sdk.core.InfraException;

import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import java.util.function.Function;

/**
 * DbClient stub. See boogie-sdk-api.md section 5.2 (infra).
 * Skeleton only — implemented during the Phase 1 TDD loop for the `infra` module.
 *
 * Each instance owns a private, independent H2 in-memory database (a
 * uniquely named {@code jdbc:h2:mem:} database per instance) and keeps a
 * single JDBC connection open for its lifetime.
 */
public class DbClient {

    private final Connection connection;

    public DbClient() {
        String databaseName = "dbclient-" + UUID.randomUUID();
        try {
            this.connection = DriverManager.getConnection(
                    "jdbc:h2:mem:" + databaseName + ";DB_CLOSE_DELAY=-1");
        } catch (SQLException e) {
            throw new InfraException("failed to open in-memory database", e);
        }
    }

    public List<Row> query(String sql, Map<String, Object> params) {
        try (PreparedStatement statement = SqlSupport.prepare(connection, sql, params);
             ResultSet resultSet = statement.executeQuery()) {
            return SqlSupport.toRows(resultSet);
        } catch (SQLException e) {
            throw new InfraException("query failed: " + sql, e);
        }
    }

    public int execute(String sql, Map<String, Object> params) {
        try (PreparedStatement statement = SqlSupport.prepare(connection, sql, params)) {
            return statement.executeUpdate();
        } catch (SQLException e) {
            throw new InfraException("execute failed: " + sql, e);
        }
    }

    public <T> T transaction(Function<DbSession, T> work) {
        try {
            connection.setAutoCommit(false);
        } catch (SQLException e) {
            throw new InfraException("failed to start transaction", e);
        }

        try {
            T result = work.apply(new DbSession(connection));
            connection.commit();
            return result;
        } catch (RuntimeException | Error e) {
            rollbackQuietly();
            throw e;
        } catch (SQLException e) {
            rollbackQuietly();
            throw new InfraException("failed to commit transaction", e);
        } finally {
            restoreAutoCommitQuietly();
        }
    }

    private void rollbackQuietly() {
        try {
            connection.rollback();
        } catch (SQLException ignored) {
            // best effort: original failure already propagating
        }
    }

    private void restoreAutoCommitQuietly() {
        try {
            connection.setAutoCommit(true);
        } catch (SQLException ignored) {
            // best effort: original result/failure already propagating
        }
    }
}
