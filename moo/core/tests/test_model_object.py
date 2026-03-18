# -*- coding: utf-8 -*-
"""
Tests for moo/core/models/object.py — Object, Relationship, Alias, AncestorCache.

Only objects from bootstrap.initialize_dataset() are treated as pre-existing:
System Object (pk=1), container class, Wizard, Permissions, Prepositions.
All other objects, verbs, and properties are created within each test.
"""

import pytest

from .. import code, create, exceptions, lookup
from ..models import Alias, AncestorCache, Object, Player, Property, Verb
from .utils import ctx as _ctx

# ---------------------------------------------------------------------------
# Basic Object attributes
# ---------------------------------------------------------------------------


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_object_str(t_init, t_wizard):
    with _ctx(t_wizard):
        obj = create("my widget")
    assert str(obj) == f"#{obj.pk} (my widget)"


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_object_kind(t_init, t_wizard):
    with _ctx(t_wizard):
        obj = create("thing")
    assert obj.kind == "object"


# ---------------------------------------------------------------------------
# Player / wizard status
# ---------------------------------------------------------------------------


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_object_is_player_false(t_init, t_wizard):
    with _ctx(t_wizard):
        obj = create("inanimate thing")
    assert not obj.is_player()


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_object_is_player_true(t_init, t_wizard):
    with _ctx(t_wizard):
        obj = create("avatar")
    Player.objects.create(avatar=obj)
    assert obj.is_player()


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_object_is_wizard_false(t_init, t_wizard):
    with _ctx(t_wizard):
        obj = create("regular player")
    Player.objects.create(avatar=obj, wizard=False)
    assert not obj.is_wizard()


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_object_is_wizard_true(t_init, t_wizard):
    with _ctx(t_wizard):
        obj = create("wiz player")
    Player.objects.create(avatar=obj, wizard=True)
    assert obj.is_wizard()


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_object_is_connected(t_init, t_wizard):
    with _ctx(t_wizard):
        obj = create("something")
    assert obj.is_connected() is True


# ---------------------------------------------------------------------------
# Naming and aliases
# ---------------------------------------------------------------------------


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_object_is_named_by_name(t_init, t_wizard):
    with _ctx(t_wizard):
        obj = create("Widget")
    assert obj.is_named("widget")
    assert obj.is_named("WIDGET")
    assert not obj.is_named("gadget")


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_object_is_named_by_alias(t_init, t_wizard):
    with _ctx(t_wizard):
        obj = create("Widget")
    Alias.objects.create(object=obj, alias="gizmo")
    assert obj.is_named("gizmo")
    assert obj.is_named("GIZMO")


# ---------------------------------------------------------------------------
# find / contains
# ---------------------------------------------------------------------------


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_object_find_by_name(t_init, t_wizard):
    with _ctx(t_wizard):
        containers = lookup("container class")
        room = create("test room", parents=[containers])
        item = create("lamp", location=room)
    with _ctx(t_wizard):
        results = room.find("lamp")
    assert item in results


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_object_find_by_alias(t_init, t_wizard):
    with _ctx(t_wizard):
        containers = lookup("container class")
        room = create("test room", parents=[containers])
        item = create("lamp", location=room)
    Alias.objects.create(object=item, alias="light")
    with _ctx(t_wizard):
        results = room.find("light")
    assert item in results


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_object_contains(t_init, t_wizard):
    with _ctx(t_wizard):
        containers = lookup("container class")
        box = create("box", parents=[containers])
        ball = create("ball", location=box)
        other = create("other")
    assert box.contains(ball)
    assert not box.contains(other)


# ---------------------------------------------------------------------------
# Ancestry / is_a
# ---------------------------------------------------------------------------


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_object_is_a_direct_parent(t_init, t_wizard):
    with _ctx(t_wizard):
        parent = create("parent class")
        child = create("child", parents=[parent])
    assert child.is_a(parent)


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_object_is_a_grandparent(t_init, t_wizard):
    with _ctx(t_wizard):
        grandparent = create("grandparent class")
        parent = create("parent class", parents=[grandparent])
        child = create("child", parents=[parent])
    assert child.is_a(grandparent)


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_object_is_a_unrelated(t_init, t_wizard):
    with _ctx(t_wizard):
        a = create("class a")
        b = create("class b")
    assert not b.is_a(a)


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_object_get_ancestors_order(t_init, t_wizard):
    with _ctx(t_wizard):
        grandparent = create("gp class")
        parent = create("p class", parents=[grandparent])
        child = create("child obj", parents=[parent])
    with _ctx(t_wizard):
        ancestors = list(child.get_ancestors())
    depths = [a.depth for a in ancestors]
    assert depths == sorted(depths)
    assert parent in ancestors
    assert grandparent in ancestors


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_object_get_ancestors_multiple_parents(t_init, t_wizard):
    with _ctx(t_wizard):
        p1 = create("parent one")
        p2 = create("parent two")
        child = create("multi child")
        child.parents.add(p1, p2)
    with _ctx(t_wizard):
        ancestors = list(child.get_ancestors())
    assert p1 in ancestors
    assert p2 in ancestors


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_object_get_descendents(t_init, t_wizard):
    with _ctx(t_wizard):
        root = create("root class")
        child = create("child class", parents=[root])
        grandchild = create("grandchild", parents=[child])
    with _ctx(t_wizard):
        descs = list(root.get_descendents())
    assert child in descs
    assert grandchild in descs
    assert all(d.depth >= 1 for d in descs)


# ---------------------------------------------------------------------------
# Contents
# ---------------------------------------------------------------------------


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_object_get_contents(t_init, t_wizard):
    with _ctx(t_wizard):
        containers = lookup("container class")
        room = create("content room", parents=[containers])
        item = create("content item", location=room)
    with _ctx(t_wizard):
        contents = list(room.get_contents())
    assert item in contents


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_object_get_contents_nested(t_init, t_wizard):
    with _ctx(t_wizard):
        containers = lookup("container class")
        room = create("nested room", parents=[containers])
        box = create("nested box", parents=[containers], location=room)
        gem = create("nested gem", location=box)
    with _ctx(t_wizard):
        contents = list(room.get_contents())
    pks = {o.pk for o in contents}
    assert box.pk in pks
    assert gem.pk in pks
    depths = {o.pk: o.depth for o in contents}
    assert depths[box.pk] < depths[gem.pk]


# ---------------------------------------------------------------------------
# Verbs
# ---------------------------------------------------------------------------


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_object_add_verb_and_has_verb(t_init, t_wizard):
    with _ctx(t_wizard):
        obj = create("verbable")
        obj.add_verb("greet", code="return 'hello'")
    with _ctx(t_wizard):
        assert obj.has_verb("greet")


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_object_has_verb_no_recurse(t_init, t_wizard):
    with _ctx(t_wizard):
        parent = create("verb parent")
        parent.add_verb("inherited", code="return 1")
        child = create("verb child", parents=[parent])
    with _ctx(t_wizard):
        assert child.has_verb("inherited", recurse=True)
        assert not child.has_verb("inherited", recurse=False)


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_object_get_verb_returns_instance(t_init, t_wizard):
    with _ctx(t_wizard):
        obj = create("gettable")
        obj.add_verb("myverb", code="pass")
    with _ctx(t_wizard):
        v = obj.get_verb("myverb")
    assert isinstance(v, Verb)
    assert v.names.filter(name="myverb").exists()


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_object_invoke_verb_returns_result(t_init, t_wizard):
    with _ctx(t_wizard):
        obj = create("invokable")
        obj.add_verb("compute", code="return 42")
        result = obj.invoke_verb("compute")
    assert result == 42


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_object_invoke_verb_inherited(t_init, t_wizard):
    with _ctx(t_wizard):
        parent = create("inv parent")
        parent.add_verb("answer", code="return 99")
        child = create("inv child", parents=[parent])
        result = child.invoke_verb("answer")
    assert result == 99


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_object_add_verb_replace(t_init, t_wizard):
    with _ctx(t_wizard):
        obj = create("replaceable")
        obj.add_verb("action", code="return 'v1'")
        obj.add_verb("action", code="return 'v2'", replace=True)
        result = obj.invoke_verb("action")
    assert result == "v2"
    assert obj.verbs.filter(names__name="action").count() == 1


# ---------------------------------------------------------------------------
# Properties
# ---------------------------------------------------------------------------


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_object_set_property(t_init, t_wizard):
    with _ctx(t_wizard):
        obj = create("prop holder")
        obj.set_property("color", "red")
    with _ctx(t_wizard):
        assert obj.get_property("color") == "red"


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_object_get_property_direct(t_init, t_wizard):
    with _ctx(t_wizard):
        obj = create("direct prop")
        obj.set_property("score", 100)
    with _ctx(t_wizard):
        assert obj.get_property("score") == 100


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_object_get_property_inherited(t_init, t_wizard):
    with _ctx(t_wizard):
        parent = create("prop parent")
        parent.set_property("flavor", "vanilla")
        child = create("prop child", parents=[parent])
    with _ctx(t_wizard):
        assert child.get_property("flavor") == "vanilla"


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_object_get_property_no_recurse_raises(t_init, t_wizard):
    with _ctx(t_wizard):
        # Set the property AFTER parents.add so it is not copied to child
        parent = create("nr parent")
        child = create("nr child", parents=[parent])
        parent.set_property("secret", "hidden")
    with _ctx(t_wizard):
        with pytest.raises(exceptions.NoSuchPropertyError):
            child.get_property("secret", recurse=False)


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_object_get_property_original(t_init, t_wizard):
    with _ctx(t_wizard):
        obj = create("orig prop")
        obj.set_property("tag", "alpha")
    with _ctx(t_wizard):
        prop = obj.get_property("tag", original=True)
    assert isinstance(prop, Property)
    assert prop.name == "tag"


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_object_get_property_objects(t_init, t_wizard):
    with _ctx(t_wizard):
        obj = create("obj list holder")
        a = create("item a")
        b = create("item b")
        obj.set_property("items", [a, b])
    with _ctx(t_wizard):
        result = obj.get_property_objects("items")
    pks = {o.pk for o in result}
    assert a.pk in pks
    assert b.pk in pks


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_object_has_property_direct(t_init, t_wizard):
    with _ctx(t_wizard):
        obj = create("has prop")
        obj.set_property("exists", True)
    with _ctx(t_wizard):
        assert obj.has_property("exists")
        assert not obj.has_property("missing")


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_object_has_property_inherited(t_init, t_wizard):
    with _ctx(t_wizard):
        parent = create("has parent")
        parent.set_property("inherited_prop", 1)
        child = create("has child", parents=[parent])
    with _ctx(t_wizard):
        assert child.has_property("inherited_prop", recurse=True)


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_object_has_property_no_recurse(t_init, t_wizard):
    with _ctx(t_wizard):
        # Set property AFTER parents.add so it is not copied to child
        parent = create("nr has parent")
        child = create("nr has child", parents=[parent])
        parent.set_property("parent_only", 1)
    with _ctx(t_wizard):
        assert not child.has_property("parent_only", recurse=False)


# ---------------------------------------------------------------------------
# delete
# ---------------------------------------------------------------------------


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_object_delete_basic(t_init, t_wizard):
    with _ctx(t_wizard):
        obj = create("doomed object")
    pk = obj.pk
    with _ctx(t_wizard):
        obj.delete()
    assert not Object.objects.filter(pk=pk).exists()


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_object_delete_invokes_recycle_verb(t_init, t_wizard):
    output = []
    with code.ContextManager(t_wizard, output.append):
        obj = create("recyclable")
        obj.add_verb("recycle", code="print('recycled')")
    with code.ContextManager(t_wizard, output.append):
        obj.delete()
    assert "recycled" in output


# ---------------------------------------------------------------------------
# save — recursion check
# ---------------------------------------------------------------------------


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_object_save_recursion_raises(t_init, t_wizard):
    with _ctx(t_wizard):
        containers = lookup("container class")
        outer = create("outer box", parents=[containers])
        inner = create("inner box", parents=[containers], location=outer)
    with _ctx(t_wizard):
        outer = lookup("outer box")
        inner = lookup("inner box")
        outer.location = inner
        with pytest.raises(exceptions.RecursiveError):
            outer.save()


# ---------------------------------------------------------------------------
# __getattr__
# ---------------------------------------------------------------------------


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_object_getattr_verb(t_init, t_wizard):
    with _ctx(t_wizard):
        obj = create("attr obj")
        obj.add_verb("myaction", code="return 'done'")
    with _ctx(t_wizard):
        v = obj.myaction
    assert isinstance(v, Verb)


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_object_getattr_property(t_init, t_wizard):
    with _ctx(t_wizard):
        obj = create("attr prop obj")
        obj.set_property("myval", 77)
    with _ctx(t_wizard):
        assert obj.myval == 77


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_object_getattr_missing_raises(t_init, t_wizard):
    with _ctx(t_wizard):
        obj = create("bare obj")
    with _ctx(t_wizard):
        with pytest.raises(AttributeError):
            _ = obj.nonexistent_thing_xyz


# ---------------------------------------------------------------------------
# owns
# ---------------------------------------------------------------------------


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_object_owns(t_init, t_wizard):
    with _ctx(t_wizard):
        obj = create("owned thing")
    assert t_wizard.owns(obj)
    other = Object.objects.create(name="other thing")
    assert not t_wizard.owns(other)


# ---------------------------------------------------------------------------
# Relationship weight
# ---------------------------------------------------------------------------


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_relationship_weight_auto_assigned(t_init, t_wizard):
    with _ctx(t_wizard):
        p1 = create("weight parent 1")
        p2 = create("weight parent 2")
        p3 = create("weight parent 3")
        child = create("weight child")
        child.parents.add(p1)
        child.parents.add(p2)
        child.parents.add(p3)
    from ..models.object import Relationship

    weights = list(Relationship.objects.filter(child=child).order_by("weight").values_list("weight", flat=True))
    assert weights == sorted(weights)
    assert len(set(weights)) == len(weights)


# ---------------------------------------------------------------------------
# Alias permission check
# ---------------------------------------------------------------------------


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_alias_requires_write_permission(t_init, t_wizard):
    with _ctx(t_wizard):
        obj = create("alias target")
    user = Object.objects.create(name="player")
    with code.ContextManager(user, lambda m: None):
        with pytest.raises(PermissionError):
            Alias.objects.create(object=obj, alias="forbidden")


# ---------------------------------------------------------------------------
# AncestorCache maintenance
# ---------------------------------------------------------------------------


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_ancestor_cache_rebuilt_on_parents_add(t_init, t_wizard):
    with _ctx(t_wizard):
        parent = create("ac parent")
        child = create("ac child")
        child.parents.add(parent)
    assert AncestorCache.objects.filter(descendant=child, ancestor=parent).exists()


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_ancestor_cache_rebuilt_on_parents_remove(t_init, t_wizard):
    with _ctx(t_wizard):
        parent = create("acr parent")
        child = create("acr child")
        child.parents.add(parent)
    assert AncestorCache.objects.filter(descendant=child, ancestor=parent).exists()
    with _ctx(t_wizard):
        child.parents.remove(parent)
    assert not AncestorCache.objects.filter(descendant=child, ancestor=parent).exists()
