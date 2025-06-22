import json

import pytest

from ..models import Object, Property


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_child_inherits_parent_property(t_init: Object):
    room_class = Object.objects.get(name="room class")
    parent_description = room_class.properties.get(name="description")
    room = Object.objects.create(name="new room")
    room.parents.add(room_class)
    description = room.get_property(name="description")
    assert description == json.loads(parent_description.value)


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
    p.set_property("test_post_creation", "There's not much to see here.")
    o.parents.add(p)

    with pytest.raises(Property.DoesNotExist):
        description = o.get_property(name="test_post_creation", recurse=False, original=True)

    description = p.get_property(name="test_post_creation", recurse=False, original=True)
    description.inherited = True
    description.save()
    description = o.get_property(name="test_post_creation", recurse=False, original=True)
    assert description.owner == player
