# -*- coding: utf-8 -*-
"""
Core MOO functionality, object model, verbs.
"""

import logging
import warnings
from typing import Union

from .code import context
from .exceptions import QuotaError

__all__ = ["lookup", "create", "write", "invoke", "api"]

log = logging.getLogger(__name__)


def lookup(x: Union[int, str]):
    """
    Lookup an object globally by PK, name, or alias.

    :param x: lookup value
    :return: the result of the lookup
    :rtype: Object
    :raises Object.DoesNotExist: when a result cannot be found
    """
    from .models import Object

    if isinstance(x, int):
        return Object.objects.get(pk=x)
    elif isinstance(x, str):
        qs = Object.objects.filter(name__iexact=x)
        aliases = Object.objects.filter(aliases__alias__iexact=x)
        qs = qs.union(aliases)
        if not qs:
            raise Object.DoesNotExist(x)
        return qs[0]
    else:
        raise ValueError(f"{x} is not a supported lookup value.")


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
    :return: the new object
    :rtype: Object
    :raises PermissionError: if the caller is not allowed to `derive` from the parent
    :raises QuotaError: if the caller has a quota and it has been exceeded
    """
    from .models.object import AccessibleObject, AccessibleProperty

    if api.caller:
        try:
            quota = api.caller.get_property("ownership_quota", recurse=False)
            if quota > 0:
                api.caller.set_property("ownership_quota", quota - 1)
            else:
                raise QuotaError(f"{api.caller} has run out of quota.")
        except AccessibleProperty.DoesNotExist:
            pass
        if "owner" not in kw:
            kw["owner"] = api.caller
    if "location" not in kw and "owner" in kw:
        kw["location"] = kw["owner"].location
    parents = kw.pop("parents", [])
    obj = AccessibleObject.objects.create(name=name, *a, **kw)
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
    from redis.exceptions import ConnectionError  # pylint: disable=redefined-builtin
    from .models.auth import Player

    try:
        player = Player.objects.get(avatar=obj)
    except Player.DoesNotExist:
        return
    from kombu import Exchange, Queue

    from ..celery import app

    with app.default_connection() as conn:
        try:
            channel = conn.channel()
        except ConnectionError:
            warnings.warn(RuntimeWarning(f"ConnectionError({obj}): {message}"))
            return
        queue = Queue(
            "messages", Exchange("moo", type="direct", channel=channel), f"user-{player.user.pk}", channel=channel
        )
        with app.producer_or_acquire() as producer:
            producer.publish(
                dict(message=message, caller=context.get("caller")),
                serializer="pickle",
                exchange=queue.exchange,
                routing_key=f"user-{player.user.pk}",
                declare=[queue],
                retry=True,
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
    from django_celery_beat.models import CrontabSchedule, IntervalSchedule, PeriodicTask

    from moo.core import tasks
    if hasattr(verb, "invoked_name"):
        l = list(args)
        l.insert(0, verb.invoked_name)
        args = tuple(l)
    if hasattr(verb, "invoked_object"):
        kwargs["this_id"] = verb.invoked_object.pk
    kwargs.update(
        dict(
            caller_id=api.caller.pk,
            verb_id=verb.pk,
            callback_verb_id=callback.pk if callback else None,
        )
    )
    if delay and periodic:
        schedule, _ = IntervalSchedule.objects.get_or_create(
            every=delay,
            period=IntervalSchedule.SECONDS,
        )
        return PeriodicTask.objects.create(
            interval=schedule,
            description=f"{api.caller.pk}:{verb}",
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
            description=f"{api.caller.pk}:{verb}",
            task="moo.core.tasks.invoke_verb",
            args=args,
            kwargs=kwargs,
        )
    else:
        tasks.invoke_verb.apply_async(args, kwargs, countdown=delay)
        return None


class _API:
    """
    This wrapper class makes it easy to use a number of contextvars.
    """

    class descriptor:
        """
        Used to perform dynamic lookups of contextvars.
        """

        def __init__(self, name):
            self.name = name

        def __get__(self, obj, objtype=None):
            d = context.vars.get({})
            return d.get(self.name)

        def __set__(self, obj, value):
            d = context.vars.get({})
            d[self.name] = value
            context.vars.set(d)

    caller = descriptor("caller")  # The user object that invoked this code
    writer = descriptor("writer")  # A callable that will print to the caller's console
    parser = descriptor("parser")


api = _API()
