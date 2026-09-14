package com.boogie.sdk.governance;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.Arguments;
import org.junit.jupiter.params.provider.MethodSource;

import java.util.HashMap;
import java.util.Map;
import java.util.stream.Stream;

import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

/**
 * Tests for FeatureFlagClient. See boogie-sdk-api.md section 5.5
 * (governance).
 *
 * <p>The design doc only documents {@code boolean isEnabled(flagKey,
 * context)} with no way to configure a flag's state and no real flag
 * service behind this fake. This test file pins down the additive,
 * testable conventions invented to make the fake usable, mirroring the
 * already-built Python port's {@code FeatureFlagClient}:
 *
 * <ul>
 *   <li><b>Constructors (additive, not in the design doc):</b> {@code
 *       FeatureFlagClient(boolean defaultEnabled)} sets the fallback
 *       value for any flag key that has never been explicitly configured;
 *       {@code FeatureFlagClient()} is a no-arg convenience constructor
 *       equivalent to {@code FeatureFlagClient(false)}.
 *   <li><b>{@code setFlag(String flagKey, boolean enabled)} (additive,
 *       not in the design doc):</b> configures a specific flag's value.
 *       Once set, that flag key's {@code isEnabled(...)} reflects the
 *       configured value regardless of the client's {@code
 *       defaultEnabled}, and can be flipped again by calling {@code
 *       setFlag} again with a different value.
 *   <li><b>{@code context}:</b> accepted by {@code isEnabled} per the
 *       design-doc signature, but this fake has no rule engine — it is
 *       simply ignored. Passing any {@code Map} (or {@code null}) must not
 *       throw and must not change the result.
 * </ul>
 *
 * <p>{@code isEnabled}/{@code setFlag} and both constructors currently
 * throw {@link UnsupportedOperationException} (skeleton stage) — every
 * test below is expected to fail with that exception until the
 * `implementer` stage fills in real bodies; that failure mode is
 * expected/fine per the TDD pipeline.
 */
class FeatureFlagClientTest {

    @Test
    void unconfiguredFlagReturnsFalseByDefault() {
        FeatureFlagClient client = new FeatureFlagClient();
        assertFalse(client.isEnabled("unconfigured-flag", null));
    }

    @Test
    void unconfiguredFlagReturnsConfiguredDefaultEnabled() {
        FeatureFlagClient client = new FeatureFlagClient(true);
        assertTrue(client.isEnabled("unconfigured-flag", null));
    }

    @Test
    void setFlagTrueThenIsEnabledReflectsTrue() {
        FeatureFlagClient client = new FeatureFlagClient(false);
        client.setFlag("new-checkout", true);
        assertTrue(client.isEnabled("new-checkout", null));
    }

    @Test
    void setFlagFalseThenIsEnabledReflectsFalse() {
        FeatureFlagClient client = new FeatureFlagClient(true);
        client.setFlag("kill-switch", false);
        assertFalse(client.isEnabled("kill-switch", null));
    }

    @Test
    void setFlagCanBeFlippedBackAndForth() {
        FeatureFlagClient client = new FeatureFlagClient();
        client.setFlag("toggle", true);
        assertTrue(client.isEnabled("toggle", null));

        client.setFlag("toggle", false);
        assertFalse(client.isEnabled("toggle", null));
    }

    @Test
    void settingOneFlagDoesNotAffectOtherUnconfiguredFlags() {
        FeatureFlagClient client = new FeatureFlagClient(false);
        client.setFlag("flag-a", true);

        assertTrue(client.isEnabled("flag-a", null));
        assertFalse(client.isEnabled("flag-b", null));
    }

    static Stream<Arguments> contextValues() {
        Map<String, Object> populated = new HashMap<>();
        populated.put("userId", "u1");
        populated.put("region", "us");
        return Stream.of(
                Arguments.of((Map<String, Object>) null),
                Arguments.of(Map.of()),
                Arguments.of(populated));
    }

    @ParameterizedTest
    @MethodSource("contextValues")
    void contextParamIsAcceptedWithoutErrorAndDoesNotChangeResult(Map<String, Object> context) {
        FeatureFlagClient client = new FeatureFlagClient(true);
        assertTrue(client.isEnabled("some-flag", context));
    }
}
