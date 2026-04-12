import pytest

from moo.core import code, parse
from moo.sdk import create, lookup
from moo.core.models import Object


def setup_board(wizard: Object, name: str = "test board") -> Object:
    system = lookup(1)
    board = create(name, parents=[system.bulletin_board], location=wizard.location)
    board.set_property("entries", [])
    board.set_property("topics", {})
    board.owner = wizard
    board.save()
    return board


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_post_adds_entry(t_init: Object, t_wizard: Object):
    """post on board with 'text' appends a tagged general entry."""
    printed = []
    with code.ContextManager(t_wizard, printed.append) as ctx:
        setup_board(t_wizard)
        parse.interpret(ctx, 'post on "test board" with "Kitchen done."')
    board = lookup("test board")
    entries = board.get_property("entries")
    assert len(entries) == 1
    assert "Kitchen done." in entries[0]
    assert t_wizard.name in entries[0]


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_post_multiple_entries(t_init: Object, t_wizard: Object):
    """Multiple general posts accumulate without overwriting."""
    with code.ContextManager(t_wizard, lambda _: None) as ctx:
        setup_board(t_wizard)
        parse.interpret(ctx, 'post on "test board" with "First entry."')
        parse.interpret(ctx, 'post on "test board" with "Second entry."')
    board = lookup("test board")
    assert len(board.get_property("entries")) == 2


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_post_for_topic_stores_in_topics(t_init: Object, t_wizard: Object):
    """post on board for <topic> with 'text' stores under topics dict."""
    printed = []
    with code.ContextManager(t_wizard, printed.append) as ctx:
        setup_board(t_wizard)
        parse.interpret(ctx, 'post on "test board" under tradesmen with "#9|#22"')
    board = lookup("test board")
    topics = board.get_property("topics")
    assert topics.get("tradesmen") == "#9|#22"
    assert any("tradesmen" in line for line in printed)


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_post_for_topic_overwrites(t_init: Object, t_wizard: Object):
    """Posting to the same topic twice overwrites the previous value."""
    with code.ContextManager(t_wizard, lambda _: None) as ctx:
        setup_board(t_wizard)
        parse.interpret(ctx, 'post on "test board" under tradesmen with "#9|#22"')
        parse.interpret(ctx, 'post on "test board" under tradesmen with "#33|#44"')
    board = lookup("test board")
    assert board.get_property("topics")["tradesmen"] == "#33|#44"


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_read_empty_board(t_init: Object, t_wizard: Object):
    """read on an empty board prints 'The board is blank.'"""
    printed = []
    with code.ContextManager(t_wizard, printed.append) as ctx:
        setup_board(t_wizard)
        parse.interpret(ctx, 'read "test board"')
    assert any("blank" in line for line in printed)


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_read_board_with_entries(t_init: Object, t_wizard: Object):
    """read shows numbered general entries."""
    printed = []
    with code.ContextManager(t_wizard, printed.append) as ctx:
        setup_board(t_wizard)
        parse.interpret(ctx, 'post on "test board" with "Room #9 done."')
        printed.clear()
        parse.interpret(ctx, 'read "test board"')
    assert any("Room #9 done." in line for line in printed)
    assert any("1." in line for line in printed)


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_read_board_for_topic(t_init: Object, t_wizard: Object):
    """read board for <topic> shows only that topic's value."""
    printed = []
    with code.ContextManager(t_wizard, printed.append) as ctx:
        setup_board(t_wizard)
        parse.interpret(ctx, 'post on "test board" under tradesmen with "#9|#22"')
        printed.clear()
        parse.interpret(ctx, 'read "test board" under tradesmen')
    assert any("#9|#22" in line for line in printed)


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_read_board_for_missing_topic(t_init: Object, t_wizard: Object):
    """read board for unknown topic prints 'Nothing posted'."""
    printed = []
    with code.ContextManager(t_wizard, printed.append) as ctx:
        setup_board(t_wizard)
        parse.interpret(ctx, 'read "test board" under inspectors')
    assert any("Nothing posted" in line for line in printed)


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_erase_topic(t_init: Object, t_wizard: Object):
    """erase board for <topic> removes that topic from the dict."""
    printed = []
    with code.ContextManager(t_wizard, printed.append) as ctx:
        setup_board(t_wizard)
        parse.interpret(ctx, 'post on "test board" under tradesmen with "#9|#22"')
        printed.clear()
        parse.interpret(ctx, 'erase "test board" under tradesmen')
    board = lookup("test board")
    assert "tradesmen" not in (board.get_property("topics") or {})
    assert any("erased" in line.lower() for line in printed)


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_erase_clears_general_entries(t_init: Object, t_wizard: Object):
    """erase board (no for) clears all general entries."""
    with code.ContextManager(t_wizard, lambda _: None) as ctx:
        setup_board(t_wizard)
        parse.interpret(ctx, 'post on "test board" with "Some entry."')
        parse.interpret(ctx, 'erase "test board"')
    board = lookup("test board")
    assert board.get_property("entries") == []


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_erase_non_owner_denied(t_init: Object, t_wizard: Object):
    """A non-owner, non-wizard player cannot erase."""
    printed = []
    player = lookup("Player")
    with code.ContextManager(t_wizard, lambda _: None) as ctx:
        setup_board(t_wizard)
        parse.interpret(ctx, 'post on "test board" with "Some entry."')
    with code.ContextManager(player, printed.append) as ctx:
        parse.interpret(ctx, 'erase "test board" under tradesmen')
    assert any("permission" in line.lower() for line in printed)


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_wizard_can_erase(t_init: Object, t_wizard: Object):
    """A wizard can erase entries even on boards they don't own."""
    player = lookup("Player")
    with code.ContextManager(t_wizard, lambda _: None) as ctx:
        board = setup_board(t_wizard)
        board.owner = player
        board.save()
        parse.interpret(ctx, 'post on "test board" under tradesmen with "#9"')
    printed = []
    with code.ContextManager(t_wizard, printed.append) as ctx:
        parse.interpret(ctx, 'erase "test board" under tradesmen')
    board = lookup("test board")
    assert "tradesmen" not in (board.get_property("topics") or {})
