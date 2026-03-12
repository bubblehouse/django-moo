import datetime

import pytest

from moo.core import code, lookup, parse
from moo.core.models import Object

UTC = datetime.timezone.utc


def set_last_connected(obj: Object, delta: datetime.timedelta):
    """Set obj's last_connected_time to now minus delta."""
    obj.set_property("last_connected_time", datetime.datetime.now(UTC) - delta)


# --- @lastlog with a named player ---


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_lastlog_named_player_shows_time(t_init: Object, t_wizard: Object):
    """@lastlog <player> shows the player's last connection time."""
    printed = []
    with code.ContextManager(t_wizard, printed.append) as ctx:
        set_last_connected(t_wizard, datetime.timedelta(hours=1))
        parse.interpret(ctx, "@lastlog Wizard")
    assert any("Wizard" in line and ":" in line for line in printed)
    # Timestamp should be formatted as YYYY-MM-DD HH:MM:SS
    assert any(any(c.isdigit() for c in line) for line in printed)


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_lastlog_named_player_never_connected(t_init: Object, t_wizard: Object):
    """@lastlog <player> shows 'has never connected.' when no property exists."""
    printed = []
    with code.ContextManager(t_wizard, printed.append) as ctx:
        # Player NPC has no last_connected_time by default
        parse.interpret(ctx, "@lastlog Player")
    assert any("has never connected." in line for line in printed)


# --- @lastlog all players (grouped output) ---


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_lastlog_groups_today(t_init: Object, t_wizard: Object):
    """@lastlog without args groups a recently connected player under 'last day'."""
    printed = []
    with code.ContextManager(t_wizard, printed.append) as ctx:
        set_last_connected(t_wizard, datetime.timedelta(hours=1))
        parse.interpret(ctx, "@lastlog")
    assert any("last day" in line for line in printed)
    assert any("Wizard" in line for line in printed)


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_lastlog_groups_this_week(t_init: Object, t_wizard: Object):
    """@lastlog without args groups a player connected 3 days ago under 'last week'."""
    printed = []
    with code.ContextManager(t_wizard, printed.append) as ctx:
        set_last_connected(t_wizard, datetime.timedelta(days=3))
        parse.interpret(ctx, "@lastlog")
    assert any("last week" in line for line in printed)
    assert any("Wizard" in line for line in printed)


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_lastlog_groups_this_month(t_init: Object, t_wizard: Object):
    """@lastlog without args groups a player connected 15 days ago under 'last month'."""
    printed = []
    with code.ContextManager(t_wizard, printed.append) as ctx:
        set_last_connected(t_wizard, datetime.timedelta(days=15))
        parse.interpret(ctx, "@lastlog")
    assert any("last month" in line for line in printed)
    assert any("Wizard" in line for line in printed)


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_lastlog_groups_older(t_init: Object, t_wizard: Object):
    """@lastlog without args groups a player connected 60 days ago under 'more than a month ago'."""
    printed = []
    with code.ContextManager(t_wizard, printed.append) as ctx:
        set_last_connected(t_wizard, datetime.timedelta(days=60))
        parse.interpret(ctx, "@lastlog")
    assert any("month ago" in line for line in printed)
    assert any("Wizard" in line for line in printed)


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_lastlog_groups_never_connected(t_init: Object, t_wizard: Object):
    """@lastlog shows players with no last_connected_time as 'never connected'."""
    printed = []
    with code.ContextManager(t_wizard, printed.append) as ctx:
        # Player NPC has no last_connected_time — should appear in the older/never group
        parse.interpret(ctx, "@lastlog")
    assert any("never connected" in line for line in printed)
    assert any("Player" in line for line in printed)
