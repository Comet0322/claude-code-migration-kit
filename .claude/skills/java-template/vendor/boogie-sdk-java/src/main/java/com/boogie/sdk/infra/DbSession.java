package com.boogie.sdk.infra;

import com.boogie.sdk.core.InfraException;

import java.sql.Connection;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.util.List;
import java.util.Map;

/**
 * DbSession stub. See boogie-sdk-api.md section 5.2 (infra).
 * Skeleton only — implemented during the Phase 1 TDD loop for the `infra` module.
 *
 * Wraps the same JDBC {@link Connection} that {@link DbClient#transaction}
 * is managing, so all work done through a session participates in that
 * single transaction (see {@link DbClient} for commit/rollback handling).
 */
public class DbSession {

    private final Connection connection;

    DbSession(Connection connection) {
        this.connection = connection;
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
}
