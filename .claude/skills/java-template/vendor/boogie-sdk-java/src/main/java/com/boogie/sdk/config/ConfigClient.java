package com.boogie.sdk.config;

import java.util.ArrayList;
import java.util.List;
import java.util.function.Consumer;

/**
 * Simulated remote config-center client with hot-reload callbacks.
 * See boogie-sdk-api.md section 4 and section 1 ("遠端設定中心 client(hot reload)").
 */
public final class ConfigClient {
    private BoogieConfig config;
    private final List<Consumer<BoogieConfig>> listeners = new ArrayList<>();

    public ConfigClient(BoogieConfig config) {
        this.config = config;
    }

    public String get(String key, String defaultValue) {
        return config.get(key, defaultValue);
    }

    public void reload() {
        reload(null);
    }

    public void reload(String path) {
        this.config = path == null ? BoogieConfig.load() : BoogieConfig.load(path);
        for (Consumer<BoogieConfig> listener : listeners) {
            listener.accept(this.config);
        }
    }

    public void onChange(Consumer<BoogieConfig> listener) {
        listeners.add(listener);
    }
}
