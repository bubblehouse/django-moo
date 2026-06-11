# -*- coding: utf-8 -*-
# pylint: disable=protected-access
"""
Security tests: Message and MessageRecipient model permission checks.

The mail tables are reachable from any verb that calls ``send_message`` or
``get_message``; without these guards a non-wizard could rewrite or hard-
delete other players' mail.

Covers:
  - Message.save() blocks edits to existing rows for non-wizards (INSERT
    is allowed so send_message still works)
  - Message.delete() requires wizard (cascades wipe other recipients)
  - MessageRecipient.save() allows the recipient to mark read / soft-delete
    but blocks recipient-FK rebinding and saves by non-recipients
  - MessageRecipient.delete() (the hard-delete bypass for soft-delete) is
    wizard-only
"""

import pytest

from moo.core.models.auth import Player
from moo.core.models.mail import Message, MessageRecipient
from moo.core.models.object import Object

from .utils import ctx


def ensure_player_avatar(obj):
    """Give an Object a Player row so mail SDK validation treats it as a player."""
    Player.objects.get_or_create(avatar=obj, defaults={"site": obj.site})


# ---------------------------------------------------------------------------
# Message.save() / Message.delete() must be restricted
# ---------------------------------------------------------------------------


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_message_save_blocked_for_non_wizard(t_init: Object, t_wizard: Object):
    """

    Attack path: verb code receives a Message instance from send_message(), modifies
    msg.sender to a wizard object, and calls msg.save(). Without a guard, Message.save()
    is a plain Django model save with no ACL check — any attribute can be overwritten.

    The guard blocks saves on existing rows (pk is not None) unless the caller is a
    wizard. It does not block INSERT (pk is None), so send_message() still works.
    """
    from moo.sdk import create, send_message
    from moo.core.exceptions import AccessError

    with ctx(t_wizard):
        plain = create("msg_save_plain")
        target = create("msg_save_target")
        ensure_player_avatar(plain)
        ensure_player_avatar(target)

    with ctx(plain):
        msg_value = send_message(plain, [target], "hello", "world")

    # msg is now an existing row (pk is not None); non-wizard cannot modify it
    msg = Message.objects.get(pk=msg_value.pk)
    msg.subject = "spoofed"
    with ctx(plain):
        with pytest.raises((PermissionError, AccessError)):
            msg.save()


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_message_save_allowed_for_wizard(t_init: Object, t_wizard: Object):
    """Wizard can save changes to an existing Message — regression for admin use."""
    from moo.sdk import create, send_message

    with ctx(t_wizard):
        target = create("msg_save_wiz_target")
        ensure_player_avatar(target)

    with ctx(t_wizard):
        msg_value = send_message(t_wizard, [target], "original", "body")

    msg = Message.objects.get(pk=msg_value.pk)
    msg.subject = "updated"
    with ctx(t_wizard):
        msg.save()

    msg.refresh_from_db()
    assert msg.subject == "updated"


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_send_message_still_works_for_non_wizard(t_init: Object, t_wizard: Object):
    """

    send_message() creates a new Message row (pk is None → INSERT). The guard only
    applies to saves on existing rows, so non-wizards can still send messages via the
    SDK function. This is the regression test for the send path.
    """
    from moo.sdk import create, send_message

    with ctx(t_wizard):
        plain = create("msg_create_plain")
        target = create("msg_create_target")
        ensure_player_avatar(plain)
        ensure_player_avatar(target)

    with ctx(plain):
        msg = send_message(plain, [target], "test subject", "test body")

    assert msg.pk is not None
    assert msg.subject == "test subject"


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_message_delete_blocked_for_non_wizard(t_init: Object, t_wizard: Object):
    """

    Attack path: verb code gets a MessageRecipient from get_message(), traverses
    mr.message to the parent Message object, and calls .delete() to cascade-delete
    the message for ALL recipients — bypassing the soft-delete mechanism entirely.

    Message.delete() must be restricted to wizards because the side-effect
    (CASCADE to all MessageRecipient rows) affects other players who did not
    initiate the delete.
    """
    from moo.sdk import create, send_message, get_message
    from moo.core.exceptions import AccessError

    with ctx(t_wizard):
        plain = create("msg_del_plain")
        other = create("msg_del_other")
        ensure_player_avatar(plain)
        ensure_player_avatar(other)

    with ctx(t_wizard):
        send_message(t_wizard, [plain, other], "shared", "body")

    mr_value = get_message(plain, 1)
    assert mr_value is not None
    msg = Message.objects.get(pk=mr_value.message.pk)

    with ctx(plain):
        with pytest.raises((PermissionError, AccessError)):
            msg.delete()

    # Message must still exist
    assert Message.objects.filter(pk=msg.pk).exists()


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_message_delete_allowed_for_wizard(t_init: Object, t_wizard: Object):
    """Wizard can hard-delete a Message (and its cascade)."""
    from moo.sdk import create, send_message

    with ctx(t_wizard):
        target = create("msg_del_wiz_target")
        ensure_player_avatar(target)

    with ctx(t_wizard):
        msg_value = send_message(t_wizard, [target], "deleteme", "body")
    msg = Message.objects.get(pk=msg_value.pk)
    msg_pk = msg.pk

    with ctx(t_wizard):
        msg.delete()

    assert not Message.objects.filter(pk=msg_pk).exists()


# ---------------------------------------------------------------------------
# MessageRecipient.save() / MessageRecipient.delete() must be restricted
# ---------------------------------------------------------------------------


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_message_recipient_save_blocks_redirection(t_init: Object, t_wizard: Object):
    """

    Attack path: verb code calls get_message(player, 1), sets mr.recipient to a
    different player object, and calls mr.save(). Without a guard, this redirects
    the ownership of the message row to another player, leaking message content.

    The guard allows saves only when caller == recipient or caller is wizard.
    Changing mr.recipient to another player means caller != new_recipient_id,
    so the save is denied.
    """
    from moo.sdk import create, send_message, get_message
    from moo.core.exceptions import AccessError

    with ctx(t_wizard):
        plain = create("mr_redirect_plain")
        victim = create("mr_redirect_victim")
        ensure_player_avatar(plain)
        ensure_player_avatar(victim)

    with ctx(t_wizard):
        send_message(t_wizard, [plain], "private", "content")

    mr_value = get_message(plain, 1)
    assert mr_value is not None
    mr = MessageRecipient.objects.get(pk=mr_value.pk)

    original_recipient_id = mr.recipient_id
    mr.recipient = victim

    with ctx(plain):
        with pytest.raises((PermissionError, AccessError)):
            mr.save()

    mr.refresh_from_db()
    assert mr.recipient_id == original_recipient_id


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_message_recipient_save_allowed_for_recipient(t_init: Object, t_wizard: Object):
    """

    The legitimate mark_read() and delete_message() SDK functions call mr.save()
    on behalf of the recipient. These must continue to work: the guard allows saves
    where caller.pk == mr.recipient_id, covering the read/delete update_fields cases.
    """
    from moo.sdk import create, send_message, mark_read, get_message

    with ctx(t_wizard):
        plain = create("mr_markread_plain")
        ensure_player_avatar(plain)

    with ctx(t_wizard):
        send_message(t_wizard, [plain], "read me", "body")

    with ctx(plain):
        result = mark_read(plain, 1)
    assert result is True

    mr = get_message(plain, 1)
    assert mr.read is True


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_message_recipient_save_blocked_for_non_recipient(t_init: Object, t_wizard: Object):
    """

    A non-wizard verb code that is NOT the recipient of the message cannot call
    mr.save() on that row, even without modifying mr.recipient. The guard checks
    caller == recipient, not merely that the row exists.
    """
    from moo.sdk import create, send_message, get_message
    from moo.core.exceptions import AccessError

    with ctx(t_wizard):
        plain = create("mr_nonrecip_plain")
        attacker = create("mr_nonrecip_attacker")
        ensure_player_avatar(plain)
        ensure_player_avatar(attacker)

    with ctx(t_wizard):
        send_message(t_wizard, [plain], "private", "content")

    mr_value = get_message(plain, 1)
    assert mr_value is not None
    mr = MessageRecipient.objects.get(pk=mr_value.pk)

    # attacker tries to save the row even without changing recipient
    with ctx(attacker):
        with pytest.raises((PermissionError, AccessError)):
            mr.save()


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_message_recipient_hard_delete_blocked_for_non_wizard(t_init: Object, t_wizard: Object):
    """

    Attack path: verb code calls get_message(player, 1) and then mr.delete().
    Unlike mr.deleted = True; mr.save() (the soft-delete path), this permanently
    removes the DB row, bypassing the soft-delete mechanism and making the message
    un-restorable.

    MessageRecipient.delete() must require wizard. Non-wizard recipients should use
    the delete_message() SDK function which sets mr.deleted = True.
    """
    from moo.sdk import create, send_message, get_message
    from moo.core.exceptions import AccessError

    with ctx(t_wizard):
        plain = create("mr_hd_plain")
        ensure_player_avatar(plain)

    with ctx(t_wizard):
        send_message(t_wizard, [plain], "precious", "body")

    mr_value = get_message(plain, 1)
    assert mr_value is not None
    mr = MessageRecipient.objects.get(pk=mr_value.pk)
    mr_pk = mr.pk

    with ctx(plain):
        with pytest.raises((PermissionError, AccessError)):
            mr.delete()

    assert MessageRecipient.objects.filter(pk=mr_pk).exists()


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_message_recipient_hard_delete_allowed_for_wizard(t_init: Object, t_wizard: Object):
    """Wizard can hard-delete a MessageRecipient row."""
    from moo.sdk import create, send_message, get_message

    with ctx(t_wizard):
        target = create("mr_hd_wiz_target")
        ensure_player_avatar(target)

    with ctx(t_wizard):
        send_message(t_wizard, [target], "deleteme", "body")

    mr_value = get_message(target, 1)
    assert mr_value is not None
    mr = MessageRecipient.objects.get(pk=mr_value.pk)
    mr_pk = mr.pk

    with ctx(t_wizard):
        mr.delete()

    assert not MessageRecipient.objects.filter(pk=mr_pk).exists()
