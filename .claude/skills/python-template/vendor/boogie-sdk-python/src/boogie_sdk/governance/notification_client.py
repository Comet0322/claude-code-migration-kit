"""NotificationClient stub. See boogie-sdk-api.md (this skill's library doc) section 5.5 (governance).

Skeleton only — implemented during the Phase 1 TDD loop for the `governance` module.
"""

from __future__ import annotations


class NotificationClient:
    def __init__(self) -> None:
        self.sent_emails: list[tuple[str, str, str]] = []
        self.sent_ims: list[tuple[str, str]] = []
        self.sent_sms: list[tuple[str, str]] = []

    def send_email(self, to: str, subject: str, body: str) -> None:
        self.sent_emails.append((to, subject, body))

    def send_im(self, channel: str, message: str) -> None:
        self.sent_ims.append((channel, message))

    def send_sms(self, phone: str, message: str) -> None:
        self.sent_sms.append((phone, message))
