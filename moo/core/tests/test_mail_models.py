# -*- coding: utf-8 -*-
"""
Unit tests for the mail SDK functions (moo/sdk/mail.py).

These tests exercise the data layer directly — no verb dispatch, no parser.
They use the standard ``t_init`` / ``t_wizard`` fixtures so that Permission
records and the Object hierarchy are in place.
"""

import pytest

from moo.core.models import Object
from moo.sdk import lookup
from moo.sdk.mail import (
    count_unread,
    delete_message,
    get_mailbox,
    get_message,
    mark_read,
    send_message,
    undelete_message,
)


# ---------------------------------------------------------------------------
# send_message
# ---------------------------------------------------------------------------


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_send_message_creates_message_and_recipient(t_init: Object, t_wizard: Object):
    player = lookup("Player")
    msg = send_message(t_wizard, [player], "Hello", "Body text")
    assert msg.pk is not None
    assert msg.subject == "Hello"
    assert msg.body == "Body text"
    assert msg.sender == t_wizard
    assert msg.recipients.filter(recipient=player).exists()


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_send_message_denormalizes_sent_at(t_init: Object, t_wizard: Object):
    player = lookup("Player")
    msg = send_message(t_wizard, [player], "Subject", "Body")
    mr = msg.recipients.get(recipient=player)
    assert mr.sent_at is not None
    assert mr.sent_at == msg.sent_at


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_send_message_multiple_recipients(t_init: Object, t_wizard: Object):
    player = lookup("Player")
    msg = send_message(t_wizard, [t_wizard, player], "Broadcast", "For everyone")
    assert msg.recipients.count() == 2


# ---------------------------------------------------------------------------
# get_mailbox
# ---------------------------------------------------------------------------


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_get_mailbox_empty(t_init: Object, t_wizard: Object):
    player = lookup("Player")
    assert get_mailbox(player) == []


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_get_mailbox_returns_newest_first(t_init: Object, t_wizard: Object):
    player = lookup("Player")
    send_message(t_wizard, [player], "First", "body")
    send_message(t_wizard, [player], "Second", "body")
    mailbox = get_mailbox(player)
    assert len(mailbox) == 2
    assert mailbox[0].message.subject == "Second"
    assert mailbox[1].message.subject == "First"


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_get_mailbox_excludes_deleted_by_default(t_init: Object, t_wizard: Object):
    player = lookup("Player")
    send_message(t_wizard, [player], "Keep", "body")
    send_message(t_wizard, [player], "Delete", "body")
    delete_message(player, 1)  # delete newest ("Delete")
    assert len(get_mailbox(player)) == 1


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_get_mailbox_include_deleted(t_init: Object, t_wizard: Object):
    player = lookup("Player")
    send_message(t_wizard, [player], "Keep", "body")
    send_message(t_wizard, [player], "Delete", "body")
    delete_message(player, 1)
    assert len(get_mailbox(player, include_deleted=True)) == 2


# ---------------------------------------------------------------------------
# get_message
# ---------------------------------------------------------------------------


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_get_message_returns_correct_row(t_init: Object, t_wizard: Object):
    player = lookup("Player")
    send_message(t_wizard, [player], "A", "body")
    send_message(t_wizard, [player], "B", "body")
    mr = get_message(player, 1)  # 1-based, newest first → "B"
    assert mr.message.subject == "B"


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_get_message_out_of_range_returns_none(t_init: Object, t_wizard: Object):
    player = lookup("Player")
    send_message(t_wizard, [player], "Only", "body")
    assert get_message(player, 0) is None
    assert get_message(player, 2) is None


# ---------------------------------------------------------------------------
# mark_read
# ---------------------------------------------------------------------------


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_mark_read_sets_flag(t_init: Object, t_wizard: Object):
    player = lookup("Player")
    send_message(t_wizard, [player], "Unread", "body")
    assert not get_message(player, 1).read
    result = mark_read(player, 1)
    assert result is True
    assert get_message(player, 1).read


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_mark_read_out_of_range_returns_false(t_init: Object, t_wizard: Object):
    player = lookup("Player")
    assert mark_read(player, 99) is False


# ---------------------------------------------------------------------------
# delete_message / undelete_message
# ---------------------------------------------------------------------------


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_delete_message_soft_deletes(t_init: Object, t_wizard: Object):
    player = lookup("Player")
    send_message(t_wizard, [player], "Msg", "body")
    result = delete_message(player, 1)
    assert result is True
    assert get_mailbox(player) == []


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_delete_message_out_of_range_returns_false(t_init: Object, t_wizard: Object):
    player = lookup("Player")
    assert delete_message(player, 5) is False


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_undelete_message_restores(t_init: Object, t_wizard: Object):
    player = lookup("Player")
    send_message(t_wizard, [player], "Msg", "body")
    delete_message(player, 1)
    result = undelete_message(player, 1)
    assert result is True
    assert len(get_mailbox(player)) == 1


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_undelete_message_out_of_range_returns_false(t_init: Object, t_wizard: Object):
    player = lookup("Player")
    assert undelete_message(player, 1) is False


# ---------------------------------------------------------------------------
# count_unread
# ---------------------------------------------------------------------------


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_count_unread_initial(t_init: Object, t_wizard: Object):
    player = lookup("Player")
    send_message(t_wizard, [player], "A", "body")
    send_message(t_wizard, [player], "B", "body")
    assert count_unread(player) == 2


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_count_unread_after_read(t_init: Object, t_wizard: Object):
    player = lookup("Player")
    send_message(t_wizard, [player], "A", "body")
    send_message(t_wizard, [player], "B", "body")
    mark_read(player, 1)
    assert count_unread(player) == 1


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_count_unread_excludes_deleted(t_init: Object, t_wizard: Object):
    player = lookup("Player")
    send_message(t_wizard, [player], "A", "body")
    delete_message(player, 1)
    assert count_unread(player) == 0
