# -*- coding: utf-8 -*-
"""
Mail SDK for verb authors.

Functions here are re-exported via ``moo.sdk`` and are available in verb code
as top-level names.  The underlying ``Message`` / ``MessageRecipient`` models
are NOT exposed — verbs receive plain Python values, not querysets.

Security properties:
- No dunder or type() exposure.
- ``send_message`` validates sender and recipients have Player rows before writing.
- ``get_message`` returns None for out-of-range indices (no IndexError leakage).
- Ownership enforced by context: players only see their own mailbox rows.
- Raw querysets are never returned; all functions return list or scalar values.
"""

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class MailMessage:
    """Plain verb-facing representation of a Message row."""

    pk: int
    sender: Any
    subject: str
    body: str
    sent_at: Any


@dataclass(frozen=True)
class MailboxEntry:
    """Plain verb-facing representation of a MessageRecipient row."""

    pk: int
    message: MailMessage
    recipient: Any
    read: bool
    deleted: bool
    sent_at: Any


def _message_value(message):
    return MailMessage(
        pk=message.pk,
        sender=message.sender,
        subject=message.subject,
        body=message.body,
        sent_at=message.sent_at,
    )


def _recipient_value(row):
    return MailboxEntry(
        pk=row.pk,
        message=_message_value(row.message),
        recipient=row.recipient,
        read=row.read,
        deleted=row.deleted,
        sent_at=row.sent_at,
    )


def _player_is_wizard(player):
    return bool(player and player.is_wizard())


def _require_own_mailbox(player):
    from ..core.code import ContextManager  # pylint: disable=import-outside-toplevel
    from ..core.exceptions import UserError  # pylint: disable=import-outside-toplevel
    from .context import context  # pylint: disable=import-outside-toplevel

    if not ContextManager.is_active() or context.player is None:
        return player
    if _player_is_wizard(context.player) or player == context.player:
        return player
    raise UserError("You can only access your own mailbox.")


def _require_sender(sender):
    from ..core.code import ContextManager  # pylint: disable=import-outside-toplevel
    from ..core.exceptions import UserError  # pylint: disable=import-outside-toplevel
    from .context import context  # pylint: disable=import-outside-toplevel

    if not ContextManager.is_active() or context.player is None:
        return sender
    if _player_is_wizard(context.player) or sender == context.player:
        return sender
    raise UserError("You can only send mail as yourself.")


def _require_player_objects(objects):
    from ..core.code import ContextManager  # pylint: disable=import-outside-toplevel
    from ..core.exceptions import UserError  # pylint: disable=import-outside-toplevel
    from ..core.models.auth import Player  # pylint: disable=import-outside-toplevel
    from .context import context  # pylint: disable=import-outside-toplevel

    # Unlike the helpers above, this still validates when a context is active
    # with player=None: system tasks must not mail non-players either.
    if not ContextManager.is_active() or _player_is_wizard(context.player):
        return
    for obj in objects:
        if not Player.objects.filter(avatar=obj).exists():
            raise UserError(f"{obj} is not a player.")


def _mailbox_rows(player, include_deleted: bool = False):
    from moo.core.models.mail import MessageRecipient

    qs = MessageRecipient.objects.filter(recipient=player).select_related("message__sender").order_by("-sent_at")
    if not include_deleted:
        qs = qs.filter(deleted=False)
    return list(qs)


def _message_row(player, n: int):
    mailbox = _mailbox_rows(player)
    if 1 <= n <= len(mailbox):
        return mailbox[n - 1]
    return None


def send_message(sender, recipients: list, subject: str, body: str):
    """

    Create a message and deliver it to all recipients.

    :param sender: the sending Object (must be a player)
    :param recipients: list of recipient Objects (must be players)
    :param subject: message subject line
    :param body: message body text
    :returns: plain message value for the created message
    """
    from moo.core.models.mail import Message, MessageRecipient

    sender = _require_sender(sender)
    _require_player_objects([sender, *recipients])
    msg = Message.objects.create(sender=sender, subject=subject, body=body)
    MessageRecipient.objects.bulk_create(
        [MessageRecipient(message=msg, recipient=r, sent_at=msg.sent_at) for r in recipients]
    )
    return _message_value(msg)


def get_mailbox(player, include_deleted: bool = False) -> list:
    """

    Return player's received messages as plain mailbox values, newest first.

    :param player: the recipient Object
    :param include_deleted: if True, include soft-deleted messages
    :returns: list of MailboxEntry values
    """
    player = _require_own_mailbox(player)
    return [_recipient_value(row) for row in _mailbox_rows(player, include_deleted)]


def get_message(player, n: int):
    """

    Return the nth message (1-based) in the player's non-deleted mailbox, or None.

    :param player: the recipient Object
    :param n: 1-based message index
    :returns: MailboxEntry or None
    """
    player = _require_own_mailbox(player)
    row = _message_row(player, n)
    return _recipient_value(row) if row is not None else None


def mark_read(player, n: int) -> bool:
    """

    Mark message n as read.  Returns True if successful, False if n is out of range.
    """
    player = _require_own_mailbox(player)
    mr = _message_row(player, n)
    if mr is None:
        return False
    mr.read = True
    mr.save(update_fields=["read"])
    return True


def delete_message(player, n: int) -> bool:
    """

    Soft-delete message n.  Returns True if successful, False if n is out of range.
    """
    player = _require_own_mailbox(player)
    mr = _message_row(player, n)
    if mr is None:
        return False
    mr.deleted = True
    mr.save(update_fields=["deleted"])
    return True


def undelete_message(player, n: int) -> bool:
    """

    Restore the nth deleted message (1-based among deleted-only list).
    Returns True if successful, False if n is out of range.
    """
    from moo.core.models.mail import MessageRecipient

    player = _require_own_mailbox(player)
    deleted = list(
        MessageRecipient.objects.filter(recipient=player, deleted=True)
        .select_related("message__sender")
        .order_by("-sent_at")
    )
    if 1 <= n <= len(deleted):
        deleted[n - 1].deleted = False
        deleted[n - 1].save(update_fields=["deleted"])
        return True
    return False


def count_unread(player) -> int:
    """

    Return the count of unread, non-deleted messages for the player.
    """
    from moo.core.models.mail import MessageRecipient

    player = _require_own_mailbox(player)
    return MessageRecipient.objects.filter(recipient=player, read=False, deleted=False).count()


def get_mail_stats(player) -> dict:
    """

    Return a dict with ``total``, ``unread``, and ``deleted`` message counts
    for the player.  All counts are computed in two queries.
    """
    from moo.core.models.mail import MessageRecipient

    player = _require_own_mailbox(player)
    total = MessageRecipient.objects.filter(recipient=player, deleted=False).count()
    unread = MessageRecipient.objects.filter(recipient=player, read=False, deleted=False).count()
    deleted = MessageRecipient.objects.filter(recipient=player, deleted=True).count()
    return {"total": total, "unread": unread, "deleted": deleted}
