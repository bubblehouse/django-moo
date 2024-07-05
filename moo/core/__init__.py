# -*- coding: utf-8 -*-
"""
Core MOO functionality, object model, verbs.
"""

import logging
from typing import Union

from .code import context

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
