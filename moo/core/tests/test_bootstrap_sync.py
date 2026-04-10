# -*- coding: utf-8 -*-
"""
Tests for the idempotent bootstrap sync system.

Covers:
- bootstrap.get_or_create_object() helper
- bootstrap.initialize_dataset() idempotency
- bootstrap.load_verbs() with replace=True
- moo_init --sync management command
"""

import pytest

from moo import bootstrap
from moo.core import code
from moo.core.models import Object, Permission, Repository, Verb


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_get_or_create_object_creates_on_first_call(t_init, t_wizard):
    """First call creates the object and returns created=True."""
    with code.ContextManager(t_wizard, None):
        obj, created = bootstrap.get_or_create_object("Test Widget", unique_name=True)
    assert created is True
    assert Object.objects.filter(name="Test Widget", unique_name=True).count() == 1


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_get_or_create_object_is_idempotent(t_init, t_wizard):
    """Second call returns the existing object without creating a duplicate."""
    with code.ContextManager(t_wizard, None):
        obj1, _ = bootstrap.get_or_create_object("Test Widget", unique_name=True)
        obj2, created = bootstrap.get_or_create_object("Test Widget", unique_name=True)
    assert created is False
    assert obj1.pk == obj2.pk
    assert Object.objects.filter(name="Test Widget", unique_name=True).count() == 1


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_get_or_create_object_adds_parents_only_on_creation(t_init, t_wizard):
    """Parents are added when the object is newly created; not re-added on subsequent calls."""
    with code.ContextManager(t_wizard, None):
        parent = bootstrap.get_or_create_object("Parent Class", unique_name=True)[0]
        child, _ = bootstrap.get_or_create_object("Child Class", unique_name=True, parents=[parent])
    assert child.parents.filter(pk=parent.pk).exists()
    # Second call should not raise IntegrityError despite unique_together on Relationship
    with code.ContextManager(t_wizard, None):
        child2, created = bootstrap.get_or_create_object("Child Class", unique_name=True, parents=[parent])
    assert created is False
    assert child.parents.filter(pk=parent.pk).count() == 1


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_initialize_dataset_is_idempotent(t_init):
    """Calling initialize_dataset() on an already-bootstrapped DB does not create duplicates."""
    sentinel_count_before = Object.objects.filter(unique_name=True).count()
    perm_count_before = Permission.objects.count()

    bootstrap.initialize_dataset("test")  # second call on same dataset

    assert Object.objects.filter(unique_name=True).count() == sentinel_count_before
    assert Permission.objects.count() == perm_count_before


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_load_verb_source_replace_true_does_not_duplicate(t_init, t_wizard, tmp_path):
    """load_verb_source() with replace=True updates in place without creating a duplicate."""
    import pathlib

    from moo.bootstrap import load_verb_source

    system = Object.objects.get(pk=1)
    repo = Repository.objects.get(slug="test")

    nothing = Object.objects.get(name="nothing", unique_name=True)
    verb_file = tmp_path / "ping.py"
    verb_file.write_text("#!moo verb ping --on nothing\nprint('v1')\n", encoding="utf8")

    with code.ContextManager(t_wizard, None):
        load_verb_source(verb_file, system, repo, replace=False)
    assert Verb.objects.filter(origin=nothing, names__name="ping").count() == 1

    # Call again with replace=True — should update in place, not create a second record.
    verb_file.write_text("#!moo verb ping --on nothing\nprint('v2')\n", encoding="utf8")
    with code.ContextManager(t_wizard, None):
        load_verb_source(verb_file, system, repo, replace=True)

    assert Verb.objects.filter(origin=nothing, names__name="ping").count() == 1
    assert "v2" in Verb.objects.filter(origin=nothing, names__name="ping").first().code


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_load_verbs_replace_param_threads_through(t_init, t_wizard, tmp_path, monkeypatch):
    """load_verbs() passes replace=True through to load_verb_source()."""
    calls = []

    def _stub(path, system, repo, replace=False):
        calls.append(replace)

    monkeypatch.setattr(bootstrap, "load_verb_source", _stub)

    repo = Repository.objects.get(slug="test")
    bootstrap.load_verbs(repo, "moo.bootstrap.default_verbs", replace=True)

    assert len(calls) > 0, "load_verb_source was never called"
    assert all(r is True for r in calls), "Some calls to load_verb_source used replace=False"


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_moo_init_sync_succeeds_on_existing_db(t_init):
    """moo_init --sync succeeds on an already-bootstrapped DB without raising."""
    from django.core.management import call_command

    call_command("moo_init", sync=True, bootstrap="default")


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_moo_init_sync_fails_on_uninitialised_db():
    """moo_init --sync raises RuntimeError when the dataset hasn't been initialised yet."""
    from django.core.management import call_command

    with pytest.raises(RuntimeError, match="has not been initialized"):
        call_command("moo_init", sync=True, bootstrap="default")
