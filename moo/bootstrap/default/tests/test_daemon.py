# pylint: disable=no-value-for-parameter,unused-variable
"""
Tests for the $daemon class — scheduled-event objects driven by
django-celery-beat PeriodicTasks.

Covers:
  - Generic Daemon class exists with expected default properties
  - enable creates a PeriodicTask wired to invoke_verb(on_tick)
  - disable deletes the PeriodicTask and clears the pointer
  - enable is idempotent on an already-enabled daemon
  - enable self-heals an orphan periodic_task_id pointer
  - disable is idempotent on a never-enabled daemon
  - trigger fires on_tick synchronously
  - Subclass on_tick override runs when triggered
  - Recycling a daemon (or a $daemon subclass) deletes its PT
  - $room.recycle activates contents-rescue after the recurse=True fix
  - Non-wizard cannot enable
  - @daemon list/enable/disable/trigger/kill wizard subcommands
"""

import pytest

from moo.core import code, exceptions, parse
from moo.core.models import Object
from moo.sdk import create, lookup
from .utils import setup_room


def _make_daemon(owner, name="ticker"):
    daemon_cls = lookup("Generic Daemon")
    return create(name, parents=[daemon_cls], location=owner, owner=owner)


def _periodic_task_count(pk):
    from django_celery_beat.models import PeriodicTask

    return PeriodicTask.objects.filter(pk=pk).count()


def _get_periodic_task(pk):
    from django_celery_beat.models import PeriodicTask

    return PeriodicTask.objects.get(pk=pk)


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_daemon_class_exists(t_init: Object, t_wizard: Object):
    """$daemon is a named class, child of $thing."""
    daemon_cls = lookup("Generic Daemon")
    assert daemon_cls is not None
    thing = lookup("Generic Thing")
    assert thing in daemon_cls.parents.all()


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_daemon_default_props(t_init: Object, t_wizard: Object):
    """Fresh daemon has interval=60, periodic_task_id=None, target=None, tick_count=0."""
    with code.ContextManager(t_wizard, lambda s: None):
        d = _make_daemon(t_wizard)
        assert d.get_property("interval") == 60
        assert d.get_property("periodic_task_id") is None
        assert d.get_property("target") is None
        assert d.get_property("tick_count") == 0
        assert d.get_property("last_tick_at") is None


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_enable_creates_periodic_task(t_init: Object, t_wizard: Object):
    """daemon.enable() creates a PT bound to invoke_verb(on_tick)."""
    with code.ContextManager(t_wizard, lambda s: None):
        d = _make_daemon(t_wizard)
        d.set_property("interval", 30)
        d.enable()
        pt_id = d.get_property("periodic_task_id")
        assert pt_id is not None
        pt = _get_periodic_task(pt_id)
        assert pt.task == "moo.core.tasks.invoke_verb"
        assert pt.interval is not None
        assert pt.interval.every == 30
        assert pt.interval.period == "seconds"
        import json

        kwargs = json.loads(pt.kwargs)
        # enable() schedules the tick wrapper, not on_tick directly
        assert kwargs["verb_name"] == "tick"
        assert kwargs["this_id"] == d.pk


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_disable_deletes_periodic_task(t_init: Object, t_wizard: Object):
    """After enable+disable, the PT row is gone and the pointer is cleared."""
    with code.ContextManager(t_wizard, lambda s: None):
        d = _make_daemon(t_wizard)
        d.enable()
        pt_id = d.get_property("periodic_task_id")
        assert _periodic_task_count(pt_id) == 1
        d.disable()
        assert _periodic_task_count(pt_id) == 0
        assert d.get_property("periodic_task_id") is None


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_enable_idempotent_when_already_enabled(t_init: Object, t_wizard: Object):
    """Calling enable twice doesn't create a second PT."""
    with code.ContextManager(t_wizard, lambda s: None):
        d = _make_daemon(t_wizard)
        d.enable()
        first_pt_id = d.get_property("periodic_task_id")
        d.enable()
        second_pt_id = d.get_property("periodic_task_id")
        assert first_pt_id == second_pt_id
        assert _periodic_task_count(first_pt_id) == 1


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_enable_self_heals_orphan_pointer(t_init: Object, t_wizard: Object):
    """If the PT is deleted out-of-band, enable creates a fresh one."""
    from django_celery_beat.models import PeriodicTask

    with code.ContextManager(t_wizard, lambda s: None):
        d = _make_daemon(t_wizard)
        d.enable()
        first_pt_id = d.get_property("periodic_task_id")
        PeriodicTask.objects.filter(pk=first_pt_id).delete()
        d.enable()
        new_pt_id = d.get_property("periodic_task_id")
        assert new_pt_id is not None
        assert new_pt_id != first_pt_id
        assert _periodic_task_count(new_pt_id) == 1


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_disable_idempotent_when_never_enabled(t_init: Object, t_wizard: Object):
    """Calling disable on a never-enabled daemon is a no-op."""
    with code.ContextManager(t_wizard, lambda s: None):
        d = _make_daemon(t_wizard)
        d.disable()
        assert d.get_property("periodic_task_id") is None


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_trigger_calls_on_tick(t_init: Object, t_wizard: Object):
    """trigger() runs the tick wrapper: increments tick_count, sets last_tick_at,
    and calls on_tick. The base on_tick stub prints a debug line."""
    printed = []
    with code.ContextManager(t_wizard, printed.append):
        d = _make_daemon(t_wizard)
        d.trigger()
        d.refresh_from_db()
        assert d.get_property("tick_count") == 1
        assert d.get_property("last_tick_at") is not None
    assert any("tick" in line.lower() for line in printed)


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_subclass_custom_on_tick(t_init: Object, t_wizard: Object):
    """A subclass with its own on_tick runs that override on trigger."""
    daemon_cls = lookup("Generic Daemon")
    with code.ContextManager(t_wizard, lambda s: None):
        # Subclass that bumps a counter on each tick
        counter_cls = create("Counter Daemon", parents=[daemon_cls], owner=t_wizard)
        counter_cls.set_property("count", 0, inherit_owner=True)
        counter_cls.add_verb(
            "on_tick",
            code="this.set_property('count', this.get_property('count') + 1)",
        )
        instance = create("counter1", parents=[counter_cls], location=t_wizard, owner=t_wizard)
        instance.trigger()
        instance.trigger()
        assert instance.get_property("count") == 2


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_recycle_disables_daemon(t_init: Object, t_wizard: Object):
    """Deleting an enabled daemon also deletes its PT (via recycle hook)."""
    with code.ContextManager(t_wizard, lambda s: None):
        d = _make_daemon(t_wizard)
        d.enable()
        pt_id = d.get_property("periodic_task_id")
        assert _periodic_task_count(pt_id) == 1
        d.delete()
        assert _periodic_task_count(pt_id) == 0


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_recycle_subclass_inherits_recycle(t_init: Object, t_wizard: Object):
    """A $daemon subclass with no own 'recycle' verb still cleans up its PT.

    Locks in the recurse=True fix at object.py:919.
    """
    daemon_cls = lookup("Generic Daemon")
    with code.ContextManager(t_wizard, lambda s: None):
        sub_cls = create("Beep Daemon", parents=[daemon_cls], owner=t_wizard)
        instance = create("beep1", parents=[sub_cls], location=t_wizard, owner=t_wizard)
        instance.enable()
        pt_id = instance.get_property("periodic_task_id")
        assert _periodic_task_count(pt_id) == 1
        instance.delete()
        assert _periodic_task_count(pt_id) == 0


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_room_recycle_now_fires(t_init: Object, t_wizard: Object):
    """$room.recycle activates after the recurse=True fix.

    Recycling a room now moves its non-player contents to their owners.
    """
    from .utils import save_quietly

    rooms_cls = lookup("Generic Room")
    thing_cls = lookup("Generic Thing")
    with code.ContextManager(t_wizard, lambda s: None):
        # Two rooms: doomed (to recycle) and elsewhere (where wizard waits).
        doomed = create("Doomed Room", parents=[rooms_cls])
        elsewhere = create("Elsewhere Room", parents=[rooms_cls])
        widget = create("widget", parents=[thing_cls], location=doomed, owner=t_wizard)
        t_wizard.location = elsewhere
        save_quietly(t_wizard)
        widget.refresh_from_db()
        assert widget.location == doomed
        doomed.delete()
        widget.refresh_from_db()
        assert widget.location == t_wizard


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_nonwizard_cannot_enable(t_init: Object, t_wizard: Object):
    """A non-wizard caller is blocked by enable's permission check."""
    with code.ContextManager(t_wizard, lambda s: None):
        d = _make_daemon(t_wizard)
        # Create a non-wizard player owned by wizard
        player_cls = lookup("Generic Player")
        peon = create("peon", parents=[player_cls], owner=t_wizard)
    # Re-enter context as the peon — verb's is_wizard() check should refuse.
    printed = []
    with code.ContextManager(peon, printed.append):
        d.enable()
    assert any("permission denied" in line.lower() for line in printed)
    assert d.get_property("periodic_task_id") is None


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_at_daemon_list(t_init: Object, t_wizard: Object):
    """@daemon list shows enabled daemons with their PT stats."""
    printed = []
    with code.ContextManager(t_wizard, printed.append) as ctx:
        d = _make_daemon(t_wizard, name="lantern")
        d.enable()
        printed.clear()
        parse.interpret(ctx, "@daemon list")
    output = "\n".join(printed)
    assert "lantern" in output
    assert str(d.pk) in output


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_at_daemon_enable_disable(t_init: Object, t_wizard: Object):
    """@daemon enable foo and @daemon disable foo cycle the PT.

    ``enable``/``disable`` are programmatic-only verbs (no dspec); the only
    user-facing path is the wizard ``@daemon`` subcommand.
    """
    with code.ContextManager(t_wizard, lambda s: None) as ctx:
        d = _make_daemon(t_wizard, name="ticker")
        parse.interpret(ctx, "@daemon enable ticker")
        d.refresh_from_db()
        pt_id = d.get_property("periodic_task_id")
        assert pt_id is not None
        assert _periodic_task_count(pt_id) == 1
        parse.interpret(ctx, "@daemon disable ticker")
        d.refresh_from_db()
        assert d.get_property("periodic_task_id") is None
        assert _periodic_task_count(pt_id) == 0


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_at_daemon_kill(t_init: Object, t_wizard: Object):
    """@daemon kill foo deletes the Object AND its PT."""
    with code.ContextManager(t_wizard, lambda s: None) as ctx:
        d = _make_daemon(t_wizard, name="doomed")
        d.enable()
        pt_id = d.get_property("periodic_task_id")
        parse.interpret(ctx, "@daemon kill doomed")
        with pytest.raises(exceptions.NoSuchObjectError):
            lookup("doomed")
        assert _periodic_task_count(pt_id) == 0


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_at_daemon_trigger(t_init: Object, t_wizard: Object):
    """@daemon trigger foo fires on_tick once."""
    daemon_cls = lookup("Generic Daemon")
    printed = []
    with code.ContextManager(t_wizard, printed.append) as ctx:
        counter_cls = create("Bumper Daemon", parents=[daemon_cls], owner=t_wizard)
        counter_cls.set_property("count", 0, inherit_owner=True)
        counter_cls.add_verb(
            "on_tick",
            code="this.set_property('count', this.get_property('count') + 1)",
        )
        instance = create("bumper", parents=[counter_cls], location=t_wizard, owner=t_wizard)
        printed.clear()
        parse.interpret(ctx, "@daemon trigger bumper")
        instance.refresh_from_db()
        assert instance.get_property("count") == 1


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_at_daemon_nonwizard_denied(t_init: Object, t_wizard: Object):
    """@daemon is on $wizard — parser won't even resolve it for non-wizards."""
    with code.ContextManager(t_wizard, lambda s: None):
        player_cls = lookup("Generic Player")
        peon = create("peon2", parents=[player_cls], owner=t_wizard)
    printed = []
    with code.ContextManager(peon, printed.append) as ctx:
        try:
            parse.interpret(ctx, "@daemon list")
        except (exceptions.NoSuchVerbError, exceptions.UserError, PermissionError):
            return
    # If parse returned, output should not contain real daemon listing
    assert not any("Interval" in line for line in printed)
