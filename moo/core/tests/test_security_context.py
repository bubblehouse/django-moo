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
# context.caller_stack items expose previous caller references (known info disclosure)
# ---------------------------------------------------------------------------

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
        assert prev is wizard_caller, (
            "Known gap: previous_caller is readable from caller_stack copy"
        )
        code.ContextManager.pop_caller()
