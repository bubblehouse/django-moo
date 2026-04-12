import pytest

from moo.core import code, parse
from moo.sdk import create, lookup
from moo.core.models import Object


def setup_book(wizard: Object, name: str = "test book") -> Object:
    system = lookup(1)
    book = create(name, parents=[system.book], location=wizard.location)
    book.set_property("notes", {})
    book.owner = wizard
    book.save()
    return book


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_write_adds_entry(t_init: Object, t_wizard: Object):
    """write in book with '#N: text' stores an entry keyed by room ID."""
    with code.ContextManager(t_wizard, lambda _: None) as ctx:
        book = setup_book(t_wizard)
        parse.interpret(ctx, 'write in "test book" with "#9: Kitchen done."')
    notes = book.get_property("notes")
    assert "#9" in notes
    assert "Kitchen done." in notes["#9"]
    assert t_wizard.name in notes["#9"]


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_write_bad_format_prints_error(t_init: Object, t_wizard: Object):
    """write without a leading room ID prints an error and stores nothing."""
    printed = []
    with code.ContextManager(t_wizard, printed.append) as ctx:
        book = setup_book(t_wizard)
        parse.interpret(ctx, 'write in "test book" with "No room ID here."')
    notes = book.get_property("notes")
    assert notes == {}
    assert any("room ID" in line for line in printed)


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_write_appends_to_existing_entry(t_init: Object, t_wizard: Object):
    """Multiple writes for the same room ID accumulate with newline separation."""
    with code.ContextManager(t_wizard, lambda _: None) as ctx:
        book = setup_book(t_wizard)
        parse.interpret(ctx, 'write in "test book" with "#9: Kitchen dug."')
        parse.interpret(ctx, 'write in "test book" with "#9: Stove lever added."')
    notes = book.get_property("notes")
    assert "Kitchen dug." in notes["#9"]
    assert "Stove lever added." in notes["#9"]
    assert "\n" in notes["#9"]


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_read_index_empty(t_init: Object, t_wizard: Object):
    """read with no argument on an empty book prints 'The book is empty.'"""
    printed = []
    with code.ContextManager(t_wizard, printed.append) as ctx:
        setup_book(t_wizard)
        parse.interpret(ctx, 'read "test book"')
    assert any("empty" in line for line in printed)


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_read_index_lists_rooms(t_init: Object, t_wizard: Object):
    """read with no argument lists all room IDs with previews."""
    printed = []
    with code.ContextManager(t_wizard, printed.append) as ctx:
        setup_book(t_wizard)
        parse.interpret(ctx, 'write in "test book" with "#9: Kitchen done."')
        parse.interpret(ctx, 'write in "test book" with "#22: Library done."')
        printed.clear()
        parse.interpret(ctx, 'read "test book"')
    text = "\n".join(printed)
    assert "#9" in text
    assert "#22" in text


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_read_page_shows_notes(t_init: Object, t_wizard: Object):
    """read book #9 shows the full notes for room #9."""
    printed = []
    with code.ContextManager(t_wizard, printed.append) as ctx:
        setup_book(t_wizard)
        parse.interpret(ctx, 'write in "test book" with "#9: Kitchen done. Needs coffee maker."')
        printed.clear()
        parse.interpret(ctx, 'read "test book" from "#9"')
    text = "\n".join(printed)
    assert "Kitchen done." in text
    assert "coffee maker" in text


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_read_page_missing_room(t_init: Object, t_wizard: Object):
    """read book from #2 prints 'No entry for #2.' when room is not in notes."""
    printed = []
    with code.ContextManager(t_wizard, printed.append) as ctx:
        setup_book(t_wizard)
        parse.interpret(ctx, 'read "test book" from "#2"')
    assert any("No entry" in line for line in printed)


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_erase_removes_room_entry(t_init: Object, t_wizard: Object):
    """erase book #9 removes the notes for room #9."""
    printed = []
    with code.ContextManager(t_wizard, printed.append) as ctx:
        book = setup_book(t_wizard)
        parse.interpret(ctx, 'write in "test book" with "#9: Kitchen done."')
        printed.clear()
        parse.interpret(ctx, 'erase "test book" from "#9"')
    notes = book.get_property("notes")
    assert "#9" not in notes
    assert any("Erased" in line for line in printed)


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_erase_missing_room(t_init: Object, t_wizard: Object):
    """erase book from #2 prints 'No entry for #2.' when the room is not in notes."""
    printed = []
    with code.ContextManager(t_wizard, printed.append) as ctx:
        setup_book(t_wizard)
        parse.interpret(ctx, 'erase "test book" from "#2"')
    assert any("No entry" in line for line in printed)


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_erase_non_owner_denied(t_init: Object, t_wizard: Object):
    """A non-owner, non-wizard player cannot erase pages."""
    player = lookup("Player")
    with code.ContextManager(t_wizard, lambda _: None) as ctx:
        book = setup_book(t_wizard)  # owner = t_wizard
        parse.interpret(ctx, 'write in "test book" with "#9: Kitchen."')
    printed = []
    with code.ContextManager(player, printed.append) as ctx:
        parse.interpret(ctx, 'erase "test book" from "#9"')
    notes = book.get_property("notes")
    assert "#9" in notes  # not erased
    assert any("permission" in line.lower() for line in printed)


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_wizard_can_erase(t_init: Object, t_wizard: Object):
    """A wizard can erase pages from books they don't own."""
    player = lookup("Player")
    with code.ContextManager(t_wizard, lambda _: None) as ctx:
        book = setup_book(t_wizard)
        book.owner = player
        book.save()
        parse.interpret(ctx, 'write in "test book" with "#9: Kitchen."')
    printed = []
    with code.ContextManager(t_wizard, printed.append) as ctx:
        parse.interpret(ctx, 'erase "test book" from "#9"')
    notes = book.get_property("notes")
    assert notes == {}


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_write_for_topic_stores_prefixed_key(t_init: Object, t_wizard: Object):
    """write in book for <topic> stores entry as topic:room_id."""
    with code.ContextManager(t_wizard, lambda _: None) as ctx:
        book = setup_book(t_wizard)
        parse.interpret(ctx, 'write in "test book" under tradesmen with "#9: Kitchen done."')
    notes = book.get_property("notes")
    assert "tradesmen:#9" in notes
    assert "Kitchen done." in notes["tradesmen:#9"]


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_write_for_topic_does_not_collide_with_plain(t_init: Object, t_wizard: Object):
    """Topic-keyed and plain entries for the same room don't overwrite each other."""
    with code.ContextManager(t_wizard, lambda _: None) as ctx:
        book = setup_book(t_wizard)
        parse.interpret(ctx, 'write in "test book" with "#9: Plain entry."')
        parse.interpret(ctx, 'write in "test book" under tradesmen with "#9: Topic entry."')
    notes = book.get_property("notes")
    assert "#9" in notes
    assert "tradesmen:#9" in notes


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_read_for_topic_shows_only_that_topic(t_init: Object, t_wizard: Object):
    """read book for <topic> shows only entries under that topic."""
    printed = []
    with code.ContextManager(t_wizard, printed.append) as ctx:
        book = setup_book(t_wizard)
        parse.interpret(ctx, 'write in "test book" under tradesmen with "#9: Kitchen done."')
        parse.interpret(ctx, 'write in "test book" under inspectors with "#22: Checked."')
        printed.clear()
        parse.interpret(ctx, 'read "test book" under tradesmen')
    text = "\n".join(printed)
    assert "#9" in text
    assert "#22" not in text


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_read_for_topic_from_room(t_init: Object, t_wizard: Object):
    """read book for <topic> from #9 shows the full entry for that room under the topic."""
    printed = []
    with code.ContextManager(t_wizard, printed.append) as ctx:
        book = setup_book(t_wizard)
        parse.interpret(ctx, 'write in "test book" under tradesmen with "#9: Needs coffee maker."')
        printed.clear()
        parse.interpret(ctx, 'read "test book" under tradesmen from "#9"')
    text = "\n".join(printed)
    assert "Needs coffee maker." in text


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_erase_for_topic_removes_all_topic_entries(t_init: Object, t_wizard: Object):
    """erase book for <topic> removes all entries prefixed with that topic."""
    printed = []
    with code.ContextManager(t_wizard, printed.append) as ctx:
        book = setup_book(t_wizard)
        parse.interpret(ctx, 'write in "test book" under tradesmen with "#9: Kitchen."')
        parse.interpret(ctx, 'write in "test book" under tradesmen with "#22: Library."')
        parse.interpret(ctx, 'write in "test book" under inspectors with "#9: Inspected."')
        printed.clear()
        parse.interpret(ctx, 'erase "test book" under tradesmen')
    notes = book.get_property("notes")
    assert "tradesmen:#9" not in notes
    assert "tradesmen:#22" not in notes
    assert "inspectors:#9" in notes  # other topic untouched
    assert any("2" in line for line in printed)  # "Erased 2 entries..."
