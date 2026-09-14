package com.boogie.sdk.deviceio;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;
import java.util.stream.Collectors;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

/**
 * Tests for FilePollingClient. See boogie-sdk-api.md section 5.3 (deviceio).
 *
 * <p>{@code pollOnce(dir, pattern)} is a straightforward, real one-shot glob
 * against a real directory (via {@link Files#newDirectoryStream(Path,
 * String)}, whose {@code pattern} argument is a glob syntax path matcher) —
 * no fakery needed, so it is tested with real files under {@code @TempDir}.
 * It does not recurse into subdirectories (a directory stream lists only the
 * immediate children of {@code dir}).
 *
 * <p>{@code watch(dir, pattern, handler)} convention (invented here, since a
 * real implementation would poll on a background interval and that isn't
 * deterministically testable): mirroring the already-built Python port's
 * {@code FilePollingClient.watch}, <b>{@code watch()} performs exactly one
 * synchronous poll pass at call time</b> — it is not a background thread or
 * loop. It calls {@code handler.accept(path)} exactly once per
 * currently-matching file (as of that single poll, in the same order as
 * {@code pollOnce} would return them), then returns. This makes it behave,
 * for a single call, like {@code pollOnce} plus a callback per match — fully
 * deterministic and synchronous for tests. Calling {@code watch()} again
 * later re-polls from scratch (no "already seen" bookkeeping).
 */
class FilePollingClientTest {

    private FilePollingClient client;

    @BeforeEach
    void setUp() {
        client = new FilePollingClient();
    }

    // -- pollOnce ------------------------------------------------------------

    @Test
    void pollOnceFindsMatchingFiles(@TempDir Path tempDir) throws IOException {
        Files.writeString(tempDir.resolve("a.csv"), "1,2,3");
        Files.writeString(tempDir.resolve("b.csv"), "4,5,6");
        Files.writeString(tempDir.resolve("c.txt"), "ignore me");

        List<Path> matches = client.pollOnce(tempDir, "*.csv");

        assertEquals(List.of("a.csv", "b.csv"), namesSorted(matches));
    }

    @Test
    void pollOnceReturnsEmptyListWhenNoMatches(@TempDir Path tempDir) throws IOException {
        Files.writeString(tempDir.resolve("readme.md"), "nothing here");

        List<Path> matches = client.pollOnce(tempDir, "*.csv");

        assertTrue(matches.isEmpty());
    }

    @Test
    void pollOnceReturnsPathsPointingIntoDirectory(@TempDir Path tempDir) throws IOException {
        Path target = tempDir.resolve("data.csv");
        Files.writeString(target, "x");

        List<Path> matches = client.pollOnce(tempDir, "*.csv");

        assertEquals(1, matches.size());
        assertEquals(target.toRealPath(), matches.get(0).toRealPath());
    }

    @Test
    void pollOnceDoesNotRecurseIntoSubdirectories(@TempDir Path tempDir) throws IOException {
        Files.writeString(tempDir.resolve("top.csv"), "x");
        Path sub = Files.createDirectory(tempDir.resolve("sub"));
        Files.writeString(sub.resolve("nested.csv"), "y");

        List<Path> matches = client.pollOnce(tempDir, "*.csv");

        assertEquals(List.of("top.csv"), namesSorted(matches));
    }

    // -- watch (one-shot synchronous poll convention) --------------------------

    @Test
    void watchCallsHandlerOncePerMatchingFile(@TempDir Path tempDir) throws IOException {
        Files.writeString(tempDir.resolve("a.csv"), "1");
        Files.writeString(tempDir.resolve("b.csv"), "2");

        List<Path> seen = new ArrayList<>();
        client.watch(tempDir, "*.csv", seen::add);

        assertEquals(List.of("a.csv", "b.csv"), namesSorted(seen));
    }

    @Test
    void watchDoesNotCallHandlerForNonMatchingFiles(@TempDir Path tempDir) throws IOException {
        Files.writeString(tempDir.resolve("a.csv"), "1");
        Files.writeString(tempDir.resolve("skip.txt"), "2");

        List<Path> seen = new ArrayList<>();
        client.watch(tempDir, "*.csv", seen::add);

        assertEquals(List.of("a.csv"), namesSorted(seen));
    }

    @Test
    void watchWithNoMatchesNeverCallsHandler(@TempDir Path tempDir) {
        List<Path> calls = new ArrayList<>();
        client.watch(tempDir, "*.csv", calls::add);

        assertTrue(calls.isEmpty());
    }

    @Test
    void watchReturnsAfterSinglePassAndDoesNotBlock(@TempDir Path tempDir) throws IOException {
        // Documents the deterministic "one poll pass, then return" convention:
        // calling watch() twice in a row (as if driving it manually) sees the
        // same file both times rather than hanging or requiring a stop signal.
        Files.writeString(tempDir.resolve("a.csv"), "1");

        List<Path> firstSeen = new ArrayList<>();
        List<Path> secondSeen = new ArrayList<>();
        client.watch(tempDir, "*.csv", firstSeen::add);
        client.watch(tempDir, "*.csv", secondSeen::add);

        assertEquals(1, firstSeen.size());
        assertEquals(1, secondSeen.size());
    }

    private static List<String> namesSorted(List<Path> paths) {
        return paths.stream()
                .map(p -> p.getFileName().toString())
                .sorted()
                .collect(Collectors.toList());
    }
}
