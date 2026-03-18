"""
Shared test helpers for default_verbs tests.
"""

import warnings

from moo.sdk import context, create, lookup
from moo.core.models import Object


def save_quietly(obj):
    """Save obj suppressing RuntimeWarning from disconnected players."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        obj.save()


def setup_room(t_wizard: Object, name: str = "Test Room", description: str = "A plain test room.") -> Object:
    """Create a Generic Room, describe it, and move the wizard into it."""
    rooms = lookup("Generic Room")
    room = create(name, parents=[rooms])
    room.describe(description)
    t_wizard.location = room
    save_quietly(t_wizard)
    context.caller.refresh_from_db()
    return room


def setup_root_item(location: Object, name: str = "red ball") -> Object:
    """Create a plain root_class child object in the given location."""
    system = lookup(1)
    return create(name, parents=[system.root_class], location=location)
