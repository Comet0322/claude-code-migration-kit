package com.boogie.sdk.governance;

import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

/**
 * FeatureFlagClient stub. See boogie-sdk-api.md section 5.5 (governance).
 * Skeleton only — implemented during the Phase 1 TDD loop for the `governance` module.
 *
 * <p>Additive members beyond the design doc's method-only sketch, needed
 * for the governance test suite to compile (see FeatureFlagClientTest for
 * the full conventions they establish, mirroring the already-built Python
 * port's {@code FeatureFlagClient}):
 *
 * <ul>
 *   <li>{@link #FeatureFlagClient(boolean)} — the fallback value returned
 *       for any flag key that has never been explicitly configured.
 *   <li>{@link #FeatureFlagClient()} — no-arg convenience constructor,
 *       equivalent to {@code FeatureFlagClient(false)}; also keeps the
 *       pre-existing {@code BoogieSdk.featureFlag()} facade method /
 *       {@code BoogieSdkSmokeTest} compiling and constructing
 *       successfully, since neither constructor throws (only
 *       {@code isEnabled}/{@code setFlag} do, as before).
 *   <li>{@link #setFlag(String, boolean)} — configures a specific flag's
 *       value, overriding the constructor default for that key.
 * </ul>
 */
public class FeatureFlagClient {

    private final boolean defaultEnabled;
    private final Map<String, Boolean> overrides = new ConcurrentHashMap<>();

    public FeatureFlagClient() {
        this(false);
    }

    public FeatureFlagClient(boolean defaultEnabled) {
        this.defaultEnabled = defaultEnabled;
    }

    public boolean isEnabled(String flagKey, Map<String, Object> context) {
        return overrides.getOrDefault(flagKey, defaultEnabled);
    }

    public void setFlag(String flagKey, boolean enabled) {
        overrides.put(flagKey, enabled);
    }
}
