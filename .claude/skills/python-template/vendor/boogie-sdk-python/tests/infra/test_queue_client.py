"""Tests for QueueClient. See boogie-sdk-api.md (this skill's library doc) section 5.2.

Convention pinned down by this test file: `QueueClient` is a synchronous
in-memory pub/sub fake. `publish(topic, message)` immediately (in-process,
same call stack) invokes every currently-registered subscriber handler for
that topic with a `Message(topic=topic, body=message)`. `subscribe(topic,
handler)` returns a `Subscription`; calling `unsubscribe()` on it stops
future delivery to that handler (it does not retroactively undo past
deliveries, and does not affect other subscribers on the same topic).
Publishing to a topic with no subscribers is a no-op (does not raise).
"""

from __future__ import annotations

from boogie_sdk.infra.queue_client import Message, QueueClient


def test_publish_with_no_subscribers_does_not_raise() -> None:
    client = QueueClient()
    client.publish("orders", b"hello")  # should simply do nothing


def test_single_subscriber_receives_published_message() -> None:
    client = QueueClient()
    received: list[Message] = []

    client.subscribe("orders", received.append)
    client.publish("orders", b"order-1")

    assert len(received) == 1
    assert received[0].topic == "orders"
    assert received[0].body == b"order-1"


def test_multiple_subscribers_on_same_topic_all_receive_the_message() -> None:
    client = QueueClient()
    received_a: list[Message] = []
    received_b: list[Message] = []

    client.subscribe("orders", received_a.append)
    client.subscribe("orders", received_b.append)
    client.publish("orders", b"order-1")

    assert len(received_a) == 1
    assert len(received_b) == 1
    assert received_a[0].body == b"order-1"
    assert received_b[0].body == b"order-1"


def test_subscriber_does_not_receive_messages_from_other_topics() -> None:
    client = QueueClient()
    received_orders: list[Message] = []
    received_shipments: list[Message] = []

    client.subscribe("orders", received_orders.append)
    client.subscribe("shipments", received_shipments.append)

    client.publish("shipments", b"shipment-1")

    assert received_orders == []
    assert len(received_shipments) == 1
    assert received_shipments[0].topic == "shipments"


def test_publish_delivers_multiple_messages_in_order() -> None:
    client = QueueClient()
    received: list[Message] = []

    client.subscribe("orders", received.append)
    client.publish("orders", b"first")
    client.publish("orders", b"second")

    assert [m.body for m in received] == [b"first", b"second"]


def test_unsubscribe_stops_future_delivery() -> None:
    client = QueueClient()
    received: list[Message] = []

    subscription = client.subscribe("orders", received.append)
    client.publish("orders", b"before-unsubscribe")
    subscription.unsubscribe()
    client.publish("orders", b"after-unsubscribe")

    assert len(received) == 1
    assert received[0].body == b"before-unsubscribe"


def test_unsubscribe_does_not_affect_other_subscribers_on_same_topic() -> None:
    client = QueueClient()
    received_a: list[Message] = []
    received_b: list[Message] = []

    sub_a = client.subscribe("orders", received_a.append)
    client.subscribe("orders", received_b.append)

    sub_a.unsubscribe()
    client.publish("orders", b"order-1")

    assert received_a == []
    assert len(received_b) == 1
