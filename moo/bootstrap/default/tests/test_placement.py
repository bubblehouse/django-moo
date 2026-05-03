# -*- coding: utf-8 -*-
# pylint: disable=no-value-for-parameter,unused-variable
"""
Tests for the placement system:
  - place.py verb
  - tell_contents placement grouping
  - room look spatial preps
  - take/drop clearing placement
  - moveto clearing dependent placements
  - delete target clearing placement
  - parser obvious filter
"""

import pytest

from moo.core import code, parse
from moo.core.models import Object
from moo.sdk import create, lookup


def _writer_ctx(t_wizard):
    printed = []

    def writer(msg):
        printed.append(msg)

    return printed, writer


def _make_thing(name, room, obvious=True):
    system = lookup(1)
    obj = create(name, parents=[system.thing], location=room)
    if obvious:
        obj.obvious = True
        obj.save()
    return obj


# ---------------------------------------------------------------------------
# Object model methods
# ---------------------------------------------------------------------------


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_set_placement_method(t_init: Object, t_wizard: Object):
    _, writer = _writer_ctx(t_wizard)
    with code.ContextManager(t_wizard, writer):
        lab = t_wizard.location
        desk = _make_thing("desk", lab)
        book = _make_thing("book", lab)
        book.set_placement("on", desk)
    book.refresh_from_db()
    assert book.placement_prep == "on"
    assert book.placement_target == desk
    assert book.placement == ("on", desk)
    assert book.is_placed()


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_clear_placement_method(t_init: Object, t_wizard: Object):
    _, writer = _writer_ctx(t_wizard)
    with code.ContextManager(t_wizard, writer):
        lab = t_wizard.location
        desk = _make_thing("desk", lab)
        book = _make_thing("book", lab)
        book.set_placement("on", desk)
        book.clear_placement()
    book.refresh_from_db()
    assert book.placement_prep is None
    assert book.placement_target_id is None
    assert book.placement is None
    assert not book.is_placed()


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_is_hidden_placement(t_init: Object, t_wizard: Object):
    _, writer = _writer_ctx(t_wizard)
    with code.ContextManager(t_wizard, writer):
        lab = t_wizard.location
        desk = _make_thing("desk", lab)
        obj = _make_thing("coin", lab)
        for prep in ("under", "behind"):
            obj.set_placement(prep, desk)
            assert obj.is_hidden_placement(), f"{prep} should be hidden"
        for prep in ("on", "before", "beside", "over"):
            obj.set_placement(prep, desk)
            assert not obj.is_hidden_placement(), f"{prep} should not be hidden"


# ---------------------------------------------------------------------------
# place verb
# ---------------------------------------------------------------------------


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_place_from_inventory_moves_to_room(t_init: Object, t_wizard: Object):
    printed, writer = _writer_ctx(t_wizard)
    with code.ContextManager(t_wizard, writer) as ctx:
        lab = t_wizard.location
        desk = _make_thing("desk", lab)
        book = _make_thing("book", lab)
        book.moveto(t_wizard)  # put in inventory first
        assert book.location == t_wizard
        parse.interpret(ctx, "place book on desk")
    book.refresh_from_db()
    assert book.location == lab  # moved out of inventory into room
    assert book.placement_prep == "on"
    assert book.placement_target == desk
    assert any("place" in m.lower() for m in printed)


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_place_on_object(t_init: Object, t_wizard: Object):
    printed, writer = _writer_ctx(t_wizard)
    with code.ContextManager(t_wizard, writer) as ctx:
        lab = t_wizard.location
        desk = _make_thing("desk", lab)
        book = _make_thing("book", lab)
        parse.interpret(ctx, "place book on desk")
    book.refresh_from_db()
    assert book.placement_prep == "on"
    assert book.placement_target == desk
    assert book.location == lab  # metadata model: stays in room
    assert any("place" in m.lower() for m in printed)


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_place_under_item(t_init: Object, t_wizard: Object):
    printed, writer = _writer_ctx(t_wizard)
    with code.ContextManager(t_wizard, writer) as ctx:
        lab = t_wizard.location
        rug = _make_thing("rug", lab)
        key = _make_thing("key", lab)
        parse.interpret(ctx, "place key under rug")
    key.refresh_from_db()
    assert key.placement_prep == "under"
    assert key.placement_target == rug
    assert key.is_hidden_placement()
    assert key.obvious  # obvious is unchanged


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_place_behind_item(t_init: Object, t_wizard: Object):
    _, writer = _writer_ctx(t_wizard)
    with code.ContextManager(t_wizard, writer) as ctx:
        lab = t_wizard.location
        painting = _make_thing("painting", lab)
        coin = _make_thing("coin", lab)
        parse.interpret(ctx, "place coin behind painting")
    coin.refresh_from_db()
    assert coin.placement_prep == "behind"
    assert coin.is_hidden_placement()
    assert coin.obvious  # unchanged


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_place_on_self_blocked(t_init: Object, t_wizard: Object):
    printed, writer = _writer_ctx(t_wizard)
    with code.ContextManager(t_wizard, writer) as ctx:
        lab = t_wizard.location
        book = _make_thing("book", lab)
        parse.interpret(ctx, "place book on book")
    book.refresh_from_db()
    assert book.placement is None
    assert any("itself" in m for m in printed)


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_surface_types_restricts_placement(t_init: Object, t_wizard: Object):
    printed, writer = _writer_ctx(t_wizard)
    with code.ContextManager(t_wizard, writer) as ctx:
        lab = t_wizard.location
        desk = _make_thing("desk", lab)
        desk.set_property("surface_types", ["on"])
        book = _make_thing("book", lab)
        parse.interpret(ctx, "place book under desk")
    book.refresh_from_db()
    assert book.placement is None
    assert any("can't place" in m for m in printed)


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_surface_types_absent_allows_all(t_init: Object, t_wizard: Object):
    _, writer = _writer_ctx(t_wizard)
    with code.ContextManager(t_wizard, writer) as ctx:
        lab = t_wizard.location
        desk = _make_thing("desk", lab)
        book = _make_thing("book", lab)
        parse.interpret(ctx, "place book under desk")
    book.refresh_from_db()
    assert book.placement_prep == "under"


# ---------------------------------------------------------------------------
# tell_contents
# ---------------------------------------------------------------------------


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_tell_contents_groups_placed_items(t_init: Object, t_wizard: Object):
    printed, writer = _writer_ctx(t_wizard)
    with code.ContextManager(t_wizard, writer) as ctx:
        lab = t_wizard.location
        desk = _make_thing("desk", lab)
        book = _make_thing("book", lab)
        book.set_placement("on", desk)
        parse.interpret(ctx, "look")
    # Surface grouping line should appear somewhere
    surface_lines = [m for m in printed if "desk" in m and "book" in m]
    assert surface_lines, f"Expected surface grouping, got: {printed}"


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_tell_contents_hides_under(t_init: Object, t_wizard: Object):
    printed, writer = _writer_ctx(t_wizard)
    with code.ContextManager(t_wizard, writer) as ctx:
        lab = t_wizard.location
        rug = _make_thing("rug", lab)
        key = _make_thing("key", lab)
        key.set_placement("under", rug)
        parse.interpret(ctx, "look")
    key_lines = [m for m in printed if "key" in m.lower()]
    assert not key_lines, f"Key should be hidden, got: {key_lines}"


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_tell_contents_obvious_false_hides_from_surface_grouping(t_init: Object, t_wizard: Object):
    printed, writer = _writer_ctx(t_wizard)
    with code.ContextManager(t_wizard, writer) as ctx:
        lab = t_wizard.location
        desk = _make_thing("desk", lab)
        scroll = _make_thing("scroll", lab, obvious=False)
        scroll.set_placement("on", desk)
        parse.interpret(ctx, "look")
    scroll_lines = [m for m in printed if "scroll" in m.lower()]
    assert not scroll_lines, f"obvious=False item should not appear, got: {scroll_lines}"


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_tell_contents_unplaced_shown_normally(t_init: Object, t_wizard: Object):
    printed, writer = _writer_ctx(t_wizard)
    with code.ContextManager(t_wizard, writer) as ctx:
        lab = t_wizard.location
        lamp = _make_thing("lamp", lab)
        parse.interpret(ctx, "look")
    lamp_lines = [m for m in printed if "lamp" in m.lower()]
    assert lamp_lines, "Unplaced obvious item should appear in tell_contents"


# ---------------------------------------------------------------------------
# look under / on / behind
# ---------------------------------------------------------------------------


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_look_under_reveals_hidden(t_init: Object, t_wizard: Object):
    printed, writer = _writer_ctx(t_wizard)
    with code.ContextManager(t_wizard, writer) as ctx:
        lab = t_wizard.location
        rug = _make_thing("rug", lab)
        key = _make_thing("key", lab)
        key.set_placement("under", rug)
        parse.interpret(ctx, "look under rug")
    assert any("key" in m.lower() for m in printed), f"Expected key in output, got: {printed}"


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_look_under_empty(t_init: Object, t_wizard: Object):
    printed, writer = _writer_ctx(t_wizard)
    with code.ContextManager(t_wizard, writer) as ctx:
        lab = t_wizard.location
        chair = _make_thing("chair", lab)
        parse.interpret(ctx, "look under chair")
    assert any("nothing" in m.lower() for m in printed), f"Expected 'nothing', got: {printed}"


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_look_on_desk_reveals_placed(t_init: Object, t_wizard: Object):
    printed, writer = _writer_ctx(t_wizard)
    with code.ContextManager(t_wizard, writer) as ctx:
        lab = t_wizard.location
        desk = _make_thing("desk", lab)
        book = _make_thing("book", lab)
        book.set_placement("on", desk)
        parse.interpret(ctx, "look on desk")
    assert any("book" in m.lower() for m in printed), f"Expected book in output, got: {printed}"


# ---------------------------------------------------------------------------
# take / drop
# ---------------------------------------------------------------------------


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_take_from_surface_clears_placement(t_init: Object, t_wizard: Object):
    _, writer = _writer_ctx(t_wizard)
    with code.ContextManager(t_wizard, writer) as ctx:
        lab = t_wizard.location
        desk = _make_thing("desk", lab)
        book = _make_thing("book", lab)
        book.set_placement("on", desk)
        parse.interpret(ctx, "take book from desk")
    book.refresh_from_db()
    assert book.location == t_wizard
    assert book.placement is None


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_take_direct_clears_placement(t_init: Object, t_wizard: Object):
    _, writer = _writer_ctx(t_wizard)
    with code.ContextManager(t_wizard, writer) as ctx:
        lab = t_wizard.location
        desk = _make_thing("desk", lab)
        book = _make_thing("book", lab)
        book.set_placement("on", desk)
        parse.interpret(ctx, "take book")
    book.refresh_from_db()
    assert book.location == t_wizard
    assert book.placement is None


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_take_from_wrong_surface_fails(t_init: Object, t_wizard: Object):
    printed, writer = _writer_ctx(t_wizard)
    with code.ContextManager(t_wizard, writer) as ctx:
        lab = t_wizard.location
        desk = _make_thing("desk", lab)
        table = _make_thing("table", lab)
        book = _make_thing("book", lab)
        book.set_placement("on", desk)
        parse.interpret(ctx, "take book from table")
    book.refresh_from_db()
    assert book.location == lab  # not taken
    assert any("isn't on" in m for m in printed)


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_drop_clears_placement(t_init: Object, t_wizard: Object):
    _, writer = _writer_ctx(t_wizard)
    with code.ContextManager(t_wizard, writer) as ctx:
        lab = t_wizard.location
        desk = _make_thing("desk", lab)
        book = _make_thing("book", lab)
        book.set_placement("on", desk)
        book.moveto(t_wizard)  # put in inventory first
        parse.interpret(ctx, "drop book")
    book.refresh_from_db()
    assert book.placement is None


# ---------------------------------------------------------------------------
# moveto clears dependent placements
# ---------------------------------------------------------------------------


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_moveto_clears_dependent_placements(t_init: Object, t_wizard: Object):
    _, writer = _writer_ctx(t_wizard)
    with code.ContextManager(t_wizard, writer) as ctx:
        lab = t_wizard.location
        system = lookup(1)
        other_room = create("Other Room", parents=[system.room], location=None)
        desk = _make_thing("desk", lab)
        book = _make_thing("book", lab)
        book.set_placement("on", desk)
        desk.moveto(other_room)
    book.refresh_from_db()
    assert book.placement is None
    assert book.location == lab  # book stays in room


# ---------------------------------------------------------------------------
# delete target clears placement
# ---------------------------------------------------------------------------


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_delete_target_clears_placement(t_init: Object, t_wizard: Object):
    _, writer = _writer_ctx(t_wizard)
    with code.ContextManager(t_wizard, writer):
        lab = t_wizard.location
        desk = _make_thing("desk", lab)
        book = _make_thing("book", lab)
        book.set_placement("on", desk)
        desk.delete()
    book.refresh_from_db()
    assert book.placement is None
    assert book.placement_prep is None
    assert book.placement_target_id is None


# ---------------------------------------------------------------------------
# Parser obvious filter
# ---------------------------------------------------------------------------


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_parser_obvious_filter_hides_nonobvious(t_init: Object, t_wizard: Object):
    _, writer = _writer_ctx(t_wizard)
    with code.ContextManager(t_wizard, writer) as ctx:
        lab = t_wizard.location
        rug = _make_thing("rug", lab)
        key = _make_thing("key", lab)
        key.set_placement("under", rug)  # hidden placement makes key invisible to parser
        parse.interpret(ctx, "take key")
    key.refresh_from_db()
    assert key.location == lab  # not taken; hidden-placed objects are invisible to parser


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_parser_obvious_filter_from_bypasses(t_init: Object, t_wizard: Object):
    _, writer = _writer_ctx(t_wizard)
    with code.ContextManager(t_wizard, writer) as ctx:
        lab = t_wizard.location
        rug = _make_thing("rug", lab)
        key = _make_thing("key", lab)
        key.set_placement("under", rug)  # hidden placement; "from" bypasses the filter
        parse.interpret(ctx, "take key from rug")
    key.refresh_from_db()
    assert key.location == t_wizard  # taken successfully
    assert key.placement is None
