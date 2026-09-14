package com.boogie.sdk.config;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNull;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import org.junit.jupiter.api.Test;

class BoogieConfigTest {

    @Test
    void getReturnsDefaultWhenMissing() {
        BoogieConfig config = new BoogieConfig(Map.of());
        assertEquals("fallback", config.get("missing", "fallback"));
        assertNull(config.get("missing"));
    }

    @Test
    void withOverrideDoesNotMutateOriginal() {
        BoogieConfig config = new BoogieConfig(Map.of("a", "1"));
        BoogieConfig updated = config.withOverride("a", "2");
        assertEquals("1", config.get("a"));
        assertEquals("2", updated.get("a"));
    }

    @Test
    void configClientGetDelegatesToConfig() {
        ConfigClient client = new ConfigClient(new BoogieConfig(Map.of("k", "v")));
        assertEquals("v", client.get("k", null));
        assertEquals("d", client.get("missing", "d"));
    }

    @Test
    void configClientOnChangeIsInvokedOnReload(@org.junit.jupiter.api.io.TempDir java.nio.file.Path tmpDir)
            throws Exception {
        String originalDir = System.getProperty("user.dir");
        System.setProperty("user.dir", tmpDir.toString());
        try {
            java.nio.file.Path configFile = tmpDir.resolve("boogie-sdk.properties");
            java.nio.file.Files.writeString(configFile, "x=1\n");

            ConfigClient client = new ConfigClient(new BoogieConfig(Map.of()));
            List<BoogieConfig> seen = new ArrayList<>();
            client.onChange(seen::add);

            client.reload(configFile.toString());

            assertEquals(1, seen.size());
            assertEquals("1", seen.get(0).get("x"));
            assertEquals("1", client.get("x", null));
        } finally {
            System.setProperty("user.dir", originalDir);
        }
    }
}
