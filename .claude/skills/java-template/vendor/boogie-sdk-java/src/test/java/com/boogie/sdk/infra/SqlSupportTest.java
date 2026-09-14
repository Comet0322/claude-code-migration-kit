package com.boogie.sdk.infra;

import org.junit.jupiter.api.Test;

import java.util.List;

import static org.junit.jupiter.api.Assertions.assertEquals;

/**
 * Regression tests for {@link SqlSupport#translate(String)}.
 *
 * These pin down that the {@code :name} scanner is aware of single-quoted
 * string-literal context: a {@code :letter} sequence inside a string
 * literal must never be mistaken for a bind parameter (that would emit a
 * phantom {@code ?} the JDBC driver doesn't count as a real parameter,
 * silently desynchronizing parameter order/count for every real
 * parameter after it), and a {@code ::} cast pair must be copied through
 * unchanged rather than having its second colon read as a parameter
 * start.
 */
class SqlSupportTest {

    @Test
    void plainNamedParameterIsTranslatedToAPositionalPlaceholder() {
        SqlSupport.Translated translated = SqlSupport.translate("SELECT * FROM users WHERE id = :id");

        assertEquals("SELECT * FROM users WHERE id = ?", translated.sql());
        assertEquals(List.of("id"), translated.paramNames());
    }

    @Test
    void colonLetterInsideAStringLiteralIsNotTreatedAsAParameter() {
        String sql = "SELECT * FROM users WHERE label = 'Status:Active' AND id = :id";

        SqlSupport.Translated translated = SqlSupport.translate(sql);

        assertEquals("SELECT * FROM users WHERE label = 'Status:Active' AND id = ?", translated.sql());
        assertEquals(List.of("id"), translated.paramNames());
    }

    @Test
    void windowsPathStyleColonInAStringLiteralIsLeftAlone() {
        String sql = "SELECT * FROM files WHERE path = 'C:Windows' AND owner = :owner";

        SqlSupport.Translated translated = SqlSupport.translate(sql);

        assertEquals("SELECT * FROM files WHERE path = 'C:Windows' AND owner = ?", translated.sql());
        assertEquals(List.of("owner"), translated.paramNames());
    }

    @Test
    void escapedQuoteInsideAStringLiteralDoesNotEndTheStringEarly() {
        String sql = "SELECT * FROM users WHERE note = 'it''s :fine' AND id = :id";

        SqlSupport.Translated translated = SqlSupport.translate(sql);

        assertEquals("SELECT * FROM users WHERE note = 'it''s :fine' AND id = ?", translated.sql());
        assertEquals(List.of("id"), translated.paramNames());
    }

    @Test
    void doubleColonCastSyntaxIsCopiedThroughUnchanged() {
        String sql = "SELECT CAST(x AS INT)::text FROM t WHERE id = :id";

        SqlSupport.Translated translated = SqlSupport.translate(sql);

        assertEquals("SELECT CAST(x AS INT)::text FROM t WHERE id = ?", translated.sql());
        assertEquals(List.of("id"), translated.paramNames());
    }

    @Test
    void multipleNamedParametersAreCapturedInOrder() {
        String sql = "INSERT INTO users (id, name, balance) VALUES (:id, :name, :balance)";

        SqlSupport.Translated translated = SqlSupport.translate(sql);

        assertEquals("INSERT INTO users (id, name, balance) VALUES (?, ?, ?)", translated.sql());
        assertEquals(List.of("id", "name", "balance"), translated.paramNames());
    }
}
