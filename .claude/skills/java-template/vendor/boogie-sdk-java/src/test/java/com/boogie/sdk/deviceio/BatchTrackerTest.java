package com.boogie.sdk.deviceio;

import com.boogie.sdk.core.NotFoundException;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.time.Instant;
import java.util.List;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;

/**
 * Tests for BatchTracker. See boogie-sdk-api.md section 5.3 (deviceio).
 *
 * <p>Conventions invented for this module, mirroring the already-built
 * Python port's {@code BatchTracker}:
 *
 * <ul>
 *   <li><b>{@code createBatch(batchId)} records an initial {@code
 *       "created"} {@link BatchEvent}.</b> {@code getHistory(batchId)}
 *       therefore always returns at least one event for a known batch —
 *       the creation itself is part of the history, not just a side effect
 *       that sets up empty state.
 *   <li><b>{@code getHistory} returns events in chronological order</b>
 *       (creation first, then each {@code updateStatus} call in the order
 *       it was made).
 *   <li><b>{@code updateStatus} on an unknown {@code batchId} throws
 *       {@link NotFoundException}.</b>
 *   <li><b>{@code getHistory} on an unknown {@code batchId} throws {@link
 *       NotFoundException}.</b> A batch must be created via {@code
 *       createBatch} before either method accepts its id.
 * </ul>
 */
class BatchTrackerTest {

    private BatchTracker tracker;

    @BeforeEach
    void setUp() {
        tracker = new BatchTracker();
    }

    // -- createBatch / getHistory: created event ------------------------------

    @Test
    void createBatchRecordsInitialCreatedEvent() {
        tracker.createBatch("batch-1");

        List<BatchEvent> history = tracker.getHistory("batch-1");

        assertEquals(1, history.size());
        assertEquals("batch-1", history.get(0).batchId());
        assertEquals("created", history.get(0).status());
    }

    @Test
    void getHistoryIsChronologicalIncludingCreationFirst() {
        tracker.createBatch("batch-1");
        tracker.updateStatus("batch-1", "running");
        tracker.updateStatus("batch-1", "completed");

        List<BatchEvent> history = tracker.getHistory("batch-1");

        assertEquals(List.of("created", "running", "completed"),
                history.stream().map(BatchEvent::status).toList());
    }

    @Test
    void getHistoryEventsAreNonDecreasingInTime() {
        tracker.createBatch("batch-1");
        tracker.updateStatus("batch-1", "running");
        tracker.updateStatus("batch-1", "completed");

        List<Instant> timestamps = tracker.getHistory("batch-1").stream().map(BatchEvent::at).toList();

        List<Instant> sorted = timestamps.stream().sorted().toList();
        assertEquals(sorted, timestamps);
    }

    @Test
    void updateStatusAppendsEventWithGivenStatus() {
        tracker.createBatch("batch-1");
        tracker.updateStatus("batch-1", "paused");

        List<BatchEvent> history = tracker.getHistory("batch-1");

        assertEquals("paused", history.get(history.size() - 1).status());
        assertEquals("batch-1", history.get(history.size() - 1).batchId());
    }

    @Test
    void multipleBatchesHaveIndependentHistories() {
        tracker.createBatch("batch-1");
        tracker.createBatch("batch-2");
        tracker.updateStatus("batch-1", "running");

        List<BatchEvent> history1 = tracker.getHistory("batch-1");
        List<BatchEvent> history2 = tracker.getHistory("batch-2");

        assertEquals(List.of("created", "running"), history1.stream().map(BatchEvent::status).toList());
        assertEquals(List.of("created"), history2.stream().map(BatchEvent::status).toList());
    }

    // -- NotFoundException for unknown batchId --------------------------------

    @Test
    void updateStatusOnUnknownBatchThrowsNotFoundException() {
        assertThrows(NotFoundException.class, () -> tracker.updateStatus("does-not-exist", "running"));
    }

    @Test
    void getHistoryOnUnknownBatchThrowsNotFoundException() {
        assertThrows(NotFoundException.class, () -> tracker.getHistory("does-not-exist"));
    }
}
