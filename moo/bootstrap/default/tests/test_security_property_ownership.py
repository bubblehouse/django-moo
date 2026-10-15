"""
Property rows keep their owner when their value changes.

``Object.set_property`` used to write ``owner = context.player`` onto the row
before ``Property.save`` checked ``write``, so the check always passed for the
writer, and anyone with ``write`` on an object could take over and rewrite any
row on it. Every avatar also owned its own ``ownership_quota`` row, so a
``$builder`` could ``@set`` an unlimited quota. An update now keeps the row's
owner, the quota row stays Wizard-owned, and the engine adjusts the quota
directly.
"""

import pytest

from moo.core import code, parse
from moo.core.models import Object
from moo.sdk import create, lookup


def builder(t_wizard):
    """Return the stock non-wizard avatar as a ``$builder``."""
    p = lookup("Player")
    with code.ContextManager(t_wizard, lambda _: None):
        p.parents.add(lookup(1).builder)
    return p


def quota_row(t_wizard, avatar):
    """Return the avatar's own ``ownership_quota`` Property row."""
    with code.ContextManager(t_wizard, lambda _: None):
        return avatar.get_property("ownership_quota", recurse=False, original=True)


def run(avatar, line):
    """Run one command as `avatar` and return its printed output."""
    out = []
    with code.ContextManager(avatar, out.append) as ctx:
        parse.interpret(ctx, line)
    return out


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_avatar_quota_row_belongs_to_wizard(t_init: Object, t_wizard: Object):
    """``$player.ownership_quota`` has ``inherit_owner``, so every avatar's copy stays Wizard-owned."""
    row = quota_row(t_wizard, lookup("Player"))
    assert row.owner == t_wizard
    assert row.inherit_owner


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_builder_cannot_raise_own_quota(t_init: Object, t_wizard: Object):
    """``@set`` runs with the player's permissions and the row is not theirs."""
    p = builder(t_wizard)
    with pytest.raises(PermissionError):
        run(p, "@set ownership_quota on me to 99999")
    assert quota_row(t_wizard, p).value == "1000"


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_engine_still_charges_and_refunds_quota(t_init: Object, t_wizard: Object):
    """``create``, ``@recycle`` and ``@restore`` adjust the quota and leave the row with the Wizard."""
    p = builder(t_wizard)
    run(p, "@create widget")
    row = quota_row(t_wizard, p)
    assert (row.value, row.owner) == ("999", t_wizard)
    widget = lookup("widget")
    run(p, f"@recycle #{widget.pk}")
    assert quota_row(t_wizard, p).value == "1000"
    run(p, "@restore widget")
    row = quota_row(t_wizard, p)
    assert (row.value, row.owner) == ("999", t_wizard)


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_exhausted_quota_blocks_create(t_init: Object, t_wizard: Object):
    """At zero, ``create()`` raises ``QuotaError``; only a wizard can raise it again."""
    p = builder(t_wizard)
    with code.ContextManager(t_wizard, lambda _: None):
        p.set_property("ownership_quota", 0)
    out = []
    with code.ContextManager(p, out.append) as ctx:
        with pytest.raises(Exception, match="run out of quota"):
            parse.interpret(ctx, "@create widget")
    assert quota_row(t_wizard, p).owner == t_wizard


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_write_on_object_does_not_take_over_rows(t_init: Object, t_wizard: Object):
    """An object owner can no longer rewrite a Wizard-owned row on their object."""
    p = builder(t_wizard)
    with code.ContextManager(t_wizard, lambda _: None):
        box = create("Player Box", parents=[lookup(1).thing], location=None)
        box.owner = p
        box.save()
    # A Wizard-owned verb writes the row while no player context is active.
    with code.ContextManager(t_wizard, lambda _: None, player=t_wizard):
        box.set_property("seal", "intact")
    with code.ContextManager(p, lambda _: None):
        with pytest.raises(PermissionError):
            box.set_property("seal", "broken")
    with code.ContextManager(t_wizard, lambda _: None):
        row = box.get_property("seal", original=True)
    assert (row.value, row.owner) == ('"intact"', t_wizard)


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_writing_a_value_keeps_the_owner(t_init: Object, t_wizard: Object):
    """A wizard updating a player's row leaves the player as its owner."""
    p = builder(t_wizard)
    run(p, '@set motto on me to "onward"')
    with code.ContextManager(t_wizard, lambda _: None, player=t_wizard):
        p.set_property("motto", "upward")
        row = p.get_property("motto", original=True)
    assert (row.value, row.owner) == ('"upward"', p)


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_inherit_owner_cascade_uses_the_parent_row_owner(t_init: Object, t_wizard: Object):
    """Turning on ``inherit_owner`` gives descendants the parent row's owner, as a parent-add copy would."""
    sys = lookup(1)
    p = builder(t_wizard)
    with code.ContextManager(t_wizard, lambda _: None, player=t_wizard):
        sys.player.set_property("badge", "none")
    run(p, '@set badge on me to "mine"')
    with code.ContextManager(t_wizard, lambda _: None):
        assert p.get_property("badge", recurse=False, original=True).owner == p
    with code.ContextManager(t_wizard, lambda _: None, player=t_wizard):
        sys.player.set_property("badge", "none", inherit_owner=True)
    with code.ContextManager(t_wizard, lambda _: None):
        row = p.get_property("badge", recurse=False, original=True)
    assert (row.owner, row.value) == (t_wizard, '"mine"')
