import pytest

from moo.core import code, parse
from moo.sdk import lookup
from moo.sdk.mail import send_message, get_mailbox
from moo.core.models import Object


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_check_inbox_no_mail(t_init: Object, t_wizard: Object):
    """check_inbox with no unread mail prints '[Mail] No new messages.'."""
    printed = []
    with code.ContextManager(t_wizard, printed.append) as ctx:
        parse.interpret(ctx, "check_inbox")
    assert any("[Mail] No new messages." in line for line in printed)


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_check_inbox_prints_report_line(t_init: Object, t_wizard: Object):
    """check_inbox with unread mail prints a '[Mail] From <sender>: <body>' line."""
    player = lookup("Player")
    send_message(player, [t_wizard], "Work Report", "Kitchen built. Needs coffee maker.")
    printed = []
    with code.ContextManager(t_wizard, printed.append) as ctx:
        parse.interpret(ctx, "check_inbox")
    report_lines = [line for line in printed if line.startswith("[Mail] From")]
    assert len(report_lines) == 1
    assert "Player" in report_lines[0]
    assert "Kitchen built" in report_lines[0]


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_check_inbox_marks_message_read(t_init: Object, t_wizard: Object):
    """check_inbox marks the fetched message as read."""
    player = lookup("Player")
    send_message(player, [t_wizard], "Work Report", "Kitchen built.")
    with code.ContextManager(t_wizard, lambda _: None) as ctx:
        parse.interpret(ctx, "check_inbox")
    mr = get_mailbox(t_wizard)[0]
    assert mr.read


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_check_inbox_only_fetches_unread(t_init: Object, t_wizard: Object):
    """check_inbox only reports unread messages; already-read messages produce '[Mail] No new messages.'."""
    player = lookup("Player")
    send_message(player, [t_wizard], "Old Report", "Already read.")
    # Mark as read first
    with code.ContextManager(t_wizard, lambda _: None) as ctx:
        parse.interpret(ctx, "check_inbox")
    # Check again — should now report none
    printed = []
    with code.ContextManager(t_wizard, printed.append) as ctx:
        parse.interpret(ctx, "check_inbox")
    assert any("[Mail] No new messages." in line for line in printed)


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_check_inbox_newlines_flattened(t_init: Object, t_wizard: Object):
    """check_inbox replaces newlines in the body with spaces for the [Mail] line."""
    player = lookup("Player")
    send_message(player, [t_wizard], "Multi-line", "Line one.\nLine two.")
    printed = []
    with code.ContextManager(t_wizard, printed.append) as ctx:
        parse.interpret(ctx, "check_inbox")
    report_lines = [line for line in printed if line.startswith("[Mail] From")]
    assert "\n" not in report_lines[0]
    assert "Line one." in report_lines[0]
    assert "Line two." in report_lines[0]
