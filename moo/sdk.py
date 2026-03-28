# -*- coding: utf-8 -*-
"""
Public SDK for verb authors. Import game primitives from here:

    from moo.sdk import context, lookup, create, NoSuchObjectError
"""

import logging
import warnings
from contextlib import contextmanager as _contextmanager
from typing import Union

from .core.code import ContextManager as _ContextManager
from .core.exceptions import (
    QuotaError,
    AmbiguousObjectError,
    UserError,
    UsageError,
    NoSuchObjectError,
    NoSuchVerbError,
    NoSuchPropertyError,
)

__all__ = [
    "lookup",
    "create",
    "players",
    "connected_players",
    "write",
    "open_editor",
    "open_paginator",
    "invoke",
    "set_task_perms",
    "context",
    "moojson",
    "get_session_setting",
    "set_session_setting",
    "list_ssh_keys",
    "add_ssh_key",
    "remove_ssh_key",
    "NoSuchObjectError",
    "NoSuchVerbError",
    "NoSuchPropertyError",
    "AmbiguousObjectError",
    "UserError",
    "UsageError",
]

# Re-export moojson for verb use
from .core import moojson

_log = logging.getLogger(__name__)


def lookup(x: Union[int, str]):
    """
    Lookup an object globally by PK, name, or alias.

    :param x: lookup value
    :return: the result of the lookup
    :rtype: Object
    :raises NoSuchObjectError: when a result cannot be found
    """
    from django.db.models import Q
    from .core.models import Object

    if isinstance(x, int):
        return Object.objects.get(pk=x)
    elif isinstance(x, str):
        if x.startswith("$"):
            system = lookup(1)
            return system.get_property(name=x[1:])
        qs = Object.objects.filter(Q(name__iexact=x) | Q(aliases__alias__iexact=x)).distinct()
        if not qs:
            if context.parser:
                obj = context.parser.get_pronoun_object(x)
                if obj:
                    return obj
            raise NoSuchObjectError(x)
        return qs[0]
    else:
        raise ValueError(f"{x} is not a supported lookup value.")


def connected_players(within=None):
    """
    Return a list of player avatars whose ``last_connected_time`` property was
    updated within the given *within* window (default: 5 minutes).

    The ``last_connected_time`` value is precached into the session-level
    property cache on every returned Object so subsequent ``get_property``
    calls incur no extra queries.

    :param within: recency window; defaults to ``timedelta(minutes=5)``
    :type within: timedelta
    :return: Objects whose avatars have connected recently
    :rtype: list[Object]
    """
    from datetime import datetime, timedelta, timezone
    from .core.models.property import Property

    if within is None:
        within = timedelta(minutes=5)

    threshold = datetime.now(timezone.utc) - within

    # Single query: restrict to player avatars only and eagerly load the
    # origin Object to avoid per-row SELECT on prop.origin access.
    props = Property.objects.filter(name="last_connected_time", origin__player__isnull=False).select_related("origin")

    pcache = _ContextManager.get_prop_lookup_cache()
    result = []
    for prop in props:
        value = moojson.loads(prop.value)
        if pcache is not None:
            pcache[(prop.origin_id, "last_connected_time", True)] = value
        if value is not None and value >= threshold:
            result.append(prop.origin)

    return result


def players():
    """
    Return a list of all player avatar Objects.

    :return: Objects that are player avatars
    :rtype: list[Object]
    """
    from .core.models.auth import Player

    return [p.avatar for p in Player.objects.select_related("avatar").filter(avatar__isnull=False)]


def create(name, *a, **kw):
    """
    Creates and returns a new object whose parents are `parents` and whose owner is as described below.
    Provided `parents` are valid Objects with `derive` permission, otherwise :class:`.PermissionError` is
    raised. After the new object is created, its `initialize` verb, if any, is called with no arguments.

    The owner of the new object is either the programmer (if `owner` is not provided), or the provided owner,
    if the caller has permission to `entrust` the object.

    If the intended owner of the new object has a property named `ownership_quota` and the value of that
    property is an integer, then `create()` treats that value as a quota. If the quota is less than
    or equal to zero, then the quota is considered to be exhausted and `create()` raises :class:`.QuotaError` instead
    of creating an object. Otherwise, the quota is decremented and stored back into the `ownership_quota`
    property as a part of the creation of the new object.

    :param name: canonical name
    :type name: str
    :param owner: owner of the Object being created
    :type owner: Object
    :param location: where to create the Object
    :type location: Object
    :param parents: a list of parents for the Object
    :type parents: list[Object]
    :param obvious: whether the object appears in room contents listings (default False)
    :type obvious: bool
    :return: the new object
    :rtype: Object
    :raises PermissionError: if the caller is not allowed to `derive` from the parent
    :raises QuotaError: if the caller has a quota and it has been exceeded
    """
    from .core.models.object import Object, Property

    _SYSTEM_KEY = "__system_object__"
    cache = _ContextManager.get_perm_cache()
    if cache is not None and _SYSTEM_KEY in cache:
        system = cache[_SYSTEM_KEY]
    else:
        system = Object.objects.get(pk=1)
        if cache is not None:
            cache[_SYSTEM_KEY] = system
    default_parents = [system.root_class] if system.has_property("root_class") else []
    if context.caller:
        try:
            quota = context.caller.get_property("ownership_quota", recurse=False)
            if quota > 0:
                context.caller.set_property("ownership_quota", quota - 1)
            else:
                raise QuotaError(f"{context.caller} has run out of quota.")
        except NoSuchPropertyError:
            pass
        if "owner" not in kw:
            kw["owner"] = context.caller
    if "location" not in kw and "owner" in kw:
        kw["location"] = kw["owner"].location
    parents = kw.pop("parents", default_parents)
    obj = Object.objects.create(name=name, *a, **kw)
    if parents:
        obj.parents.add(*parents)
    if obj.has_verb("initialize"):
        invoke(obj.get_verb("initialize"))
    return obj


def write(obj, message):
    """
    Send an asynchronous message to the user.

    :param obj: the Object to write to
    :type obj: Object
    :param message: any pickle-able object
    :type message: Any
    """
    from moo.core import _publish_to_player

    if context.caller and not context.caller.is_wizard():
        raise UserError("Only verbs owned by wizards can write to the console.")
    _publish_to_player(obj, message)


def open_editor(obj, initial_content: str, callback_verb, *args, content_type: str = "text", title: str | None = None):
    """
    Request the connected SSH client to open a full-screen text editor.
    When the user saves, the edited text is passed to callback_verb as args[0],
    followed by any extra positional arguments supplied here.
    If the user cancels, the callback is not invoked.

    :param obj: the player Object whose client should open the editor
    :param initial_content: text to pre-populate the editor buffer
    :param callback_verb: Verb to invoke with the edited text as args[0]
    :param args: additional arguments forwarded to the callback verb as args[1:]
    :param content_type: "python", "json", or "text" (default); controls syntax highlighting
    """
    from moo.core import _publish_to_player

    if content_type not in ("python", "json", "text"):
        raise UserError(f"content_type must be 'python', 'json', or 'text', not {content_type!r}.")
    if context.caller and not context.caller.is_wizard():
        raise UserError("Only verbs owned by wizards can open the editor.")
    _publish_to_player(
        obj,
        {
            "event": "editor",
            "content": initial_content,
            "content_type": content_type,
            "title": title,
            "args": list(args),
            "callback_this_id": callback_verb._invoked_object.pk,  # pylint: disable=protected-access
            "callback_verb_name": callback_verb._invoked_name,  # pylint: disable=protected-access
            "caller_id": context.caller.pk,
            "player_id": (context.player or context.caller).pk,
        },
    )


def open_paginator(obj, content: str, content_type: str = "text"):
    """
    Request the connected SSH client to open a full-screen read-only paginator.
    The user can scroll through the content and press Q to quit.

    :param obj: the player Object whose client should open the paginator
    :param content: text to display
    :param content_type: "python", "json", or "text" (default); controls syntax highlighting
    """
    from moo.core import _publish_to_player

    if content_type not in ("python", "json", "text"):
        raise UserError(f"content_type must be 'python', 'json', or 'text', not {content_type!r}.")
    if context.caller and not context.caller.is_wizard():
        raise UserError("Only verbs owned by wizards can open the paginator.")
    _publish_to_player(
        obj,
        {
            "event": "paginator",
            "content": content,
            "content_type": content_type,
        },
    )


def invoke(*args, verb=None, callback=None, delay: int = 0, periodic: bool = False, cron: str = None, **kwargs):
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
            caller_id=context.caller.pk,
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
    if context.caller and not context.caller.is_wizard():
        raise UserError("Only verbs owned by wizards can modify the task permissions..")

    if not _ContextManager.is_active() or who is None:
        yield
        return
    _ContextManager.override_caller(who)
    try:
        yield
    finally:
        _ContextManager.pop_caller()


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

    # Build the execution environment
    globals_dict = get_default_globals()
    globals_dict.update(get_restricted_environment("@eval", context.writer))

    # Add standard verb variables to locals, plus all moo.sdk exports
    _sdk_globals = globals()
    locals_dict = {name: _sdk_globals[name] for name in __all__}
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


class _Context:
    """
    This wrapper class makes it easy to use a number of contextvars.
    """

    class descriptor:
        """
        Used to perform dynamic lookups of contextvars.

        Defined as a data descriptor (implements both __get__ and __set__) so that
        Python's attribute lookup always invokes __get__ and never allows an instance
        attribute to shadow it.  Verb code must not be able to overwrite context.caller
        (or any other context attribute) with a forged object.
        """

        def __init__(self, name):
            self.name = name

        def __get__(self, obj, objtype=None):
            return _ContextManager.get(self.name)

        def __set__(self, obj, value):
            raise AttributeError("context attributes are read-only")

        def __delete__(self, obj):
            raise AttributeError("context attributes are read-only")

    def __setattr__(self, name, value):
        raise AttributeError("context attributes are read-only")

    caller = descriptor("caller")  # Code runs with the permission of this object
    player = descriptor("player")  # This object that originally invoked this session, defaults to original caller
    writer = descriptor("writer")  # A callable that will print to the player's console
    parser = descriptor("parser")
    task_id = descriptor("task_id")  # The current task ID
    task_time = descriptor("task_time")  # TaskTime(elapsed, time_limit, remaining) for the current task
    caller_stack = descriptor("caller_stack")  # A stack of callers, with the current caller at the end


context = _Context()


# Session settings for PREFIX/SUFFIX/QUIET commands
def get_session_setting(key, default=None):
    """
    Get a session-specific output setting for the current player.

    Session settings are stored per-user and cleared on disconnect.
    Used by PREFIX, SUFFIX, and QUIET commands for machine-readable output.

    :param key: setting name ('output_prefix', 'output_suffix', 'quiet_mode', 'color_system')
    :param default: value to return if setting is not found
    :return: setting value or default
    """
    from .shell import prompt as prompt_module

    player = context.player
    if not player:
        return default

    user_pk = player.owner.pk if player.owner else None
    if user_pk is None:
        return default

    settings = prompt_module._session_settings.get(user_pk, {})  # pylint: disable=protected-access
    return settings.get(key, default)


def set_session_setting(key, value):
    """
    Set a session-specific output setting for the current player.

    Session settings are stored per-user and cleared on disconnect.
    Used by PREFIX, SUFFIX, and QUIET commands for machine-readable output.

    Publishes a ``session_setting`` event to the player's Kombu message queue,
    which the SSH server's ``process_messages()`` loop picks up and applies to
    its own in-process registry. This bridges the Celery worker / SSH server
    process boundary.

    :param key: setting name ('output_prefix', 'output_suffix', 'quiet_mode', 'color_system')
    :param value: setting value
    """
    from moo.core import _publish_to_player

    player = context.player
    if not player:
        return
    _publish_to_player(player, {"event": "session_setting", "key": key, "value": value})


def list_ssh_keys(player_obj):
    """
    Return a list of UserKey records for the player's Django User, ordered by creation date.

    :param player_obj: the player Object whose SSH keys to list
    :type player_obj: Object
    :return: list of UserKey model instances
    :rtype: list
    :raises UserError: if the caller is not wizard-owned, or the player has no account
    """
    from moo.core.models.auth import Player
    from simplesshkey.models import UserKey

    if context.caller and not context.caller.is_wizard():
        raise UserError("Only verbs owned by wizards can manage SSH keys.")
    try:
        player_record = Player.objects.get(avatar=player_obj)
    except Player.DoesNotExist as exc:
        raise UserError(f"{player_obj.title()} has no player account.") from exc
    if player_record.user is None:
        raise UserError(f"{player_obj.title()} has no Django user account.")
    return list(UserKey.objects.filter(user=player_record.user).order_by("created"))


def add_ssh_key(player_obj, key_string):
    """
    Validate and add an SSH public key for the player's Django User.

    The key is parsed and normalised by simplesshkey before being saved.
    The key name is taken from the key's comment field if present.

    :param player_obj: the player Object to add the key to
    :type player_obj: Object
    :param key_string: the SSH public key string (e.g. ``ssh-rsa AAAA... comment``)
    :type key_string: str
    :return: the newly created UserKey instance
    :rtype: UserKey
    :raises UserError: if the caller is not wizard-owned, the key is invalid, or the player has no account
    """
    from moo.core.models.auth import Player
    from simplesshkey.models import UserKey
    from django.core.exceptions import ValidationError

    if context.caller and not context.caller.is_wizard():
        raise UserError("Only verbs owned by wizards can manage SSH keys.")
    try:
        player_record = Player.objects.get(avatar=player_obj)
    except Player.DoesNotExist as exc:
        raise UserError(f"{player_obj.title()} has no player account.") from exc
    if player_record.user is None:
        raise UserError(f"{player_obj.title()} has no Django user account.")
    key = UserKey(user=player_record.user, key=key_string)
    try:
        key.full_clean()
    except ValidationError as e:
        raise UserError(f"Invalid SSH key: {e}") from e
    key.save()
    return key


def remove_ssh_key(player_obj, index):
    """
    Remove the SSH key at the given 1-based index for the player.

    The index corresponds to the position in the list returned by :func:`list_ssh_keys`.

    :param player_obj: the player Object whose SSH key to remove
    :type player_obj: Object
    :param index: 1-based position of the key to remove
    :type index: int
    :raises UserError: if the caller is not wizard-owned, the index is out of range, or the player has no account
    """
    from moo.core.models.auth import Player
    from simplesshkey.models import UserKey

    if context.caller and not context.caller.is_wizard():
        raise UserError("Only verbs owned by wizards can manage SSH keys.")
    try:
        player_record = Player.objects.get(avatar=player_obj)
    except Player.DoesNotExist as exc:
        raise UserError(f"{player_obj.title()} has no player account.") from exc
    if player_record.user is None:
        raise UserError(f"{player_obj.title()} has no Django user account.")
    keys = list(UserKey.objects.filter(user=player_record.user).order_by("created"))
    if not (1 <= index <= len(keys)):
        raise UserError(f"No key at index {index}. Use @keys to list your keys.")
    key = keys[index - 1]
    key.delete()
    return key


def boot_player(obj):
    """

    Disconnect the given player from the MOO server.

    Publishes a ``disconnect`` event to the player's Kombu message queue,
    which the SSH server's ``process_messages()`` loop picks up and exits cleanly.

    Permission: the caller must be the player being booted, or a wizard.

    :param obj: the player Object to disconnect
    """
    from moo.core import _publish_to_player

    caller = context.caller
    if caller and caller != obj and not caller.is_wizard():
        raise UserError("Only wizards can boot other players.")
    _publish_to_player(obj, {"event": "disconnect"})
