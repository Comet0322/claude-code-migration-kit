package com.boogie.sdk.infra;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.util.ArrayList;
import java.util.List;

import static org.junit.jupiter.api.Assertions.assertArrayEquals;
import static org.junit.jupiter.api.Assertions.assertDoesNotThrow;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

/**
 * Tests for QueueClient. See boogie-sdk-api.md section 5.2 (infra).
 *
 * Conventions this test file pins down (none exist yet beyond the public
 * method shapes):
 *
 * - Synchronous in-memory pub/sub fake: {@code publish} immediately
 *   invokes every currently-registered subscriber's handler for that
 *   topic, on the calling thread, before {@code publish} returns (no
 *   background delivery, no buffering/replay of messages published before
 *   a subscription existed).
 * - {@code subscribe} returns a {@link Subscription} whose
 *   {@code unsubscribe()} stops future delivery to that one handler only
 *   — other subscribers on the same topic are unaffected.
 * - Topics are isolated: publishing to one topic never invokes a handler
 *   registered on a different topic.
 */
class QueueClientTest {

    private QueueClient client;

    @BeforeEach
    void setUp() {
        client = new QueueClient();
    }

    @Test
    void publishWithNoSubscribersDoesNotThrow() {
        assertDoesNotThrow(() -> client.publish("topic", "hi".getBytes()));
    }

    @Test
    void publishDeliversToASingleSubscriberSynchronously() {
        List<Message> received = new ArrayList<>();
        client.subscribe("topic", received::add);

        client.publish("topic", "hello".getBytes());

        assertEquals(1, received.size());
        assertEquals("topic", received.get(0).topic());
        assertArrayEquals("hello".getBytes(), received.get(0).body());
    }

    @Test
    void publishDeliversToEveryRegisteredSubscriber() {
        List<Message> a = new ArrayList<>();
        List<Message> b = new ArrayList<>();
        client.subscribe("topic", a::add);
        client.subscribe("topic", b::add);

        client.publish("topic", "hi".getBytes());

        assertEquals(1, a.size());
        assertEquals(1, b.size());
    }

    @Test
    void subscribersOnDifferentTopicsAreIsolated() {
        List<Message> topicA = new ArrayList<>();
        List<Message> topicB = new ArrayList<>();
        client.subscribe("topic-a", topicA::add);
        client.subscribe("topic-b", topicB::add);

        client.publish("topic-a", "hi".getBytes());

        assertEquals(1, topicA.size());
        assertTrue(topicB.isEmpty());
    }

    @Test
    void unsubscribeStopsFutureDeliveryToThatHandler() {
        List<Message> received = new ArrayList<>();
        Subscription subscription = client.subscribe("topic", received::add);

        client.publish("topic", "one".getBytes());
        subscription.unsubscribe();
        client.publish("topic", "two".getBytes());

        assertEquals(1, received.size());
        assertArrayEquals("one".getBytes(), received.get(0).body());
    }

    @Test
    void unsubscribeDoesNotAffectOtherSubscribersOnTheSameTopic() {
        List<Message> a = new ArrayList<>();
        List<Message> b = new ArrayList<>();
        Subscription subscriptionA = client.subscribe("topic", a::add);
        client.subscribe("topic", b::add);

        subscriptionA.unsubscribe();
        client.publish("topic", "hi".getBytes());

        assertTrue(a.isEmpty());
        assertEquals(1, b.size());
    }

    @Test
    void messagesPublishedBeforeASubscriptionExistsAreNotReplayed() {
        client.publish("topic", "early".getBytes());

        List<Message> received = new ArrayList<>();
        client.subscribe("topic", received::add);

        assertTrue(received.isEmpty());
    }

    @Test
    void multipleMessagesAreDeliveredInPublishOrder() {
        List<byte[]> received = new ArrayList<>();
        client.subscribe("topic", m -> received.add(m.body()));

        client.publish("topic", "1".getBytes());
        client.publish("topic", "2".getBytes());
        client.publish("topic", "3".getBytes());

        assertEquals(3, received.size());
        assertArrayEquals("1".getBytes(), received.get(0));
        assertArrayEquals("2".getBytes(), received.get(1));
        assertArrayEquals("3".getBytes(), received.get(2));
    }
}
