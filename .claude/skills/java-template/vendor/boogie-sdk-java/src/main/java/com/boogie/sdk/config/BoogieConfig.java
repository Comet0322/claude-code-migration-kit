package com.boogie.sdk.config;

import java.io.IOException;
import java.io.InputStream;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.HashMap;
import java.util.Map;
import java.util.Properties;

/**
 * Immutable configuration snapshot loaded from a properties file + env var overrides.
 * See boogie-sdk-api.md section 4 (共用慣例).
 */
public final class BoogieConfig {
    private static final String ENV_PREFIX = "BOOGIE_";
    private static final String DEFAULT_CONFIG_FILE = "boogie-sdk.properties";

    private final Map<String, String> values;

    public BoogieConfig(Map<String, String> values) {
        this.values = Map.copyOf(values);
    }

    public static BoogieConfig load() {
        return load(DEFAULT_CONFIG_FILE);
    }

    public static BoogieConfig load(String path) {
        Map<String, String> values = new HashMap<>();
        Path configPath = Path.of(path);
        if (Files.exists(configPath)) {
            Properties props = new Properties();
            try (InputStream in = Files.newInputStream(configPath)) {
                props.load(in);
            } catch (IOException e) {
                throw new IllegalStateException("failed to read config file: " + path, e);
            }
            for (String name : props.stringPropertyNames()) {
                values.put(name, props.getProperty(name));
            }
        }
        for (Map.Entry<String, String> entry : System.getenv().entrySet()) {
            if (entry.getKey().startsWith(ENV_PREFIX)) {
                String key = entry.getKey().substring(ENV_PREFIX.length()).toLowerCase();
                values.put(key, entry.getValue());
            }
        }
        return new BoogieConfig(values);
    }

    public String get(String key, String defaultValue) {
        return values.getOrDefault(key, defaultValue);
    }

    public String get(String key) {
        return get(key, null);
    }

    public BoogieConfig withOverride(String key, String value) {
        Map<String, String> copy = new HashMap<>(values);
        copy.put(key, value);
        return new BoogieConfig(copy);
    }
}
