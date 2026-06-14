"""Tests for the per-task loop/tick budget (spec 200, item N)."""

import pytest

from .. import code
from ..exceptions import TickLimitError
from ..models import Object


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_tight_loop_aborts(settings, t_init: Object, t_wizard: Object):
    settings.MOO_TICK_BUDGET = 1000
    with code.ContextManager(t_wizard, lambda _: None):
        t_wizard.add_verb("spin", code="for i in range(100000):\n    pass\nreturn 'done'")
        with pytest.raises(TickLimitError):
            t_wizard.spin()


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_normal_loop_runs_under_budget(settings, t_init: Object, t_wizard: Object):
    settings.MOO_TICK_BUDGET = 100000
    with code.ContextManager(t_wizard, lambda _: None):
        t_wizard.add_verb("countup", code="total = 0\nfor i in range(50):\n    total = total + i\nreturn total")
        assert t_wizard.countup() == sum(range(50))


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_budget_zero_disables(settings, t_init: Object, t_wizard: Object):
    settings.MOO_TICK_BUDGET = 0
    with code.ContextManager(t_wizard, lambda _: None):
        t_wizard.add_verb("spin2", code="for i in range(20000):\n    pass\nreturn 'ok'")
        assert t_wizard.spin2() == "ok"


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_budget_resets_between_tasks(settings, t_init: Object, t_wizard: Object):
    settings.MOO_TICK_BUDGET = 1000
    # Each ContextManager session starts a fresh counter, so a per-task budget
    # of 1000 admits a 500-iteration loop run twice in separate sessions.
    with code.ContextManager(t_wizard, lambda _: None):
        t_wizard.add_verb("half", code="for i in range(500):\n    pass\nreturn 'a'")
        assert t_wizard.half() == "a"
    with code.ContextManager(t_wizard, lambda _: None):
        assert t_wizard.half() == "a"
