package com.boogie.sdk.infra;

import com.boogie.sdk.core.InfraException;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.SQLException;
import java.util.List;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

/**
 * Tests for DbClient. See boogie-sdk-api.md section 5.2 (infra).
 *
 * Conventions this test file pins down (none exist yet beyond the public
 * method shapes):
 *
 * - Backing store: each {@code DbClient} instance owns a private,
 *   independent H2 (org.h2database:h2) in-memory database. H2 is added
 *   here as a test-scope Maven dependency (see pom.xml) purely so this
 *   file's fixture SQL (the DDL/DML constants below) can be validated
 *   directly against a real H2 engine in {@link #fixtureSqlIsValidH2Sql()}
 *   below, independently of DbClient's own (not-yet-built)
 *   implementation — so that a test failure here can never be misread as
 *   "the fixture SQL is wrong" once DbClient is implemented. Every other
 *   test in this file calls {@code DbClient} directly, never H2 itself.
 *   The implementer stage is expected to add H2 again as a compile-scope
 *   dependency for the real DbClient implementation.
 * - Named parameters: {@code query}/{@code execute} (and
 *   {@code DbSession.query}/{@code DbSession.execute} inside a
 *   transaction) take a {@code Map<String, Object>} of parameters bound
 *   against {@code :name}-style placeholders written directly in the SQL
 *   text (mirroring the Python port's sqlite3-style {@code :name}
 *   binding), which DbClient is expected to translate to the underlying
 *   JDBC {@code ?} placeholders using the map.
 * - {@code transaction(Function<DbSession, T> work)}: commits all of
 *   {@code work}'s changes if it returns normally, and rolls back all of
 *   {@code work}'s changes if it throws — the original exception
 *   propagates to the caller unwrapped.
 * - SQL-level failures (e.g. querying a table that doesn't exist) are
 *   wrapped in {@link InfraException} rather than letting a raw
 *   {@link java.sql.SQLException} escape.
 */
class DbClientTest {

    private static final String CREATE_USERS_SQL =
            "CREATE TABLE users (id INT PRIMARY KEY, name VARCHAR(100), balance INT)";
    private static final String INSERT_USER_SQL =
            "INSERT INTO users (id, name, balance) VALUES (:id, :name, :balance)";

    /**
     * Comparison fixture: verifies the DDL/DML this file relies on is
     * valid against a real, independent H2 engine before any test relies
     * on DbClient to run it — so a failure in the tests below can't be
     * misattributed to a typo in this file's own fixture SQL.
     */
    @BeforeAll
    static void fixtureSqlIsValidH2Sql() throws SQLException {
        try (Connection connection =
                     DriverManager.getConnection("jdbc:h2:mem:dbclienttest-fixture-check;DB_CLOSE_DELAY=-1")) {
            connection.createStatement().execute(CREATE_USERS_SQL);
            connection.createStatement().execute(
                    "INSERT INTO users (id, name, balance) VALUES (1, 'Ann', 100)");
        }
    }

    private DbClient client;

    @BeforeEach
    void setUp() {
        client = new DbClient();
    }

    private void createUsersTable(DbClient target) {
        target.execute(CREATE_USERS_SQL, Map.of());
    }

    private void insertUser(DbClient target, int id, String name, int balance) {
        target.execute(INSERT_USER_SQL, Map.of("id", id, "name", name, "balance", balance));
    }

    // -- execute -----------------------------------------------------------

    @Test
    void executeCreateTableReturnsZeroRowsAffected() {
        assertEquals(0, client.execute(CREATE_USERS_SQL, Map.of()));
    }

    @Test
    void executeInsertReturnsOneRowAffected() {
        createUsersTable(client);

        int affected = client.execute(INSERT_USER_SQL, Map.of("id", 1, "name", "Ann", "balance", 100));

        assertEquals(1, affected);
    }

    @Test
    void executeUpdateReturnsNumberOfMatchedRows() {
        createUsersTable(client);
        insertUser(client, 1, "Ann", 100);
        insertUser(client, 2, "Bob", 50);

        int affected = client.execute("UPDATE users SET balance = :balance", Map.of("balance", 0));

        assertEquals(2, affected);
    }

    // -- query ---------------------------------------------------------------

    @Test
    void queryReturnsTheInsertedRow() {
        createUsersTable(client);
        insertUser(client, 1, "Ann", 100);

        List<Row> rows = client.query("SELECT id, name, balance FROM users WHERE id = :id", Map.of("id", 1));

        assertEquals(1, rows.size());
        Row row = rows.get(0);
        assertEquals(1, ((Number) row.values().get("id")).intValue());
        assertEquals("Ann", row.values().get("name"));
        assertEquals(100, ((Number) row.values().get("balance")).intValue());
    }

    @Test
    void queryWithNoMatchesReturnsAnEmptyList() {
        createUsersTable(client);

        List<Row> rows = client.query("SELECT * FROM users WHERE id = :id", Map.of("id", 999));

        assertTrue(rows.isEmpty());
    }

    @Test
    void queryOnANonexistentTableThrowsInfraException() {
        assertThrows(InfraException.class, () -> client.query("SELECT * FROM ghost_table", Map.of()));
    }

    // -- transaction -----------------------------------------------------------

    @Test
    void transactionCommitsChangesWhenWorkReturnsNormally() {
        createUsersTable(client);

        String result = client.transaction(session -> {
            session.execute(INSERT_USER_SQL, Map.of("id", 1, "name", "Ann", "balance", 100));
            return "ok";
        });

        assertEquals("ok", result);
        assertEquals(1, client.query("SELECT * FROM users", Map.of()).size());
    }

    @Test
    void transactionRollsBackAllChangesWhenWorkThrows() {
        createUsersTable(client);
        insertUser(client, 1, "Ann", 100);

        class BoomException extends RuntimeException {
        }

        assertThrows(BoomException.class, () -> client.transaction(session -> {
            session.execute(INSERT_USER_SQL, Map.of("id", 2, "name", "Bob", "balance", 50));
            session.execute("UPDATE users SET balance = :balance WHERE id = :id", Map.of("id", 1, "balance", 0));
            throw new BoomException();
        }));

        List<Row> rows = client.query("SELECT * FROM users", Map.of());
        assertEquals(1, rows.size());
        assertEquals(100, ((Number) rows.get(0).values().get("balance")).intValue());
    }

    @Test
    void transactionWorkReceivesAUsableDbSession() {
        createUsersTable(client);
        insertUser(client, 1, "Ann", 100);

        List<Row> seen = client.transaction(session -> session.query("SELECT * FROM users", Map.of()));

        assertNotNull(seen);
        assertEquals(1, seen.size());
    }

    @Test
    void transactionReturnValuePropagatesToTheCaller() {
        createUsersTable(client);

        int returned = client.transaction(session -> 42);

        assertEquals(42, returned);
    }

    // -- instance isolation -----------------------------------------------------

    @Test
    void separateDbClientInstancesDoNotShareData() {
        createUsersTable(client);
        insertUser(client, 1, "Ann", 100);

        DbClient other = new DbClient();
        createUsersTable(other);

        assertTrue(other.query("SELECT * FROM users", Map.of()).isEmpty());
    }
}
