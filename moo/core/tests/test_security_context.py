# -*- coding: utf-8 -*-
# pylint: disable=protected-access
"""
Security tests: ContextManager state and invoke() guards.

Covers: caller_stack copy, context read-only descriptor, set_task_perms wizard
check, invoke() periodic/cron/execute permission checks (passes 2, 3, 7).
"""

import pytest

from moo.core.models.object import Object

from .. import code
from .utils import ctx, mock_caller, raises_in_verb

# ---------------------------------------------------------------------------
# set_task_perms must require wizard (regression guard)
# ---------------------------------------------------------------------------


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_set_task_perms_requires_wizard(t_init: Object, t_wizard: Object):
    """

    set_task_perms() raises UserError when called by a non-wizard.
    This is already enforced; test guards against regression.
    """
    from moo.sdk import create, set_task_perms
    from moo.core.exceptions import UserError

    plain = create("plain_user")

    with ctx(plain):
        with pytest.raises(UserError):
            with set_task_perms(t_wizard):
                pass


# ---------------------------------------------------------------------------
# context.caller_stack must return a copy, not the live list
# ---------------------------------------------------------------------------


def test_caller_stack_returns_copy():
    """

    ContextManager.get('caller_stack') must return a copy of the stack list.
    Mutating the returned list must not affect the live _active_caller_stack.
    """
    caller = mock_caller()
    with ctx(caller):
        stack_copy = code.ContextManager.get("caller_stack")
        stack_copy.append({"previous_caller": "FAKE"})
        live = code.ContextManager.get("caller_stack")
        assert "FAKE" not in [f.get("previous_caller") for f in live]


# ---------------------------------------------------------------------------
# invoke() must require wizard for persistent (periodic/cron) tasks
# ---------------------------------------------------------------------------


def test_invoke_periodic_requires_wizard():
    """invoke(..., periodic=True) raises UserError when called by a non-wizard."""
    from unittest.mock import MagicMock
    from moo.sdk import invoke
    from moo.core.exceptions import UserError

    non_wizard = MagicMock()
    non_wizard.is_wizard.return_value = False
    verb = MagicMock()

    with ctx(non_wizard):
        with pytest.raises(UserError):
            invoke(verb=verb, delay=60, periodic=True)


def test_invoke_cron_requires_wizard():
    """invoke(..., cron=...) raises UserError when called by a non-wizard."""
    from unittest.mock import MagicMock
    from moo.sdk import invoke
    from moo.core.exceptions import UserError

    non_wizard = MagicMock()
    non_wizard.is_wizard.return_value = False
    verb = MagicMock()

    with ctx(non_wizard):
        with pytest.raises(UserError):
            invoke(verb=verb, cron="* * * * *")


def test_invoke_oneshot_allowed_for_nonwizard():
    """invoke() without periodic/cron must not raise for non-wizards."""
    from unittest.mock import MagicMock, patch
    from moo.sdk import invoke

    non_wizard = MagicMock()
    non_wizard.is_wizard.return_value = False
    non_wizard.pk = 42
    verb = MagicMock()
    verb._invoked_object.pk = 1
    verb._invoked_name = "test"

    with ctx(non_wizard):
        with patch("moo.core.tasks.invoke_verb.apply_async"):
            invoke(verb=verb)


# ---------------------------------------------------------------------------
# invoke() must check execute permission on the verb
# ---------------------------------------------------------------------------


def test_invoke_checks_execute_permission():
    """

    invoke() must call can_caller("execute", verb) before dispatching.
    Previously the check was missing; a caller with only read access could
    enqueue any verb they could look up.
    """
    from unittest.mock import MagicMock, patch
    from moo.sdk import invoke

    caller = MagicMock()
    caller.is_wizard.return_value = False
    caller.pk = 42

    verb = MagicMock()
    verb._invoked_name = "test"
    verb._invoked_object.can_caller.side_effect = PermissionError("no execute")

    with ctx(caller):
        with pytest.raises(PermissionError):
            with patch("moo.core.tasks.invoke_verb.apply_async"):
                invoke(verb=verb)


# ---------------------------------------------------------------------------
# context attributes must be read-only (descriptor shadowing guard)
# ---------------------------------------------------------------------------


def test_context_caller_is_read_only_directly():
    """

    Directly assigning context.caller must raise AttributeError.
    The _Context.descriptor is a data descriptor; instance attributes cannot shadow it.
    """
    from moo.sdk import context

    with pytest.raises(AttributeError):
        context.caller = mock_caller(is_wizard=True)


def test_context_caller_shadowing_blocked_in_verb():
    """

    Verb code must not be able to shadow context.caller via _write_ assignment.
    Previously, setattr(context, 'caller', wizard_obj) silently shadowed the
    non-data descriptor, making context.caller.is_wizard() return True for all
    subsequent code in the same worker process.
    """
    raises_in_verb("from moo.sdk import context\ncontext.caller = None", AttributeError)


# ---------------------------------------------------------------------------
# invoke() — PeriodicTask return value and kwargs security
# ---------------------------------------------------------------------------


def test_invoke_periodic_returns_task_with_registered_task_name():
    """

    invoke(verb, delay=60, periodic=True) is wizard-gated and returns a live
    PeriodicTask model instance.  PeriodicTask has no MOO ACL guard on .save(),
    so a wizard who receives the return value can modify periodic_task.task.

    The escalation risk is limited by Celery's task registry: only tasks
    decorated with @app.task are callable by beat.  Setting task to an
    unregistered name causes a celery.exceptions.NotRegistered error at
    execution time, not arbitrary code execution.

    The wizard guard at invoke() entry prevents non-wizards from creating
    PeriodicTasks at all; modifying one's own already-scheduled task is
    accepted wizard-level access.
    """
    from unittest.mock import MagicMock, patch
    from moo.sdk import invoke

    wizard = mock_caller(is_wizard=True)
    wizard.pk = 1
    verb = MagicMock()
    verb._invoked_object.pk = 1
    verb._invoked_name = "test_verb"

    with ctx(wizard):
        with (
            patch("django_celery_beat.models.IntervalSchedule.objects.get_or_create") as mock_sched,
            patch("django_celery_beat.models.PeriodicTask.objects.create") as mock_create,
        ):
            mock_sched.return_value = (MagicMock(), True)
            mock_task = MagicMock()
            mock_task.task = "moo.core.tasks.invoke_verb"
            mock_create.return_value = mock_task

            task = invoke(verb=verb, delay=60, periodic=True)

    assert task is not None
    assert task.task == "moo.core.tasks.invoke_verb"


def test_invoke_kwargs_caller_id_cannot_be_forged():
    """

    invoke() unconditionally overwrites caller_id, player_id, this_id, and
    verb_name with values derived from the authenticated context after merging
    any verb-supplied kwargs.  Even if verb code passes a forged caller_id
    using the dict.update() underscore-key bypass documented elsewhere, invoke()
    overwrites it with context.caller.pk before dispatching the task.
    """
    from unittest.mock import MagicMock, patch
    from moo.sdk import invoke

    wizard = mock_caller(is_wizard=True)
    wizard.pk = 99
    verb = MagicMock()
    verb._invoked_object.pk = 1
    verb._invoked_name = "test"

    captured_kwargs = {}

    def fake_apply_async(args, kwargs, **kw):
        captured_kwargs.update(kwargs)

    with ctx(wizard):
        with patch("moo.core.tasks.invoke_verb.apply_async", side_effect=fake_apply_async):
            invoke(verb=verb)

    assert captured_kwargs["caller_id"] == 99


# ---------------------------------------------------------------------------
# context.writer / context.parser / context.task_id surface
# ---------------------------------------------------------------------------


def test_context_writer_equivalent_to_print():
    """

    context.writer is the same callable that the sandbox's print() uses
    internally (_print_._call_print calls writer(s)).  Non-wizard verb code
    calling context.writer('msg') is equivalent to print('msg') — both write
    only to the current player's own console.

    The wizard check on write(obj, msg) guards writing to ARBITRARY players
    (by specifying obj).  context.writer always targets the current session's
    player and is not a bypass of that check.
    """
    caller = mock_caller(is_wizard=False)
    printed = []
    with ctx(caller, printed.append):
        w = code.ContextManager.get("writer")
        g = code.get_default_globals()
        g.update(code.get_restricted_environment("__main__", w))
        code.r_exec(
            "from moo.sdk import context\ncontext.writer('test msg')",
            {},
            g,
        )
    assert printed == ["test msg"]


def test_context_task_id_is_string_or_none():
    """

    context.task_id returns the Celery task ID string (or None outside a task).
    Celery's inspect/revoke APIs require broker access which verb code cannot
    obtain — knowing the task ID string alone does not allow a verb to cancel
    or inspect tasks from inside the sandbox.
    """
    caller = mock_caller(is_wizard=False)
    with ctx(caller):
        task_id = code.ContextManager.get("task_id")
    assert task_id is None or isinstance(task_id, str)


def test_context_parser_is_none_outside_command_dispatch():
    """

    context.parser returns the Parser instance for the current command.
    Its public attributes (command, words, dobj_str, dobj, prepositions) expose
    the same information already available to verb code via the sdk parse helpers.
    Parser does not expose Django internals or model managers.

    Outside command dispatch (e.g. unit tests where set_parser() is not called),
    context.parser is None.
    """
    caller = mock_caller(is_wizard=False)
    with ctx(caller):
        parser = code.ContextManager.get("parser")
    assert parser is None


@pytest.mark.skip(reason="info disclosure only — not scheduled for remediation")
def test_caller_stack_previous_caller_reference_accessible():
    """

    Known gap (information disclosure): context.caller_stack returns a copy of
    the live stack (preventing mutation), but each frame dict contains
    'previous_caller' — a live Object reference. Verb code can read this via
    frame.get('previous_caller') since 'previous_caller' has no underscore
    prefix and dict.get() bypasses _getitem_.

    In a scenario where a wizard verb uses set_task_perms(plain) to run as
    plain, the inner verb sees the wizard Object on the caller stack and can
    call methods like is_wizard() on it. This is information disclosure; it
    does not allow privilege escalation because context.caller is a read-only
    data descriptor that cannot be overwritten.
    """
    wizard_caller = mock_caller(is_wizard=True)
    non_wizard = mock_caller(is_wizard=False)

    with ctx(wizard_caller):
        code.ContextManager.override_caller(non_wizard)
        stack = code.ContextManager.get("caller_stack")
        assert len(stack) == 1
        frame = stack[0]
        prev = frame.get("previous_caller")
        assert prev is wizard_caller, "Known gap: previous_caller is readable from caller_stack copy"
        code.ContextManager.pop_caller()
