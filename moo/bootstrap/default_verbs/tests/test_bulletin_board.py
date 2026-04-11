import pytest

from moo.core import code, parse
from moo.sdk import create, lookup
from moo.core.models import Object


def setup_board(wizard: Object, name: str = "test board") -> Object:
    system = lookup(1)
    board = create(name, parents=[system.bulletin_board], location=wizard.location)
    board.set_property("entries", [])
    board.owner = wizard
    board.save()
    return board


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_post_adds_entry(t_init: Object, t_wizard: Object):
    """post on board with 'text' appends a tagged entry."""
    printed = []
    with code.ContextManager(t_wizard, printed.append) as ctx:
        board = setup_board(t_wizard)
        parse.interpret(ctx, 'post on "test board" with "Kitchen done."')
    entries = board.get_property("entries")
    assert len(entries) == 1
    assert "Kitchen done." in entries[0]
    assert t_wizard.name in entries[0]


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_post_multiple_entries(t_init: Object, t_wizard: Object):
    """Multiple posts accumulate without overwriting."""
    with code.ContextManager(t_wizard, lambda _: None) as ctx:
        board = setup_board(t_wizard)
        parse.interpret(ctx, 'post on "test board" with "First entry."')
        parse.interpret(ctx, 'post on "test board" with "Second entry."')
    entries = board.get_property("entries")
    assert len(entries) == 2


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
    """read shows numbered entries."""
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
def test_erase_by_key_removes_matching_entries(t_init: Object, t_wizard: Object):
    """erase board from '#9' removes entries containing '#9'."""
    printed = []
    with code.ContextManager(t_wizard, printed.append) as ctx:
        board = setup_board(t_wizard)
        parse.interpret(ctx, 'post on "test board" with "#9: Kitchen done."')
        parse.interpret(ctx, 'post on "test board" with "#22: Library done."')
        printed.clear()
        parse.interpret(ctx, 'erase "test board" from "#9"')
    entries = board.get_property("entries")
    assert len(entries) == 1
    assert "#22" in entries[0]
    assert any("1" in line for line in printed)  # "Erased 1 entry..."


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_erase_non_owner_denied(t_init: Object, t_wizard: Object):
    """A non-owner, non-wizard player cannot erase entries."""
    printed = []
    player = lookup("Player")
    with code.ContextManager(t_wizard, lambda _: None) as ctx:
        board = setup_board(t_wizard)  # owner = t_wizard
        parse.interpret(ctx, 'post on "test board" with "Some entry."')
    with code.ContextManager(player, printed.append) as ctx:
        parse.interpret(ctx, 'erase "test board" from "Some"')
    entries = board.get_property("entries")
    assert len(entries) == 1  # not erased
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
        parse.interpret(ctx, 'post on "test board" with "#9: done."')
    printed = []
    with code.ContextManager(t_wizard, printed.append) as ctx:
        parse.interpret(ctx, 'erase "test board" from "#9"')
    entries = board.get_property("entries")
    assert entries == []
