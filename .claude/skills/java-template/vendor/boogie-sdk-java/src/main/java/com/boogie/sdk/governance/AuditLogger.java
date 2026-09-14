package com.boogie.sdk.governance;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;

/**
 * AuditLogger stub. See boogie-sdk-api.md section 5.5 (governance).
 * Skeleton only — implemented during the Phase 1 TDD loop for the `governance` module.
 *
 * <p>Additive member beyond the design doc's method-only sketch, needed
 * for the governance test suite to compile (see AuditLoggerTest for the
 * full conventions it establishes, mirroring the already-built Python
 * port's {@code records} list): {@link #records()} returns every {@link
 * AuditRecord} appended by {@link #record(String, String, String,
 * String)}, in call order, and never clears it.
 */
public class AuditLogger {

    public record AuditRecord(String actor, String action, String resource, String result) {
    }

    private final List<AuditRecord> records = Collections.synchronizedList(new ArrayList<>());

    public void record(String actor, String action, String resource, String result) {
        records.add(new AuditRecord(actor, action, resource, result));
    }

    public List<AuditRecord> records() {
        return new ArrayList<>(records);
    }
}
