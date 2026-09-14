package com.boogie.sdk;

import com.boogie.sdk.deviceio.BatchTracker;
import com.boogie.sdk.deviceio.DeviceProtocolClient;
import com.boogie.sdk.deviceio.FilePollingClient;
import com.boogie.sdk.deviceio.FlatFileParser;
import com.boogie.sdk.deviceio.ReportGenerator;
import com.boogie.sdk.deviceio.ShiftCalendar;
import com.boogie.sdk.deviceio.SpcAnalyzer;

/** Groups the deviceio module's several clients under {@code sdk.deviceIo().xxx()}. */
public final class DeviceIoNamespace {
    private final LazyRegistry registry = new LazyRegistry();

    public DeviceProtocolClient protocolClient() {
        return registry.get("protocolClient", DeviceProtocolClient::new);
    }

    public FilePollingClient filePolling() {
        return registry.get("filePolling", FilePollingClient::new);
    }

    public FlatFileParser flatFileParser() {
        return registry.get("flatFileParser", FlatFileParser::new);
    }

    public ReportGenerator reportGenerator() {
        return registry.get("reportGenerator", ReportGenerator::new);
    }

    public BatchTracker batchTracker() {
        return registry.get("batchTracker", BatchTracker::new);
    }

    public ShiftCalendar shiftCalendar() {
        return registry.get("shiftCalendar", ShiftCalendar::new);
    }

    public SpcAnalyzer spcAnalyzer() {
        return registry.get("spcAnalyzer", SpcAnalyzer::new);
    }
}
