# -*- coding: utf-8 -*-
# pylint: disable=protected-access
"""
Security tests: Verb / VerbName / Alias model permission checks.

Covers Verb.save / .delete / .reload, VerbName.save / .delete, Alias.delete,
Verb._invoked_object / _invoked_name read+write blocking, and passthrough()
caller-context forgery.
"""

import pytest

from moo.core.models.object import Object

from .. import code
from .utils import ctx

# ---------------------------------------------------------------------------
# Verb.save() must require write permission
# ---------------------------------------------------------------------------


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_verb_save_requires_write_permission(t_init, t_wizard):
    """

    A non-wizard with only read access must not be able to overwrite verb code
    by getting a Verb model instance and calling .save() directly.
    Verb.save() now calls can_caller("write", self) for updates.
    """
    from moo.sdk import create
    from moo.core.exceptions import AccessError

    with ctx(t_wizard):
        target = create("target_obj")
        target.add_verb("secret_verb", code='print("original")')

    with ctx(t_wizard):
        plain = create("plain_caller")
        target.allow(plain, "read")

    verb = target.get_verb("secret_verb")
    with ctx(plain):
        verb.code = "print('hacked')"
        with pytest.raises((PermissionError, AccessError)):
            verb.save()


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_verb_save_allowed_for_owner(t_init, t_wizard):
    """The owner of an object can still save changes to a verb on it."""
    from moo.sdk import create

    with ctx(t_wizard):
        target = create("target_obj2")
        target.add_verb("a_verb", code='print("v1")')

    verb = target.get_verb("a_verb")
    with ctx(t_wizard):
        verb.code = 'print("v2")'
        verb.save()

    verb.refresh_from_db()
    assert verb.code == 'print("v2")'


# ---------------------------------------------------------------------------
# Verb.delete() must require write permission
# ---------------------------------------------------------------------------


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_verb_delete_requires_write_permission(t_init: Object, t_wizard: Object):
    """

    Verb.delete() previously had no permission check. A non-wizard with read
    access could get a Verb instance via obj.verbs.filter(...).first() and call
    .delete() to destroy the verb, breaking dispatch. Verb.delete() now calls
    origin.can_caller("write", self) before delegating to super().delete().
    """
    from moo.sdk import create
    from moo.core.exceptions import AccessError

    with ctx(t_wizard):
        target = create("verb_del_target")
        target.add_verb("important_verb", code='print("hi")')
        plain = create("verb_del_plain")
        target.allow(plain, "read")

    verb = target.verbs.filter(names__name="important_verb").first()
    assert verb is not None

    with ctx(plain):
        with pytest.raises((PermissionError, AccessError)):
            verb.delete()

    assert target.verbs.filter(names__name="important_verb").exists()


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_verb_delete_allowed_for_owner(t_init: Object, t_wizard: Object):
    """The owner can delete a verb on their own object."""
    from moo.sdk import create

    with ctx(t_wizard):
        target = create("verb_del_owner_target")
        target.add_verb("deletable_verb", code='print("bye")')

    verb = target.verbs.filter(names__name="deletable_verb").first()
    assert verb is not None

    with ctx(t_wizard):
        verb.delete()

    assert not target.verbs.filter(names__name="deletable_verb").exists()


# ---------------------------------------------------------------------------
# VerbName.save() / VerbName.delete() must require write permission
# ---------------------------------------------------------------------------


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_verbname_save_requires_write_permission(t_init: Object, t_wizard: Object):
    """

    VerbName.save() previously had no permission check. A non-wizard with only
    read access could rename a verb by fetching its VerbName via verb.names.all()
    and calling .save() on it directly. VerbName.save() now calls
    verb.can_caller('write', verb) before delegating to super().save().
    """
    from moo.sdk import create
    from moo.core.exceptions import AccessError

    with ctx(t_wizard):
        target = create("verbname_save_target")
        target.add_verb("secret_verb", code='print("hi")')
        plain = create("verbname_save_plain")
        target.allow(plain, "read")

    verb = target.verbs.filter(names__name="secret_verb").first()
    vname = verb.names.first()
    assert vname is not None

    with ctx(plain):
        vname.name = "hijacked"
        with pytest.raises((PermissionError, AccessError)):
            vname.save()

    vname.refresh_from_db()
    assert vname.name == "secret_verb"


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_verbname_delete_requires_write_permission(t_init: Object, t_wizard: Object):
    """

    VerbName.delete() previously had no permission check. A non-wizard with read
    access could remove a verb's names (breaking dispatch) by calling .delete()
    on a VerbName instance. VerbName.delete() now calls can_caller('write', verb).
    """
    from moo.sdk import create
    from moo.core.exceptions import AccessError

    with ctx(t_wizard):
        target = create("verbname_del_target")
        target.add_verb("named_verb", code='print("hi")')
        plain = create("verbname_del_plain")
        target.allow(plain, "read")

    verb = target.verbs.filter(names__name="named_verb").first()
    vname = verb.names.first()
    assert vname is not None

    with ctx(plain):
        with pytest.raises((PermissionError, AccessError)):
            vname.delete()

    assert verb.names.filter(name="named_verb").exists()


# ---------------------------------------------------------------------------
# Alias.delete() must require write permission
# ---------------------------------------------------------------------------


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_alias_delete_requires_write_permission(t_init: Object, t_wizard: Object):
    """

    Alias.save() was already permission-checked, but Alias.delete() was not.
    A non-wizard with read access could delete an object's alias (altering how
    it is found by lookup()) by calling .delete() on an Alias instance.
    Alias.delete() now calls can_caller('write', self.object).
    """
    from moo.sdk import create
    from moo.core.exceptions import AccessError
    from moo.core.models.object import Alias

    with ctx(t_wizard):
        target = create("alias_del_target")
        target.add_alias("my_alias")
        plain = create("alias_del_plain")
        target.allow(plain, "read")

    alias = Alias.objects.filter(object=target, alias="my_alias").first()
    assert alias is not None

    with ctx(plain):
        with pytest.raises((PermissionError, AccessError)):
            alias.delete()

    assert Alias.objects.filter(object=target, alias="my_alias").exists()


# ---------------------------------------------------------------------------
# Verb.reload() must require write permission
# ---------------------------------------------------------------------------


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_verb_reload_requires_write_permission(t_init: Object, t_wizard: Object):
    """

    Verb.reload() previously had no permission check. A non-wizard with read
    access could call verb.reload() to trigger a repo fetch and overwrite verb
    code. Verb.reload() now calls origin.can_caller('write', self) first.
    The check fires even when repo/filename are None, so AccessError is raised
    before the RuntimeError for missing repo config.
    """
    from moo.sdk import create
    from moo.core.exceptions import AccessError

    with ctx(t_wizard):
        target = create("verb_reload_target")
        target.add_verb("reload_verb", code='print("original")')
        plain = create("verb_reload_plain")
        target.allow(plain, "read")

    verb = target.verbs.filter(names__name="reload_verb").first()
    assert verb is not None

    with ctx(plain):
        with pytest.raises((PermissionError, AccessError)):
            verb.reload()


# ---------------------------------------------------------------------------
# Verb._invoked_object / _invoked_name must be inaccessible from sandbox
# ---------------------------------------------------------------------------


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def testinvoked_object_write_blocked(t_init: Object, t_wizard: Object):
    """

    Verb._invoked_object is an underscore-prefixed instance attribute.
    _write_.__setattr__ must block verb code from overwriting it, preventing
    an attacker from redirecting the 'this' context to an arbitrary object
    before calling the verb.
    """
    from moo.sdk import create

    with ctx(t_wizard):
        target = create("invoked_obj_write_target")
        target.add_verb("test_verb", code='print("ok")')
        other = create("invoked_obj_other")

    verb_obj = target.verbs.filter(names__name="test_verb").first()
    assert verb_obj is not None

    with ctx(t_wizard):
        w = code.ContextManager.get("writer")
        g = code.get_default_globals()
        g.update(code.get_restricted_environment("__main__", w))
        g["verb_obj"] = verb_obj
        g["other"] = other
        with pytest.raises((AttributeError, TypeError, SyntaxError)):
            code.r_exec("verb_obj._invoked_object = other", {}, g)


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def testinvoked_name_write_blocked(t_init: Object, t_wizard: Object):
    """

    Verb._invoked_name is an underscore-prefixed instance attribute.
    _write_.__setattr__ must block verb code from overwriting it, preventing
    an attacker from redirecting passthrough() to an arbitrary verb name.
    RestrictedPython rejects _-prefixed attribute names at compile time
    (code.code is None), so exec raises TypeError; either way access is denied.
    """
    from moo.sdk import create

    with ctx(t_wizard):
        target = create("invoked_name_write_target")
        target.add_verb("test_verb2", code='print("ok")')

    verb_obj = target.verbs.filter(names__name="test_verb2").first()
    assert verb_obj is not None

    with ctx(t_wizard):
        w = code.ContextManager.get("writer")
        g = code.get_default_globals()
        g.update(code.get_restricted_environment("__main__", w))
        g["verb_obj"] = verb_obj
        with pytest.raises((AttributeError, TypeError, SyntaxError)):
            code.r_exec("verb_obj._invoked_name = 'hijacked'", {}, g)


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def testinvoked_object_read_blocked(t_init: Object, t_wizard: Object):
    """

    Verb._invoked_object is underscore-prefixed; get_protected_attribute must
    block read access from verb code, preventing information disclosure about
    the dispatch target. RestrictedPython rejects _-prefixed attribute names
    at compile time, so exec raises TypeError; either way access is denied.
    """
    from moo.sdk import create

    with ctx(t_wizard):
        target = create("invoked_obj_read_target")
        target.add_verb("test_verb3", code='print("ok")')

    verb_obj = target.verbs.filter(names__name="test_verb3").first()
    verb_obj._invoked_object = target

    with ctx(t_wizard):
        w = code.ContextManager.get("writer")
        g = code.get_default_globals()
        g.update(code.get_restricted_environment("__main__", w))
        g["verb_obj"] = verb_obj
        with pytest.raises((AttributeError, TypeError, SyntaxError)):
            code.r_exec("_ = verb_obj._invoked_object", {}, g)


# ---------------------------------------------------------------------------
# passthrough cannot be used to forge caller context
# ---------------------------------------------------------------------------


def test_passthrough_has_no_this_parameter():
    """

    passthrough() is passed to verb code as its second positional argument.
    Its implementation always uses self._invoked_object (underscore-prefixed,
    inaccessible to verb code) as the 'this' context for the parent verb call.
    Verb code can pass extra positional args but cannot supply a forged 'this'
    context because passthrough() does not accept it as a parameter.
    """
    import inspect
    from moo.core.models.verb import Verb

    v = Verb()
    sig = inspect.signature(v.passthrough)
    assert "this" not in sig.parameters


def test_passthrough_raises_when_unbound():
    """
    passthrough() raises RuntimeError when called on an unbound verb (no
    _invoked_object/_invoked_name set).  Verb code cannot construct a
    passthrough callable that would work outside of a legitimate dispatch
    context established by the Verb.__call__ machinery.
    """
    from moo.core.models.verb import Verb

    v = Verb()
    with pytest.raises(RuntimeError, match="unbound"):
        v.passthrough()
