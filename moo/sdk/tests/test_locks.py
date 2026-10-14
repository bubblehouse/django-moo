# -*- coding: utf-8 -*-
"""
Tests for moo.sdk.lock_until_commit.

The tests that prove the locking run only on Postgres; the test settings use
SQLite, where the call does nothing. Run them with a Postgres ``DATABASES``
setting.
"""

import threading
import time

import pytest
from django.db import connection, connections, transaction

from moo.core import code, create
from moo.core.exceptions import LockTimeout
from moo.sdk import lock_until_commit
from moo.sdk.locks import _lock_number

postgres_only = pytest.mark.skipif(connection.vendor != "postgresql", reason="advisory locks need Postgres")


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_lock_rejects_bad_arguments(t_init, t_wizard):
    """Empty, long, or non-string names and out-of-range waits raise ValueError."""
    with code.ContextManager(t_wizard, lambda _: None):
        for kwargs in ({"name": ""}, {"name": "x" * 201}, {"name": 5}, {"name": "ok", "wait": 60}):
            with pytest.raises(ValueError):
                lock_until_commit(**kwargs)


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_lock_is_scoped_to_the_verb_owner(t_init, t_wizard):
    """The same name under two different owners maps to two different lock numbers."""
    with code.ContextManager(t_wizard, lambda _: None):
        plain = create("plain owner")
        wizard_number = _lock_number("shared")
    with code.ContextManager(plain, lambda _: None):
        assert _lock_number("shared") != wizard_number
        assert _lock_number("shared") == _lock_number("shared")


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_verb_code_can_take_a_lock(t_init, t_wizard):
    """Verb code imports lock_until_commit from moo.sdk; outside Postgres it does nothing."""
    with code.ContextManager(t_wizard, lambda _: None):
        thing = create("locker")
        thing.add_verb(
            "bump",
            code=(
                "from moo.sdk import lock_until_commit\n"
                "lock_until_commit('bump')\n"
                "lock_until_commit('bump')\n"
                "this.set_property('count', this.get_property('count') + 1)\n"
                "return this.get_property('count')\n"
            ),
        )
        thing.set_property("count", 0)
        assert thing.bump() == 1
        assert thing.bump() == 2


def _in_thread(target):
    """Run ``target`` on a new thread with its own database connection; return the thread and its errors."""
    errors = []

    def run():
        try:
            target()
        except Exception as err:  # pylint: disable=broad-except
            errors.append(err)
        finally:
            connections.close_all()

    thread = threading.Thread(target=run)
    thread.start()
    return thread, errors


@postgres_only
@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_lock_blocks_a_second_transaction_until_commit(t_init, t_wizard):
    """A second transaction cannot take a held lock; it can once the holder commits."""
    held = threading.Event()
    release = threading.Event()

    def holder():
        with code.ContextManager(t_wizard, lambda _: None), transaction.atomic():
            lock_until_commit("ledger:1")
            lock_until_commit("ledger:1")  # The same transaction can take it again.
            held.set()
            release.wait(5)

    thread, errors = _in_thread(holder)
    assert held.wait(5)
    with code.ContextManager(t_wizard, lambda _: None):
        with pytest.raises(LockTimeout), transaction.atomic():
            lock_until_commit("ledger:1", wait=0.1)
        with transaction.atomic():
            lock_until_commit("ledger:2", wait=0)
    release.set()
    thread.join(5)
    assert not errors
    with code.ContextManager(t_wizard, lambda _: None), transaction.atomic():
        lock_until_commit("ledger:1", wait=0)


@postgres_only
@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_lock_prevents_a_lost_update(t_init, t_wizard):
    """Two transactions that each read, add one, and write a property both count when they lock first."""
    with code.ContextManager(t_wizard, lambda _: None):
        counter = create("counter")
        counter.set_property("count", 0)

    def bump():
        with code.ContextManager(t_wizard, lambda _: None), transaction.atomic():
            lock_until_commit("counter")
            value = counter.get_property("count")
            time.sleep(0.2)  # Hold the read long enough for the other thread to try.
            counter.set_property("count", value + 1)

    threads = [_in_thread(bump) for _ in range(2)]
    for thread, errors in threads:
        thread.join(10)
        assert not errors
    with code.ContextManager(t_wizard, lambda _: None):
        assert counter.get_property("count") == 2
