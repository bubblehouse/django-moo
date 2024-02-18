from termiverse.tests import *
from ..models import Object

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
