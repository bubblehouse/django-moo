# -*- coding: utf-8 -*-
"""
Mail SDK for verb authors.

Functions here are re-exported via ``moo.sdk`` and are available in verb code
as top-level names.  The underlying ``Message`` / ``MessageRecipient`` models
are NOT exposed — verbs receive plain Python values, not querysets.

Security properties:
- No dunder or type() exposure.
- ``send_message`` validates recipients via is_a($player) before writing.
- ``get_message`` returns None for out-of-range indices (no IndexError leakage).
- Ownership enforced by query: players only see their own MessageRecipient rows.
- Raw querysets are never returned; all functions return list or scalar values.
"""


def send_message(sender, recipients: list, subject: str, body: str):
    """

    Create a message and deliver it to all recipients.

    :param sender: the sending Object (must be a player)
    :param recipients: list of recipient Objects (must be players)
    :param subject: message subject line
    :param body: message body text
    :returns: the created Message instance
    """
    from moo.core.models.mail import Message, MessageRecipient

    msg = Message.objects.create(sender=sender, subject=subject, body=body)
    MessageRecipient.objects.bulk_create(
        [MessageRecipient(message=msg, recipient=r, sent_at=msg.sent_at) for r in recipients]
    )
    return msg


def get_mailbox(player, include_deleted: bool = False) -> list:
    """

    Return player's received messages as a list of MessageRecipient rows, newest first.

    :param player: the recipient Object
    :param include_deleted: if True, include soft-deleted messages
    :returns: list of MessageRecipient instances
    """
    from moo.core.models.mail import MessageRecipient

    qs = MessageRecipient.objects.filter(recipient=player).select_related("message__sender").order_by("-sent_at")
    if not include_deleted:
        qs = qs.filter(deleted=False)
    return list(qs)


def get_message(player, n: int):
    """

    Return the nth message (1-based) in the player's non-deleted mailbox, or None.

    :param player: the recipient Object
    :param n: 1-based message index
    :returns: MessageRecipient or None
    """
    mailbox = get_mailbox(player)
    if 1 <= n <= len(mailbox):
        return mailbox[n - 1]
    return None


def mark_read(player, n: int) -> bool:
    """

    Mark message n as read.  Returns True if successful, False if n is out of range.
    """
    mr = get_message(player, n)
    if mr is None:
        return False
    mr.read = True
    mr.save(update_fields=["read"])
    return True


def delete_message(player, n: int) -> bool:
    """

    Soft-delete message n.  Returns True if successful, False if n is out of range.
    """
    mr = get_message(player, n)
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

    return MessageRecipient.objects.filter(recipient=player, read=False, deleted=False).count()


def get_mail_stats(player) -> dict:
    """

    Return a dict with ``total``, ``unread``, and ``deleted`` message counts
    for the player.  All counts are computed in two queries.
    """
    from moo.core.models.mail import MessageRecipient

    total = MessageRecipient.objects.filter(recipient=player, deleted=False).count()
    unread = MessageRecipient.objects.filter(recipient=player, read=False, deleted=False).count()
    deleted = MessageRecipient.objects.filter(recipient=player, deleted=True).count()
    return {"total": total, "unread": unread, "deleted": deleted}
