import pytest

from moo.core import code
from moo.core.models import Object
from moo.sdk import create, lookup


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_deleting_a_room_sends_players_home(t_init: Object, t_wizard: Object):
    """`$room:recycle` moves a player inside to their `home` property, not to the `home` verb."""
    with code.ContextManager(t_wizard, lambda _: None):
        lab = lookup("The Laboratory")
        doomed = create("Doomed Room", parents=[lookup(1).room], location=None)
        widget = create("widget", parents=[lookup(1).thing], location=doomed)
        p = lookup("Player")
        p.set_property("home", lab)
        p.location = doomed
        p.save()
        doomed.delete()
    p.refresh_from_db()
    widget.refresh_from_db()
    assert p.location == lab
    assert widget.location == t_wizard


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_deleting_a_room_without_a_home_uses_player_start(t_init: Object, t_wizard: Object):
    """A player with no `home` goes to `$player_start`."""
    with code.ContextManager(t_wizard, lambda _: None):
        doomed = create("Doomed Room", parents=[lookup(1).room], location=None)
        p = lookup("Player")
        p.set_property("home", None)
        p.location = doomed
        p.save()
        doomed.delete()
        start = lookup(1).get_property("player_start")
    p.refresh_from_db()
    assert p.location == start
