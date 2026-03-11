# -*- coding: utf-8 -*-
"""
Tests for moo/core/models/property.py — Property.
"""

import pytest

from .. import code, create
from ..models import Access, Object

def _ctx(wizard):
    return code.ContextManager(wizard, lambda m: None)


# ---------------------------------------------------------------------------
# Property.__str__ and .kind
# ---------------------------------------------------------------------------

@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_property_str(t_init, t_wizard):
    with _ctx(t_wizard):
        obj = create("prop str obj")
        obj.set_property("label", "hello")
    prop = obj.properties.get(name="label")
    s = str(prop)
    assert "label" in s
    assert str(obj) in s


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_property_kind(t_init, t_wizard):
    with _ctx(t_wizard):
        obj = create("prop kind obj")
        obj.set_property("x", 1)
    prop = obj.properties.get(name="x")
    assert prop.kind == "property"


# ---------------------------------------------------------------------------
# save() applies default permissions
# ---------------------------------------------------------------------------

@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_property_save_applies_default_permissions(t_init, t_wizard):
    with _ctx(t_wizard):
        obj = create("prop perm obj")
        obj.set_property("myprop", "value")
    prop = obj.properties.get(name="myprop")
    assert Access.objects.filter(property=prop).exists()


# ---------------------------------------------------------------------------
# inherit_owner propagation
# ---------------------------------------------------------------------------

@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_property_inherit_owner_propagates(t_init, t_wizard):
    with _ctx(t_wizard):
        parent = create("inh parent")
        child = create("inh child")
        child.parents.add(parent)
        # Set property AFTER parents.add so it is only on parent, not copied yet
        parent.set_property("shared", "data")

    with _ctx(t_wizard):
        # Flip inherit_owner on the parent's property — should push to child
        prop = parent.get_property("shared", original=True)
        prop.inherit_owner = True
        prop.save()

    # Child should now have a property row, and its owner should be child.owner
    child_prop = child.properties.get(name="shared")
    assert child_prop.owner == child.owner


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_property_inherit_owner_only_on_change(t_init, t_wizard):
    with _ctx(t_wizard):
        parent = create("no-change parent")
        child = create("no-change child")
        child.parents.add(parent)
        parent.set_property("already_inherited", "v")

    with _ctx(t_wizard):
        prop = parent.get_property("already_inherited", original=True)
        prop.inherit_owner = True
        prop.save()
        # Save again — already True, should not re-propagate (no error)
        prop.save()

    # Child's property should still be consistent
    assert child.properties.filter(name="already_inherited").exists()


# ---------------------------------------------------------------------------
# Value roundtrip via moojson
# ---------------------------------------------------------------------------

@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_property_value_roundtrip_string(t_init, t_wizard):
    with _ctx(t_wizard):
        obj = create("rt str obj")
        obj.set_property("greeting", "hello world")
    with _ctx(t_wizard):
        assert obj.get_property("greeting") == "hello world"


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_property_value_roundtrip_integer(t_init, t_wizard):
    with _ctx(t_wizard):
        obj = create("rt int obj")
        obj.set_property("count", 42)
    with _ctx(t_wizard):
        assert obj.get_property("count") == 42


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_property_value_roundtrip_list(t_init, t_wizard):
    with _ctx(t_wizard):
        obj = create("rt list obj")
        obj.set_property("items", ["a", "b", "c"])
    with _ctx(t_wizard):
        assert obj.get_property("items") == ["a", "b", "c"]


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_property_value_roundtrip_none(t_init, t_wizard):
    with _ctx(t_wizard):
        obj = create("rt none obj")
        obj.set_property("empty", None)
    with _ctx(t_wizard):
        assert obj.get_property("empty") is None


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_property_value_roundtrip_object_ref(t_init, t_wizard):
    with _ctx(t_wizard):
        target = create("rt ref target")
        holder = create("rt ref holder")
        holder.set_property("ref", target)
    with _ctx(t_wizard):
        result = holder.get_property("ref")
    assert result == target


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_child_owns_inherited_property(t_init: Object):
    player = Object.objects.get(name="Player")
    room_class = Object.objects.get(name="room class")
    room = Object.objects.create(name="new room", owner=player)
    room.parents.add(room_class)
    description = room.get_property(name="description", recurse=False, original=True)
    assert description.origin == room


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_returned_property_is_from_correct_object(t_init: Object):
    player = Object.objects.get(name="Player")
    room_class = Object.objects.get(name="room class")
    room = Object.objects.create(name="new room", owner=player)
    room.parents.add(room_class)
    description = room.get_property(name="description", recurse=False, original=True)
    assert description.owner == player


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_property_inheritance_can_change_after_save(t_init: Object, t_wizard: Object):
    player = Object.objects.get(name="Player")
    o = Object.objects.create(name="new object", owner=player)
    p = Object.objects.create(name="new parent", owner=t_wizard)
    p.set_property("test_post_creation", "There's not much to see here.", owner=t_wizard)
    o.parents.add(p)

    description = o.get_property(name="test_post_creation", recurse=False, original=True)
    assert description.owner == player

    # You normally don't want to change the inheritence after creation, but it should be possible
    description = p.get_property(name="test_post_creation", recurse=False, original=True)
    description.inherit_owner = True
    description.save()

    # you just need to delete the inherited property and re-add the parent to re-inherit it with the correct owner
    o.get_property(name="test_post_creation", recurse=False, original=True).delete()
    o.parents.remove(p)
    o.parents.add(p)

    description = o.get_property(name="test_post_creation", recurse=False, original=True)
    assert description.owner == t_wizard
