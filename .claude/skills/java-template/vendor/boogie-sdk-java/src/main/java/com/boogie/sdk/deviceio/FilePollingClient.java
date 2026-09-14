package com.boogie.sdk.deviceio;

import java.io.IOException;
import java.io.UncheckedIOException;
import java.nio.file.DirectoryStream;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;
import java.util.function.Consumer;

/**
 * FilePollingClient stub. See boogie-sdk-api.md section 5.3 (deviceio).
 * Skeleton only — implemented during the Phase 1 TDD loop for the `deviceio` module.
 */
public class FilePollingClient {
    public void watch(Path dir, String pattern, Consumer<Path> handler) {
        for (Path match : pollOnce(dir, pattern)) {
            handler.accept(match);
        }
    }

    public List<Path> pollOnce(Path dir, String pattern) {
        List<Path> matches = new ArrayList<>();
        try (DirectoryStream<Path> stream = Files.newDirectoryStream(dir, pattern)) {
            for (Path entry : stream) {
                matches.add(entry);
            }
        } catch (IOException e) {
            throw new UncheckedIOException(e);
        }
        return matches;
    }
}
