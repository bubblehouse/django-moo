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

    Permission guards:

    - ``save()`` on an existing row (pk is not None) requires the caller to be
      a wizard.  INSERTs (pk is None) are always allowed so that ``send_message()``
      in the SDK can create new messages on behalf of any player.
    - ``delete()`` requires the caller to be a wizard because a CASCADE delete
      removes MessageRecipient rows for every recipient.
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

    def save(self, *args, **kwargs):
        if self.pk is not None:
            from moo.core.code import ContextManager
            from moo.core.exceptions import AccessError

            caller = ContextManager.get("caller")
            if caller is not None and not caller.is_wizard():
                raise AccessError(caller, "write", self)
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        from moo.core.code import ContextManager
        from moo.core.exceptions import AccessError

        caller = ContextManager.get("caller")
        if caller is not None and not caller.is_wizard():
            raise AccessError(caller, "write", self)
        return super().delete(*args, **kwargs)


class MessageRecipient(models.Model):
    """
    One row per (message, recipient) pair.  Tracks per-recipient read and
    deleted state.  ``sent_at`` is denormalized from ``message.sent_at``
    so that mailbox list queries are single-table scans.

    Permission guards:

    - ``save()`` on an existing row requires the caller to be a wizard OR the
      caller to be the recipient of this row.  This allows the SDK's
      ``mark_read()`` / ``delete_message()`` / ``undelete_message()`` helpers to
      work for the owning player while blocking attempts to redirect the row to
      a different recipient.  INSERTs (pk is None) are always allowed.
    - ``delete()`` (hard-delete) requires the caller to be a wizard.  Non-wizard
      players should use the ``delete_message()`` SDK function, which performs a
      soft-delete by setting ``deleted = True``.
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

    def save(self, *args, **kwargs):
        if self.pk is not None:
            from moo.core.code import ContextManager
            from moo.core.exceptions import AccessError

            caller = ContextManager.get("caller")
            if caller is not None and not caller.is_wizard():
                if caller.pk != self.recipient_id:
                    raise AccessError(caller, "write", self)
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        from moo.core.code import ContextManager
        from moo.core.exceptions import AccessError

        caller = ContextManager.get("caller")
        if caller is not None and not caller.is_wizard():
            raise AccessError(caller, "write", self)
        return super().delete(*args, **kwargs)
