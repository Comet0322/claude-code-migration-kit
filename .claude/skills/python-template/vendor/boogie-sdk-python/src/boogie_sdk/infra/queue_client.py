"""QueueClient stub. See boogie-sdk-api.md (this skill's library doc) section 5.2 (infra).

Synchronous in-memory pub/sub fake (see
tests/infra/test_queue_client.py module docstring for the
pinned-down convention): `publish` immediately invokes every
currently-registered subscriber handler for that topic, in the same call
stack.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable


@dataclass(frozen=True)
class Message:
    topic: str
    body: bytes


class Subscription:
    def __init__(self, topic: str, handler: Callable[[Message], None], client: "QueueClient") -> None:
        self._topic = topic
        self._handler = handler
        self._client = client

    def unsubscribe(self) -> None:
        self._client._unsubscribe(self._topic, self)

    def _handle(self, message: Message) -> None:
        self._handler(message)


class QueueClient:
    def __init__(self) -> None:
        self._subscriptions: dict[str, list[Subscription]] = {}

    def publish(self, topic: str, message: bytes) -> None:
        msg = Message(topic=topic, body=message)
        for subscription in list(self._subscriptions.get(topic, [])):
            subscription._handle(msg)

    def subscribe(
        self, topic: str, handler: Callable[[Message], None]
    ) -> Subscription:
        subscription = Subscription(topic, handler, self)
        self._subscriptions.setdefault(topic, []).append(subscription)
        return subscription

    def _unsubscribe(self, topic: str, subscription: Subscription) -> None:
        subscribers = self._subscriptions.get(topic)
        if subscribers is None:
            return
        try:
            subscribers.remove(subscription)
        except ValueError:
            pass
