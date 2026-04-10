# -*- coding: utf-8 -*-
"""
Mail models for the DjangoMOO mail system.

Messages are stored in a dedicated Django model rather than as MOO Objects
so that mailboxes can be queried with indexed SQL, paginated efficiently,
and per-recipient read/delete state tracked without pressure on the
Object/Property tables.
"""

from django.db import models


class Message(models.Model):
    """
    A single mail message.  One row regardless of recipient count.
    """

    sender = models.ForeignKey(
        "core.Object",
        related_name="sent_messages",
        on_delete=models.SET_NULL,
        null=True,
    )
    subject = models.CharField(max_length=255)
    body = models.TextField()
    sent_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        indexes = [models.Index(fields=["sender", "sent_at"])]

    def __str__(self):
        return f"Message({self.pk}, subject={self.subject!r})"


class MessageRecipient(models.Model):
    """
    One row per (message, recipient) pair.  Tracks per-recipient read and
    deleted state.  ``sent_at`` is denormalized from ``message.sent_at``
    so that mailbox list queries are single-table scans.
    """

    message = models.ForeignKey(Message, related_name="recipients", on_delete=models.CASCADE)
    recipient = models.ForeignKey(
        "core.Object",
        related_name="received_messages",
        on_delete=models.CASCADE,
    )
    read = models.BooleanField(default=False, db_index=True)
    deleted = models.BooleanField(default=False)
    sent_at = models.DateTimeField(null=True, db_index=True)

    class Meta:
        unique_together = [("message", "recipient")]
        indexes = [
            models.Index(fields=["recipient", "deleted", "sent_at"]),
            models.Index(fields=["recipient", "read", "deleted"]),
        ]

    def __str__(self):
        return f"MessageRecipient({self.pk}, recipient={self.recipient_id}, read={self.read})"
