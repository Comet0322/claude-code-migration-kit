"""Tests for NotificationClient. See boogie-sdk-api.md (this skill's library doc)
section 5.5 (governance).

`send_email`/`send_im`/`send_sms` return `None` per the design doc and
there is no real mail/IM/SMS backend behind this fake, so nothing is
actually delivered anywhere. To make delivery observable in tests, this
fake adds introspection lists (additive, not in the design doc), each
appended to exactly once per corresponding send call, in call order:

- `sent_emails: list[tuple[str, str, str]]` — `(to, subject, body)`,
  appended to by `send_email`.
- `sent_ims: list[tuple[str, str]]` — `(channel, message)`, appended to
  by `send_im`.
- `sent_sms: list[tuple[str, str]]` — `(phone, message)`, appended to by
  `send_sms`.

These lists are independent of each other (sending an email never
affects `sent_ims`/`sent_sms`, and so on).
"""

from __future__ import annotations

import pytest

from boogie_sdk.governance.notification_client import NotificationClient


@pytest.fixture
def client() -> NotificationClient:
    return NotificationClient()


# -- send_email -----------------------------------------------------------


def test_send_email_returns_none(client: NotificationClient) -> None:
    assert client.send_email("a@example.com", "Subject", "Body") is None


def test_send_email_appends_tuple_to_sent_emails(client: NotificationClient) -> None:
    client.send_email("a@example.com", "Hello", "World")

    assert client.sent_emails == [("a@example.com", "Hello", "World")]


# -- send_im ----------------------------------------------------------------


def test_send_im_returns_none(client: NotificationClient) -> None:
    assert client.send_im("#alerts", "ping") is None


def test_send_im_appends_tuple_to_sent_ims(client: NotificationClient) -> None:
    client.send_im("#alerts", "deploy finished")

    assert client.sent_ims == [("#alerts", "deploy finished")]


# -- send_sms -----------------------------------------------------------------


def test_send_sms_returns_none(client: NotificationClient) -> None:
    assert client.send_sms("+15551234567", "code: 000000") is None


def test_send_sms_appends_tuple_to_sent_sms(client: NotificationClient) -> None:
    client.send_sms("+15551234567", "code: 123456")

    assert client.sent_sms == [("+15551234567", "code: 123456")]


# -- accumulation / independence ----------------------------------------------


def test_multiple_sends_of_same_kind_accumulate_in_order(
    client: NotificationClient,
) -> None:
    client.send_email("a@example.com", "First", "1")
    client.send_email("b@example.com", "Second", "2")

    assert client.sent_emails == [
        ("a@example.com", "First", "1"),
        ("b@example.com", "Second", "2"),
    ]


def test_sending_different_kinds_only_affects_their_own_list(
    client: NotificationClient,
) -> None:
    client.send_email("a@example.com", "Subject", "Body")
    client.send_im("#alerts", "ping")
    client.send_sms("+15551234567", "code")

    assert len(client.sent_emails) == 1
    assert len(client.sent_ims) == 1
    assert len(client.sent_sms) == 1
