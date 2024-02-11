from termiverse.tests import *
from .. import code
from ..models import Object
from ..models.property import AccessibleProperty

import pytest

@pytest.mark.django_db
def test_parent_property(t_init):
    room_class = Object.objects.get(name="room class")
    parent_description = room_class.properties.get(name="description")
    room = Object.objects.create(name="new room")
    room.parents.add(room_class)

    with pytest.raises(AccessibleProperty.DoesNotExist):
        description = room.get_property(name="description", inherited=False)

    description = room.get_property(name="description")
    assert description == parent_description.value
