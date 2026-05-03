import pytest

from moo.core import code
from moo.sdk import lookup
from moo.core.models import Object


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_match_player_by_prefix(t_init: Object, t_wizard: Object):
    """match_player returns players whose name starts with the query."""
    with code.ContextManager(t_wizard, lambda _: None):
        system = lookup(1)
        result = system.match_utils.match_player("Wiz")
    assert any(p.name == "Wizard" for p in result)


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_match_player_no_match(t_init: Object, t_wizard: Object):
    """match_player returns an empty list when no player matches."""
    with code.ContextManager(t_wizard, lambda _: None):
        system = lookup(1)
        result = system.match_utils.match_player("xyz_nobody")
    assert result == []


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_match_player_case_insensitive(t_init: Object, t_wizard: Object):
    """match_player is case-insensitive."""
    with code.ContextManager(t_wizard, lambda _: None):
        system = lookup(1)
        result = system.match_utils.match_player("wiz")
    assert any(p.name == "Wizard" for p in result)


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_match_player_multiple_results(t_init: Object, t_wizard: Object):
    """match_player returns all matching players."""
    with code.ContextManager(t_wizard, lambda _: None):
        system = lookup(1)
        # Both "Wizard" and "Player" exist in the default dataset
        result = system.match_utils.match_player("")
    # Empty prefix matches all players
    assert len(result) >= 2
