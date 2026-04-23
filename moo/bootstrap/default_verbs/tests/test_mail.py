# pylint: disable=protected-access
import pytest

from moo.core import code, parse
from moo.sdk import context, lookup
from moo.sdk.mail import send_message, get_mailbox, count_unread
from moo.core.models import Object


# --- @mail (list / read / stats / delete / undelete) ---


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_at_mail_empty_mailbox(t_init: Object, t_wizard: Object):
    """@mail with no messages tells the player the mailbox is empty."""
    printed = []
    with code.ContextManager(t_wizard, printed.append) as ctx:
        parse.interpret(ctx, "@mail")
    assert any("empty" in line for line in printed)


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_at_mail_lists_messages(t_init: Object, t_wizard: Object):
    """@mail opens the paginator with inbox contents when messages exist."""
    with code.ContextManager(t_wizard, lambda _: None) as ctx:
        player = lookup("Player")
        send_message(player, [t_wizard], "Test subject", "Test body")
        with pytest.warns(RuntimeWarning, match=r"ConnectionError") as caught:
            parse.interpret(ctx, "@mail")
    messages = [str(w.message) for w in caught.list]
    assert any("Test subject" in m for m in messages)
    assert any("unread" in m for m in messages)


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_at_mail_read_marks_read(t_init: Object, t_wizard: Object):
    """@mail <n> shows the message and marks it as read."""
    with code.ContextManager(t_wizard, lambda _: None) as ctx:
        player = lookup("Player")
        send_message(player, [t_wizard], "Hello subject", "Hello body text")
        with pytest.warns(RuntimeWarning, match=r"ConnectionError") as caught:
            parse.interpret(ctx, "@mail 1")
    messages = [str(w.message) for w in caught.list]
    assert any("Hello subject" in m for m in messages)
    assert any("Hello body text" in m for m in messages)
    mr = get_mailbox(t_wizard)[0]
    assert mr.read


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_at_mail_read_out_of_range(t_init: Object, t_wizard: Object):
    """@mail <n> for a nonexistent message prints an error."""
    printed = []
    with code.ContextManager(t_wizard, printed.append) as ctx:
        parse.interpret(ctx, "@mail 99")
    assert any("no message 99" in line for line in printed)


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_at_mail_stats(t_init: Object, t_wizard: Object):
    """@mail stats shows message counts."""
    printed = []
    with code.ContextManager(t_wizard, printed.append) as ctx:
        player = lookup("Player")
        send_message(player, [t_wizard], "Subj", "body")
        parse.interpret(ctx, "@mail stats")
    assert any("total" in line and "unread" in line for line in printed)


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_at_mail_delete(t_init: Object, t_wizard: Object):
    """@mail delete <n> removes the message from the active mailbox."""
    printed = []
    with code.ContextManager(t_wizard, printed.append) as ctx:
        player = lookup("Player")
        send_message(player, [t_wizard], "Subj", "body")
        parse.interpret(ctx, "@mail delete 1")
    assert any("deleted" in line for line in printed)
    assert not get_mailbox(t_wizard)


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_at_mail_undelete(t_init: Object, t_wizard: Object):
    """@mail undelete <n> restores a deleted message."""
    printed = []
    with code.ContextManager(t_wizard, printed.append) as ctx:
        player = lookup("Player")
        send_message(player, [t_wizard], "Subj", "body")
        parse.interpret(ctx, "@mail delete 1")
        printed.clear()
        parse.interpret(ctx, "@mail undelete 1")
    assert any("restored" in line for line in printed)
    assert len(get_mailbox(t_wizard)) == 1


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_at_mail_bad_subcommand(t_init: Object, t_wizard: Object):
    """@mail with an unrecognised argument prints a usage hint."""
    printed = []
    with code.ContextManager(t_wizard, printed.append) as ctx:
        parse.interpret(ctx, "@mail blah")
    assert any("Usage" in line for line in printed)


# --- @send ---


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_at_send_no_recipient_prints_error(t_init: Object, t_wizard: Object):
    """@send with no argument prints a usage error."""
    printed = []
    with code.ContextManager(t_wizard, printed.append) as ctx:
        parse.interpret(ctx, "@send")
    assert any("whom" in line.lower() for line in printed)


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_at_send_callback_delivers_message(t_init: Object, t_wizard: Object):
    """Invoking at_send_callback directly delivers a message to the recipient."""
    player = lookup("Player")
    verb = t_wizard.get_verb("at_send_callback")
    text = "Subject: Hello\n\nThis is the body."
    with code.ContextManager(t_wizard, lambda _: None):
        verb(text, player.pk)
    mailbox = get_mailbox(player)
    assert len(mailbox) == 1
    assert mailbox[0].message.subject == "Hello"
    assert "This is the body." in mailbox[0].message.body


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_at_send_callback_empty_body_prints_error(t_init: Object, t_wizard: Object):
    """at_send_callback with empty body prints an error and sends nothing."""
    player = lookup("Player")
    printed = []
    verb = t_wizard.get_verb("at_send_callback")
    with code.ContextManager(t_wizard, printed.append):
        verb("Subject: Hi\n\n", player.pk)
    assert any("empty" in line for line in printed)
    assert not get_mailbox(player)


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_at_send_with_syntax(t_init: Object, t_wizard: Object):
    """@send <player> with '...' delivers a message without opening the editor."""
    player = lookup("Player")
    printed = []
    with code.ContextManager(t_wizard, printed.append) as ctx:
        parse.interpret(ctx, '@send Player with "Subject: Hello\\n\\nHello there"')
    mailbox = get_mailbox(player)
    assert len(mailbox) == 1
    assert mailbox[0].message.subject == "Hello"
    assert "Hello there" in mailbox[0].message.body
    assert any("sent" in line.lower() for line in printed)


# --- @reply ---


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_at_reply_no_arg_prints_error(t_init: Object, t_wizard: Object):
    """@reply with no argument prints a usage error."""
    printed = []
    with code.ContextManager(t_wizard, printed.append) as ctx:
        parse.interpret(ctx, "@reply")
    assert any("which message" in line.lower() for line in printed)


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_at_reply_callback_delivers_reply(t_init: Object, t_wizard: Object):
    """at_reply_callback sends a reply to the original sender."""
    player = lookup("Player")
    send_message(t_wizard, [player], "Question", "What do you think?")
    verb = player.get_verb("at_reply_callback")
    with code.ContextManager(player, lambda _: None):
        verb("Subject: Re: Question\n\nI think yes.", t_wizard.pk, "Re: Question")
    mailbox = get_mailbox(t_wizard)
    assert any(mr.message.subject == "Re: Question" for mr in mailbox)


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_at_reply_with_syntax(t_init: Object, t_wizard: Object):
    """@reply <n> with '...' sends a reply without opening the editor."""
    player = lookup("Player")
    send_message(player, [t_wizard], "Question", "What do you think?")
    printed = []
    with code.ContextManager(t_wizard, printed.append) as ctx:
        parse.interpret(ctx, '@reply 1 with "I think yes."')
    mailbox = get_mailbox(player)
    assert any(mr.message.subject == "Re: Question" for mr in mailbox)
    assert any("I think yes." in mr.message.body for mr in mailbox)
    assert any("sent" in line.lower() for line in printed)


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_at_send_raw_mode_hints_with_form(t_init: Object, t_wizard: Object):
    """In raw mode, @send <player> (no `with`) prints the inline-form hint."""
    from moo.shell import prompt as prompt_module

    printed = []
    prompt_module._session_settings[t_wizard.owner.pk] = {"mode": "raw"}
    try:
        with code.ContextManager(t_wizard, printed.append) as ctx:
            parse.interpret(ctx, "@send Player")
    finally:
        prompt_module._session_settings.pop(t_wizard.owner.pk, None)
    assert any("Raw mode" in str(m) and "with" in str(m) for m in printed)


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_at_reply_raw_mode_hints_with_form(t_init: Object, t_wizard: Object):
    """In raw mode, @reply <n> (no `with`) prints the inline-form hint."""
    from moo.shell import prompt as prompt_module

    player = lookup("Player")
    send_message(player, [t_wizard], "Question", "What do you think?")
    printed = []
    prompt_module._session_settings[t_wizard.owner.pk] = {"mode": "raw"}
    try:
        with code.ContextManager(t_wizard, printed.append) as ctx:
            parse.interpret(ctx, "@reply 1")
    finally:
        prompt_module._session_settings.pop(t_wizard.owner.pk, None)
    assert any("Raw mode" in str(m) and "with" in str(m) for m in printed)


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_at_forward_raw_mode_hints_with_form(t_init: Object, t_wizard: Object):
    """In raw mode, @forward <n> to <player> (no `with`) prints the inline-form hint."""
    from moo.shell import prompt as prompt_module

    player = lookup("Player")
    send_message(player, [t_wizard], "Original", "Original body.")
    printed = []
    prompt_module._session_settings[t_wizard.owner.pk] = {"mode": "raw"}
    try:
        with code.ContextManager(t_wizard, printed.append) as ctx:
            parse.interpret(ctx, "@forward 1 to Player")
    finally:
        prompt_module._session_settings.pop(t_wizard.owner.pk, None)
    assert any("Raw mode" in str(m) and "with" in str(m) for m in printed)


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_at_forward_with_syntax(t_init: Object, t_wizard: Object):
    """@forward <n> to <player> with '...' forwards a message without opening the editor."""
    player = lookup("Player")
    send_message(player, [t_wizard], "Original Subject", "Original body.")
    printed = []
    with code.ContextManager(t_wizard, printed.append) as ctx:
        parse.interpret(ctx, '@forward 1 to Player with "See below."')
    mailbox = get_mailbox(player)
    fwd = next((mr for mr in mailbox if mr.message.subject.startswith("Fwd:")), None)
    assert fwd is not None
    assert "See below." in fwd.message.body
    assert "Original body." in fwd.message.body
    assert any("forwarded" in line.lower() for line in printed)


# --- confunc unread notification ---


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_confunc_shows_unread_notification(t_init: Object, t_wizard: Object):
    """confunc tells the player about unread mail when there are unread messages."""
    player = lookup("Player")
    send_message(t_wizard, [player], "Welcome", "Hi there.")
    with pytest.warns(RuntimeWarning, match=r"ConnectionError") as caught:
        with code.ContextManager(player, lambda _: None):
            verb = player.get_verb("confunc")
            verb()
    messages = [str(w.message) for w in caught.list]
    assert any("unread message" in m for m in messages)


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_confunc_no_notification_when_mailbox_empty(t_init: Object, t_wizard: Object):
    """confunc does not mention mail when the mailbox is empty."""
    player = lookup("Player")
    printed = []
    with code.ContextManager(player, printed.append):
        verb = player.get_verb("confunc")
        verb()
    assert not any("unread message" in line for line in printed)
