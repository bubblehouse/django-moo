# -*- coding: utf-8 -*-
"""
Task execution and scheduling functions.
"""

import warnings
from contextlib import contextmanager as _contextmanager

from ..core.code import ContextManager as _ContextManager
from ..core.exceptions import UserError
from .context import context


def invoke(*args, verb=None, callback=None, delay: int = 0, periodic: bool = False, cron: str | None = None, **kwargs):
    """
    Asynchronously execute a Verb, optionally returning the result to another Verb.
    This is often a better alternative than using `__call__`-syntax to invoke
    a verb directly, since Verbs invoked this way will each have their own timeout.

    :param verb: the Verb to execute
    :type verb: Verb
    :param callback: an optional callback Verb to receive the result
    :type callback: Verb
    :param delay: seconds to wait before executing, cannot be used with `cron`
    :param periodic: should this task continue to repeat? cannot be used with `cron`
    :param cron: a crontab expression to schedule Verb execution
    :param args: positional arguments for the Verb, if any
    :param kwargs: keyword arguments for the Verb, if any
    :returns: a :class:`.PeriodicTask` instance or `None` if the task is a one-shot
    :rtype: Optional[:class:`.PeriodicTask`]
    """
    if (periodic or cron) and context.caller and not context.caller.is_wizard():
        raise UserError("Only verbs owned by wizards can create persistent scheduled tasks.")
    if verb is not None and context.caller:
        exec_obj = (
            verb._invoked_object  # pylint: disable=protected-access
            if verb._invoked_object is not None  # pylint: disable=protected-access
            else verb.origin
        )
        exec_obj.can_caller("execute", verb)

    from django_celery_beat.models import CrontabSchedule, IntervalSchedule, PeriodicTask
    from moo.core import tasks

    kwargs.update(
        dict(
            caller_id=context.caller.pk if context.caller else None,
            player_id=context.player.pk if context.player else None,
            this_id=verb._invoked_object.pk,  # pylint: disable=protected-access
            verb_name=verb._invoked_name,  # pylint: disable=protected-access
            callback_this_id=callback._invoked_object.pk if callback else None,  # pylint: disable=protected-access
            callback_verb_name=callback._invoked_name if callback else None,  # pylint: disable=protected-access
        )
    )
    if delay and periodic:
        schedule, _ = IntervalSchedule.objects.get_or_create(
            every=delay,
            period=IntervalSchedule.SECONDS,
        )
        return PeriodicTask.objects.create(
            interval=schedule,
            description=f"{context.caller.pk}:{verb}",
            task="moo.core.tasks.invoke_verb",
            args=args,
            kwargs=kwargs,
        )
    elif cron:
        cronparts = cron.split()
        schedule, _ = CrontabSchedule.objects.get_or_create(
            minute=cronparts[0],
            hour=cronparts[1],
            day_of_week=cronparts[2],
            day_of_month=cronparts[3],
            month_of_year=cronparts[4],
        )
        return PeriodicTask.objects.create(
            interval=schedule,
            description=f"{context.caller.pk}:{verb}",
            task="moo.core.tasks.invoke_verb",
            args=args,
            kwargs=kwargs,
        )
    else:
        tasks.invoke_verb.apply_async(args, kwargs, countdown=delay)
        return None


@_contextmanager
def set_task_perms(who):
    """
    Set the task permissions to those of `who` for the duration of the with-block.
    :param who: the Object whose permissions to assume
    :type who: Object
    """
    caller_is_wizard = context.caller and context.caller.is_wizard()
    player_is_wizard = context.player and context.player.is_wizard()
    if context.caller and not caller_is_wizard and not player_is_wizard:
        raise UserError("Only verbs owned by wizards (or wizard sessions) can modify the task permissions.")

    if not _ContextManager.is_active() or who is None:
        yield
        return
    _ContextManager.override_caller(who)
    try:
        yield
    finally:
        _ContextManager.pop_caller()


def task_time_low(threshold=0.5):
    """
    Return ``True`` if the current task's remaining time is at or below
    *threshold* seconds.

    Always returns ``False`` when there is no task-time limit (e.g. in tests
    or interactive shells without a configured limit).

    :param threshold: seconds remaining before considering time low (default 0.5)
    :rtype: bool
    """
    tt = context.task_time
    return tt is not None and tt.remaining is not None and tt.remaining <= threshold


def schedule_continuation(remaining_items, verb, msg=None):
    """
    Schedule a continuation task carrying the PKs of *remaining_items* and
    notify the current player.

    Intended for use inside long-running verbs that iterate over many objects.
    The continuation verb (e.g. ``audit_batch``, ``reload_batch``) receives
    ``args[0]`` as the list of PKs and dispatches on ``verb_name``.

    Usage::

        for i, item in enumerate(items):
            if task_time_low():
                schedule_continuation(items[i:], this.get_verb("audit_batch"))
                return
            # ... process item

    :param remaining_items: iterable of Objects (or any model with ``.pk``)
    :param verb: Verb instance to invoke for the continuation
    :param msg: optional override for the progress message shown to the player
    """
    pks = [x.pk for x in remaining_items]
    invoke(pks, verb=verb)
    context.player.tell(msg or f"  Continuing ({len(pks)} remaining)...")


def moo_eval(code_string: str):
    """
    Evaluate arbitrary Python code in the RestrictedPython sandbox.

    The code runs with the same environment as verb code, with standard
    verb variables (this, _, context) automatically available.

    :param code_string: Python code to evaluate
    :return: The result of the evaluation
    """
    from moo.core.code import get_default_globals, get_restricted_environment
    from RestrictedPython import compile_restricted
    import ast
    import moo.sdk as _sdk_module  # deferred: avoid circular import at module load time
    from .objects import lookup  # deferred: same reason

    # Build the execution environment
    globals_dict = get_default_globals()
    globals_dict.update(get_restricted_environment("@eval", context.writer))

    # Add standard verb variables to locals, plus all moo.sdk exports
    locals_dict = {name: getattr(_sdk_module, name) for name in _sdk_module.__all__}
    locals_dict.update(
        {
            "this": context.player,
            "passthrough": lambda: None,
            "_": lookup(1),
        }
    )

    # Try to evaluate as an expression first (for REPL-like behavior)
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", category=SyntaxWarning)
            compiled = compile_restricted(code_string, "<@eval>", "eval")
        return eval(compiled, globals_dict, locals_dict)  # pylint: disable=eval-used
    except SyntaxError:
        # If it's not a valid expression, compile as statements
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", category=SyntaxWarning)
            compiled = compile_restricted(code_string, "<@eval>", "exec")

        # Parse the code to check if the last statement is an expression
        try:
            tree = ast.parse(code_string, mode="exec")
            if tree.body and isinstance(tree.body[-1], ast.Expr):
                # Last statement is an expression - evaluate it and return
                # Execute all but the last statement
                if len(tree.body) > 1:
                    with warnings.catch_warnings():
                        warnings.simplefilter("ignore", category=SyntaxWarning)
                        exec_compiled = compile_restricted(
                            (
                                ast.unparse(tree.body[:-1][0])
                                if len(tree.body) == 2
                                else "\n".join(ast.unparse(stmt) for stmt in tree.body[:-1])
                            ),
                            "<@eval>",
                            "exec",
                        )
                    exec(exec_compiled, globals_dict, locals_dict)  # pylint: disable=exec-used

                # Now evaluate and return the last expression
                last_expr_code = ast.unparse(tree.body[-1].value)
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore", category=SyntaxWarning)
                    expr_compiled = compile_restricted(last_expr_code, "<@eval>", "eval")
                return eval(expr_compiled, globals_dict, locals_dict)  # pylint: disable=eval-used
        except Exception:  # pylint: disable=broad-except
            pass  # Fall back to just executing

        # Execute the code (no return value)
        exec(compiled, globals_dict, locals_dict)  # pylint: disable=exec-used
        return None
