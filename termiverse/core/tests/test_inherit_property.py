from termiverse.tests import *
from ..models import Object, Property

import pytest

@pytest.mark.django_db
def test_parent_property(t_init: Object):
    room_class = Object.objects.get(name="room class")
    parent_description = room_class.properties.get(name="description")
    room = Object.objects.create(name="new room")
    room.parents.add(room_class)
    description = room.get_property(name="description")
    assert description == parent_description.value

@pytest.mark.django_db
def test_inherited_property_owner(t_init: Object):
    player = Object.objects.get(name="Player")
    room_class = Object.objects.get(name="room class")
    room = Object.objects.create(name="new room", owner=player)
    room.parents.add(room_class)
    description = room.get_property(name="description", recurse=False, original=True)
    assert description.origin == room

@pytest.mark.django_db
def test_inherited_property_origin(t_init: Object):
    player = Object.objects.get(name="Player")
    room_class = Object.objects.get(name="room class")
    room = Object.objects.create(name="new room", owner=player)
    room.parents.add(room_class)
    description = room.get_property(name="description", recurse=False, original=True)
    assert description.owner == player

@pytest.mark.django_db
def test_post_creation_inherited_property(t_init: Object, t_wizard: Object):
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
