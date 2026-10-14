# -*- coding: utf-8 -*-
"""
Named locks that last until the current transaction ends.

Verbs run as Celery tasks, and several tasks can run at once. Each task runs
in one database transaction, but a transaction does not stop two tasks from
reading the same value: under Postgres's default isolation, both tasks read the
last committed value, both change it, and the later write wins. The earlier
change is lost, with no error.

:func:`lock_until_commit` closes that gap. A task calls it before it reads the
value. Only one transaction at a time can hold a given lock name; another
transaction that asks for it waits until the holder commits or rolls back, and
then reads the committed result. The lock does not block plain reads or writes
of any table; it blocks only other callers of the same name.

The lock is a Postgres transaction-scoped advisory lock
(``pg_try_advisory_xact_lock``). Postgres releases it at commit or rollback,
also when Celery kills the task. The same transaction can take it again. On
another database, or outside a transaction, the call does nothing.

A lock name is scoped to the active Site and to the owner of the calling verb
(``context.caller``). So a player's own verbs can never hold, or wait on, a lock
that Wizard-owned code uses.
"""

import hashlib
import time

from django.db import connection

from ..core.exceptions import LockTimeout
from .context import context

#: The longest a lock name may be.
MAX_LOCK_NAME = 200
#: The longest a caller may wait for a lock, in seconds. A verb task has a few seconds in all.
MAX_LOCK_WAIT = 10
#: The first and the longest pause between attempts to take a held lock, in seconds.
POLL_START = 0.005
POLL_MAX = 0.05


def _lock_scope(name):
    """Return the scoped lock name: the active Site, the calling verb's owner, and ``name``."""
    from ..core.code import ContextManager  # pylint: disable=import-outside-toplevel

    site = ContextManager.get_site()
    caller = context.caller
    site_id = site.pk if site is not None else getattr(caller, "site_id", None)
    owner = caller.pk if caller is not None else None
    return f"{site_id}:{owner}:{name}"


def _lock_number(name):
    """Return the signed 64-bit advisory lock number for a scoped lock name."""
    digest = hashlib.blake2b(_lock_scope(name).encode("utf8"), digest_size=8).digest()
    return int.from_bytes(digest, "big", signed=True)


def lock_until_commit(name, wait=2):
    """
    Take the lock ``name`` for the rest of the current transaction.

    Call it before a read-modify-write that two tasks can run at the same time::

        lock_until_commit(f"ledger:{player.pk}")
        row = ledger.get_property(key)
        row["xp"] = row["xp"] + amount
        ledger.set_property(key, row)

    There is no release call. The lock ends when the task's transaction commits
    or rolls back. A second call with the same name in the same transaction
    returns at once. On a database other than Postgres, or outside a
    transaction, the call does nothing.

    :param name: the lock name; a non-empty string of at most 200 characters
    :param wait: seconds to wait for a held lock, from 0 to 10; cut to the time
        the task has left
    :raises ValueError: if ``name`` or ``wait`` is out of range
    :raises LockTimeout: if another transaction holds the lock for the whole wait
    """
    if not isinstance(name, str) or not name or len(name) > MAX_LOCK_NAME:
        raise ValueError(f"A lock name must be a string of 1 to {MAX_LOCK_NAME} characters.")
    if not 0 <= wait <= MAX_LOCK_WAIT:
        raise ValueError(f"A lock wait must be from 0 to {MAX_LOCK_WAIT} seconds.")
    if connection.vendor != "postgresql" or not connection.in_atomic_block:
        return
    task_time = context.task_time
    if task_time is not None and task_time.remaining is not None:
        wait = min(wait, max(task_time.remaining - 0.25, 0))

    number = _lock_number(name)
    deadline = time.monotonic() + wait
    pause = POLL_START
    with connection.cursor() as cursor:
        while True:
            cursor.execute("SELECT pg_try_advisory_xact_lock(%s)", [number])
            if cursor.fetchone()[0]:
                return
            if time.monotonic() >= deadline:
                raise LockTimeout(f"The lock {name!r} is busy. Try again.")
            time.sleep(pause)
            pause = min(pause * 2, POLL_MAX)
