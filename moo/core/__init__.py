# -*- coding: utf-8 -*-
"""
Core MOO functionality, object model, verbs.
"""

import logging
from typing import Union, Optional

from .code import context

__all__ = ['lookup', 'create', 'write', 'invoke', 'api']

log = logging.getLogger(__name__)

def lookup(x:Union[int, str]):
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

def create(name,  *a, owner=None, location=None, parents=None, **kw):
    """
    [`TODO <https://gitlab.com/bubblehouse/django-moo/-/issues/11>`_]
    Creates and returns a new object whose parent is `parent` and whose owner is as described below.
    Either the given `parent` object must be None or a valid object with `derive` permission,
    otherwise :class:`.PermissionError` is raised. After the new object is created, its `initialize`
    verb, if any, is called with no arguments.

    The owner of the new object is either the programmer (if `owner` is not provided), the new object
    itself (if owner was given as None), or the provided owner.

    In addition, the new object inherits all of the other properties on `parent`. These properties have
    the same permission bits as on `parent`. If the `inherit` permission bit is set, then the owner of the
    property on the new object is the same as the owner of the new object itself; otherwise, the owner
    of the property on the new object is the same as that on parent.

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
    if owner is None:
        owner = context.get('caller')
    if location is None and owner:
        location = owner.location
    from .models.object import AccessibleObject
    return AccessibleObject.objects.create(
        name=name,
        location=location,
        owner=owner,
        # parent=parent,
        *a, **kw
    )

def write(obj, message):
    """
    Send an asynchronous message to the user.

    :param obj: the Object to write to
    :type obj: Object
    :param message: any pickle-able object
    :type message: Any
    """
    from .models.auth import Player
    try:
        player = Player.objects.get(avatar=obj)
    except Player.DoesNotExist:
        return
    from ..celery import app
    from kombu import Exchange, Queue
    with app.default_connection() as conn:
        channel = conn.channel()
        queue = Queue('messages', Exchange('moo', type='direct', channel=channel), f'user-{player.user.pk}', channel=channel)
        with app.producer_or_acquire() as producer:
            producer.publish(
                dict(message=message, caller=context.get('caller')),
                serializer='pickle',
                exchange=queue.exchange,
                routing_key=f'user-{player.user.pk}',
                declare=[queue],
                retry=True,
            )

def invoke(*args, verb=None, callback=None, delay:int=0, periodic:bool=False, cron:str=None, **kwargs):
    """
    [`TODO <https://gitlab.com/bubblehouse/django-moo/-/issues/13>`_]
    Asynchronously execute a Verb, optionally returning the result to another Verb.

    Here's a bad example of a talking parrot:

    .. code-block:: Python

        from moo.core import api, invoke
        if api.parser is not None:
            invoke(api.parser.verb, delay=30, periodic=True)
            return
        for obj in api.caller.location.filter(player__isnull=False):
            write(obj, "A parrot squawks.")

    Right now it's just repeating every thirty seconds, but we can make it slightly more intelligent
    by handling our own repeating Verbs:

    .. code-block:: Python

        from moo.core import api, invoke
        if api.parser is not None:
            invoke(api.parser.verb, delay=30, value=0)
            return
        value = kwargs['value'] + 1
        for obj in api.caller.location.filter(player__isnull=False):
            write(obj, f"A parrot squawks {value}.")
        invoke(api.parser.verb, delay=30, value=value)
    
    Let's say we didn't want to handle writing ourselves (we shouldn't) and wanted instead
    to re-use the `say` Verb.

    .. code-block:: Python

        from moo.core import api, invoke
        if api.parser is not None:
            say = api.caller.get_verb('say', recurse=True)
            invoke(verb=api.parser.verb, callback=say, delay=30, value=0)
            return
        value = kwargs['value'] + 1
        return f"A parrot squawks {value}."
    
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
    from django_celery_beat.models import PeriodicTask, IntervalSchedule, CrontabSchedule
    from moo.core import tasks
    kwargs.update(dict(
        caller_id = api.caller.pk,
        verb_id = verb.pk,
        callback_verb_id = callback.pk if callback else None,
    ))
    if delay and periodic:
        schedule, _ = IntervalSchedule.objects.get_or_create(
            every=delay,
            period=IntervalSchedule.SECONDS,
        )
        return PeriodicTask.objects.create(
            interval    = schedule,
            description = f"{api.caller.pk}:{verb}",
            task        = 'moo.core.tasks.invoke_verb',
            args        = args,
            kwargs      = kwargs
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
            interval    = schedule,
            description = f"{api.caller.pk}:{verb}",
            task        = 'moo.core.tasks.invoke_verb',
            args        = args,
            kwargs      = kwargs
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

    caller = descriptor('caller')  # The user object that invoked this code
    writer = descriptor('writer')  # A callable that will print to the caller's console
    parser = descriptor('parser')

api = _API()
