package com.boogie.sdk.infra;

import java.util.List;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.CopyOnWriteArrayList;
import java.util.function.Consumer;

/**
 * QueueClient stub. See boogie-sdk-api.md section 5.2 (infra).
 * Skeleton only — implemented during the Phase 1 TDD loop for the `infra` module.
 */
public class QueueClient {

    private final Map<String, CopyOnWriteArrayList<Consumer<Message>>> subscribersByTopic = new ConcurrentHashMap<>();

    public void publish(String topic, byte[] message) {
        List<Consumer<Message>> subscribers = subscribersByTopic.get(topic);
        if (subscribers == null) {
            return;
        }
        Message envelope = new Message(topic, message);
        for (Consumer<Message> handler : subscribers) {
            handler.accept(envelope);
        }
    }

    public Subscription subscribe(String topic, Consumer<Message> handler) {
        CopyOnWriteArrayList<Consumer<Message>> subscribers =
                subscribersByTopic.computeIfAbsent(topic, t -> new CopyOnWriteArrayList<>());
        subscribers.add(handler);
        return () -> subscribers.remove(handler);
    }
}
