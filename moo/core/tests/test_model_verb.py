# -*- coding: utf-8 -*-
# pylint: disable=protected-access
"""
Tests for moo/core/models/verb.py — Verb, VerbName, Preposition, PrepositionName,
PrepositionSpecifier, Repository.
"""

import warnings

import pytest
from django.db import IntegrityError

from .. import code, create
from ..models import Object, Repository, Verb, VerbName
from .utils import ctx as _ctx


# ---------------------------------------------------------------------------
# Verb.__str__ and .kind
# ---------------------------------------------------------------------------

@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_verb_str(t_init, t_wizard):
    with _ctx(t_wizard):
        obj = create("str obj")
        obj.add_verb("greet", code="pass")
    v = obj.verbs.get(names__name="greet")
    s = str(v)
    assert "greet" in s
    assert str(obj) in s


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_verb_kind(t_init, t_wizard):
    with _ctx(t_wizard):
        obj = create("kind obj")
        obj.add_verb("kv", code="pass")
    v = obj.verbs.get(names__name="kv")
    assert v.kind == "verb"


# ---------------------------------------------------------------------------
# Verb.name()
# ---------------------------------------------------------------------------

@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_verb_name_untitled(t_init, t_wizard):
    with _ctx(t_wizard):
        obj = create("untitled obj")
    v = Verb.objects.create(origin=obj, owner=t_wizard, code="pass")
    assert v.name() == "(untitled)"


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_verb_name_returns_first(t_init, t_wizard):
    with _ctx(t_wizard):
        obj = create("named obj")
        obj.add_verb("alpha", code="pass")
    v = obj.verbs.get(names__name="alpha")
    assert v.name() == "alpha"


# ---------------------------------------------------------------------------
# Verb.save() applies default permissions
# ---------------------------------------------------------------------------

@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_verb_save_applies_default_permissions(t_init, t_wizard):
    from ..models import Access
    with _ctx(t_wizard):
        obj = create("perm obj")
        obj.add_verb("permverb", code="pass")
    v = obj.verbs.get(names__name="permverb")
    assert Access.objects.filter(verb=v).exists()


# ---------------------------------------------------------------------------
# Verb.is_bound()
# ---------------------------------------------------------------------------

@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_verb_is_bound_false(t_init, t_wizard):
    with _ctx(t_wizard):
        obj = create("bound obj")
    v = Verb.objects.create(origin=obj, owner=t_wizard, code="pass")
    VerbName.objects.create(verb=v, name="ubv")
    assert not v.is_bound()


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_verb_is_bound_true(t_init, t_wizard):
    with _ctx(t_wizard):
        obj = create("bindable obj")
    v = Verb.objects.create(origin=obj, owner=t_wizard, code="pass")
    VerbName.objects.create(verb=v, name="bv")
    v._invoked_object = obj
    v._invoked_name = "bv"
    assert v.is_bound()


# ---------------------------------------------------------------------------
# Verb.__call__
# ---------------------------------------------------------------------------

@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_verb_call_executes_code(t_init, t_wizard):
    with _ctx(t_wizard):
        obj = create("callable obj")
        obj.add_verb("compute", code="return 2 + 2")
        result = obj.invoke_verb("compute")
    assert result == 4


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_verb_call_this_isinvoked_object(t_init, t_wizard):
    with _ctx(t_wizard):
        obj = create("this obj")
        obj.add_verb("selfcheck", code="return this.pk")
        result = obj.invoke_verb("selfcheck")
    assert result == obj.pk


# ---------------------------------------------------------------------------
# Verb.passthrough
# ---------------------------------------------------------------------------

@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_verb_passthrough_calls_parent(t_init, t_wizard):
    with _ctx(t_wizard):
        parent = create("pt parent")
        parent.add_verb("greet", code="return 'hello from parent'")
        child = create("pt child", parents=[parent])
        child.add_verb("greet", code="return passthrough() + '!'")
        result = child.invoke_verb("greet")
    assert result == "hello from parent!"


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_verb_passthrough_no_parent_warns(t_init, t_wizard):
    with _ctx(t_wizard):
        obj = create("orphan obj")
        obj.add_verb("lonely", code="passthrough()")
        with pytest.warns(RuntimeWarning, match="Passthrough ignored"):
            obj.invoke_verb("lonely")


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_verb_passthrough_unbound_raises(t_init, t_wizard):
    with _ctx(t_wizard):
        obj = create("unbound pt obj")
    v = Verb.objects.create(origin=obj, owner=t_wizard, code="pass")
    with pytest.raises(RuntimeError, match="unbound"):
        v.passthrough()


# ---------------------------------------------------------------------------
# VerbName uniqueness
# ---------------------------------------------------------------------------

@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_verbname_uniqueness_constraint(t_init, t_wizard):
    with _ctx(t_wizard):
        obj = create("unique name obj")
    v = Verb.objects.create(origin=obj, owner=t_wizard, code="pass")
    VerbName.objects.create(verb=v, name="dupe")
    with pytest.raises(IntegrityError):
        VerbName.objects.create(verb=v, name="dupe")


# ---------------------------------------------------------------------------
# Repository
# ---------------------------------------------------------------------------

@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_repository_fields_stored(t_init, t_wizard):
    repo = Repository.objects.create(
        slug="myrepo",
        url="https://example.com/repo",
        prefix="moo/bootstrap/myrepo_verbs",
    )
    repo.refresh_from_db()
    assert repo.slug == "myrepo"
    assert repo.url == "https://example.com/repo"
    assert repo.prefix == "moo/bootstrap/myrepo_verbs"


# ---------------------------------------------------------------------------
# Verb override in subclass
# ---------------------------------------------------------------------------

@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_override_verb_in_subclass(t_init, t_wizard):
    with code.ContextManager(t_wizard, lambda m: None):
        root = create("Override Root Class")
        root.add_verb("accept", code="return False")
        room = create("Override Test Room", parents=[root])
        with pytest.raises(PermissionError):
            create("Test Object", location=room)
        room.add_verb("accept", code="return True")
        obj = create("Test Object", location=room)
        assert obj.location == room


# ---------------------------------------------------------------------------
# write() emits RuntimeWarning on memory broker
# ---------------------------------------------------------------------------

@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_write_to_caller(t_init, t_wizard):
    with code.ContextManager(t_wizard, lambda m: None):
        with pytest.warns(RuntimeWarning, match=r"ConnectionError"):
            code.interpret(
                "from moo.sdk import context, write\nwrite(context.caller, 'TEST_STRING')",
                "__main__",
            )
