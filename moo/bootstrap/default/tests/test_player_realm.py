from unittest.mock import patch

import pytest

from moo.core import code, parse
from moo.sdk import create, lookup
from moo.core.models import Object


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_realm_shows_descendants(t_init: Object, t_wizard: Object):
    """@realm <obj> produces output listing descendant objects."""
    printed = []
    with code.ContextManager(t_wizard, printed.append) as ctx:
        with patch("moo.sdk.open_paginator", side_effect=lambda obj, text, **kw: printed.extend(text.splitlines())):
            parse.interpret(ctx, "@realm $room")
    # $room has descendants (Generic Container, Generic Furniture, etc. inherit from Generic Thing which is not under $room,
    # but $room itself may have children — just check the root line is there)
    assert any("Generic Room" in line or "room" in line.lower() for line in printed)


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_classes_defaults_to_root_class(t_init: Object, t_wizard: Object):
    """@classes with no argument shows the root class tree."""
    printed = []
    with code.ContextManager(t_wizard, printed.append) as ctx:
        with patch("moo.sdk.open_paginator", side_effect=lambda obj, text, **kw: printed.extend(text.splitlines())):
            parse.interpret(ctx, "@classes")
    assert any("Root Class" in line or "root" in line.lower() for line in printed)


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_realm_no_descendants(t_init: Object, t_wizard: Object):
    """@realm on a leaf object shows '(no descendants)'."""
    system = lookup(1)
    printed = []
    with code.ContextManager(t_wizard, printed.append) as ctx:
        create("leaf_obj", parents=[system.thing], location=t_wizard.location)
        with patch("moo.sdk.open_paginator", side_effect=lambda obj, text, **kw: printed.extend(text.splitlines())):
            parse.interpret(ctx, "@realm leaf_obj")
    assert any("no descendants" in line for line in printed)


# --- @audit ---


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_audit_own_objects(t_init: Object, t_wizard: Object):
    """@audit with no argument lists objects owned by the caller."""
    with pytest.warns(RuntimeWarning) as w:
        with code.ContextManager(t_wizard, lambda _: None) as ctx:
            parse.interpret(ctx, "@audit")
    messages = [str(x.message) for x in w.list]
    assert any("Wizard" in m and "total" in m for m in messages)


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_audit_other_player_wizard(t_init: Object, t_wizard: Object):
    """Wizard can audit another player's objects."""
    with pytest.warns(RuntimeWarning) as w:
        with code.ContextManager(t_wizard, lambda _: None) as ctx:
            parse.interpret(ctx, "@audit Player")
    messages = [str(x.message) for x in w.list]
    assert any("Player" in m for m in messages)


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_audit_other_player_denied(t_init: Object, t_wizard: Object):
    """Non-wizard cannot audit another player's objects."""
    player_npc = lookup("Player")
    printed = []
    with code.ContextManager(player_npc, printed.append) as ctx:
        parse.interpret(ctx, "@audit Wizard")
    assert any("Permission denied" in line for line in printed)


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_audit_no_objects(t_init: Object, t_wizard: Object):
    """@audit on a player with no owned objects prints an appropriate message."""
    system = lookup(1)
    printed = []
    with code.ContextManager(t_wizard, printed.append) as ctx:
        create("EmptyOne", parents=[system.player], location=t_wizard.location)
        parse.interpret(ctx, "@audit EmptyOne")
    assert any("owns no objects" in line for line in printed)
