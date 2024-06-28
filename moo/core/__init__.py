# -*- coding: utf-8 -*-
"""
Core MOO functionality, object model, verbs.
"""

import logging

from .code import context

log = logging.getLogger(__name__)

def create_object(name, *a, **kw):
    kw['name'] = name
    if 'owner' not in kw:
        kw['owner'] =  context.get('caller')
    if 'location' not in kw and kw['owner']:
        kw['location'] = kw['owner'].location
    from .models.object import AccessibleObject
    return AccessibleObject.objects.create(*a, **kw)

def message_user(user_obj, message, producer=None):
    from .models.auth import Player
    try:
        player = Player.objects.get(avatar=user_obj)
    except Player.DoesNotExist:
        return
    from ..celery import app
    from kombu import Exchange, Queue
    with app.default_connection() as conn:
        channel = conn.channel()
        queue = Queue('messages', Exchange('moo', type='direct', channel=channel), f'user-{player.user.pk}', channel=channel)
        with app.producer_or_acquire(producer) as producer:  #  pylint: disable=redefined-argument-from-local
            producer.publish(
                dict(message=message, caller=context.get('caller')),
                serializer='pickle',
                exchange=queue.exchange,
                routing_key=f'user-{player.user.pk}',
                declare=[queue],
                retry=True,
            )

class API:
    class descriptor:
        def __init__(self, name):
            self.name = name

        def __get__(self, obj, objtype=None):
            d = context.vars.get({})
            return d.get(self.name)

        def __set__(self, obj, value):
            d = context.vars.get({})
            d[self.name] = value
            context.vars.set(d)

    caller = descriptor('caller')
    writer = descriptor('writer')
    args = descriptor('args')
    kwargs = descriptor('kwargs')
    parser = descriptor('parser')

api = API()
