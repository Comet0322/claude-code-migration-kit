package com.boogie.sdk;

import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertSame;

import com.boogie.sdk.config.BoogieConfig;
import java.util.Map;
import org.junit.jupiter.api.Test;

/**
 * Phase 0 smoke test: the skeleton compiles and the facade wires every module.
 * Individual module behavior is covered by each module's own Phase 1 test suite.
 */
class BoogieSdkSmokeTest {

    @Test
    void facadeExposesEveryModuleWithoutError() {
        BoogieSdk sdk = BoogieSdk.init(new BoogieConfig(Map.of()));

        assertNotNull(sdk.config());
        assertNotNull(sdk.crypto());
        assertNotNull(sdk.secret());
        assertNotNull(sdk.token());
        assertNotNull(sdk.cert());
        assertNotNull(sdk.http());
        assertNotNull(sdk.db());
        assertNotNull(sdk.cache());
        assertNotNull(sdk.queue());
        assertNotNull(sdk.objectStorage());
        assertNotNull(sdk.serviceDiscovery());
        assertNotNull(sdk.scheduler());
        assertNotNull(sdk.deviceIo().protocolClient());
        assertNotNull(sdk.deviceIo().filePolling());
        assertNotNull(sdk.deviceIo().flatFileParser());
        assertNotNull(sdk.deviceIo().reportGenerator());
        assertNotNull(sdk.deviceIo().batchTracker());
        assertNotNull(sdk.deviceIo().shiftCalendar());
        assertNotNull(sdk.deviceIo().spcAnalyzer());
        assertNotNull(sdk.logger());
        assertNotNull(sdk.metrics());
        assertNotNull(sdk.tracer());
        assertNotNull(sdk.idGenerator());
        assertNotNull(sdk.featureFlag());
        assertNotNull(sdk.rateLimiter());
        assertNotNull(sdk.notification());
        assertNotNull(sdk.health());
        assertNotNull(sdk.audit());

        sdk.close();
    }

    @Test
    void facadeCachesClientInstances() {
        BoogieSdk sdk = BoogieSdk.init(new BoogieConfig(Map.of()));
        assertSame(sdk.crypto(), sdk.crypto());
        assertSame(sdk.deviceIo().spcAnalyzer(), sdk.deviceIo().spcAnalyzer());
    }
}
