package com.boogie.sdk.deviceio;

import com.boogie.sdk.core.NotFoundException;

import java.time.Instant;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * BatchTracker stub. See boogie-sdk-api.md section 5.3 (deviceio).
 * Skeleton only — implemented during the Phase 1 TDD loop for the `deviceio` module.
 */
public class BatchTracker {

    private final Map<String, List<BatchEvent>> histories = new LinkedHashMap<>();

    public void createBatch(String batchId) {
        List<BatchEvent> history = new ArrayList<>();
        history.add(new BatchEvent(batchId, "created", Instant.now()));
        histories.put(batchId, history);
    }

    public void updateStatus(String batchId, String status) {
        List<BatchEvent> history = histories.get(batchId);
        if (history == null) {
            throw new NotFoundException("unknown batch: " + batchId);
        }
        history.add(new BatchEvent(batchId, status, Instant.now()));
    }

    public List<BatchEvent> getHistory(String batchId) {
        List<BatchEvent> history = histories.get(batchId);
        if (history == null) {
            throw new NotFoundException("unknown batch: " + batchId);
        }
        return List.copyOf(history);
    }
}
