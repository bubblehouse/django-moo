# -*- coding: utf-8 -*-
"""
Non-destructive object recovery (spec 200, item K).

``@recycle`` is destructive — a permanent Django delete with no recovery.
Author recovery of a griefed building and the reaper's "freeze, don't delete"
both want a reversible path.  This module is that path: :func:`soft_recycle`
retains the object's id and inbound references but hides it from the world,
:func:`restore` brings it back, and :func:`destroy` is the genuine hard delete
that remains for real removal.  :func:`sweep_recycled` purges anything left
recycled past the retention window.
"""

from django.utils import timezone

from ..core.exceptions import NoSuchPropertyError
from .context import context


def soft_recycle(obj):
    """Soft-delete an object: hide it, but keep its id and inbound refs.

    Refunds the owner's quota immediately (so the builder can build again) and
    moves the object out of the world.  Idempotent.

    :param obj: the Object to recycle
    :return: the recycled Object
    """
    from .audit import record_action

    if obj.recycled:
        return obj
    obj.can_caller("write", obj)
    # Refund quota now; the eventual hard purge will not refund again.
    try:
        owner = obj.owner
        if owner is not None:
            quota = owner.get_property("ownership_quota", recurse=False)
            if quota is not None:
                owner.set_property("ownership_quota", quota + 1)
    except NoSuchPropertyError:
        pass
    obj.recycled = True
    obj.recycled_at = timezone.now()
    obj.location = None
    obj.save()
    record_action("recycle", target=obj)
    return obj


def restore(obj, location=None):
    """Restore a soft-recycled object, re-consuming a quota slot.

    :param obj: the recycled Object
    :param location: where to place it (defaults to the owner's location)
    :return: the restored Object
    """
    from .audit import record_action

    if not obj.recycled:
        return obj
    obj.can_caller("write", obj)
    try:
        owner = obj.owner
        if owner is not None:
            quota = owner.get_property("ownership_quota", recurse=False)
            if quota is not None:
                owner.set_property("ownership_quota", quota - 1)
    except NoSuchPropertyError:
        pass
    obj.recycled = False
    obj.recycled_at = None
    if location is None and obj.owner is not None:
        location = obj.owner.location
    obj.location = location
    obj.save()
    record_action("restore", target=obj)
    return obj


def destroy(obj):
    """Hard-delete an object permanently (the irreversible path).

    :param obj: the Object to destroy
    """
    obj.delete()


def get_recycled(owner=None):
    """List soft-recycled objects (optionally for one owner) for recovery.

    Uses ``global_objects`` because the site-scoped default manager hides
    recycled rows by design.

    :param owner: optional owner Object to filter by
    :return: list of recycled Objects
    """
    from ..core.code import ContextManager
    from ..core.models import Object

    qs = Object.global_objects.filter(recycled=True)
    site = ContextManager.get_site()
    if site is not None:
        qs = qs.filter(site=site)
    if owner is not None:
        qs = qs.filter(owner=owner)
    return list(qs.order_by("recycled_at"))


def sweep_recycled(older_than_days=30):
    """Hard-delete objects left recycled beyond the retention window.

    The reaper's final step.  Returns the number purged.

    :param older_than_days: retention window in days
    :return: count of objects hard-deleted
    """
    import datetime

    from ..core.models import Object

    cutoff = timezone.now() - datetime.timedelta(days=older_than_days)
    purged = 0
    for obj in Object.global_objects.filter(recycled=True, recycled_at__lt=cutoff):
        obj.delete()
        purged += 1
    return purged
