# -*- coding: utf-8 -*-
"""
Unit tests for moo.sdk.prefetch_property.

Verifies that prefetch_property correctly pre-warms the session property cache
with direct properties, inherited properties (nearest-ancestor-wins), and missing
property sentinels — matching the semantics of get_property().
"""

import pytest

from moo.core import code
from moo.core.models import Object
from moo.core.models.object import _PROP_MISSING
from moo.sdk import create, lookup, prefetch_property


def _pcache_key(pk, name):
    return (pk, name, True)


def _open_ctx(wizard):
    return code.ContextManager(wizard, lambda s: None)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_obj(name, parent=None, owner=None):
    parents = [parent] if parent else []
    return create(name, parents=parents, owner=owner)


# ---------------------------------------------------------------------------
# Direct properties
# ---------------------------------------------------------------------------


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_direct_property(t_init: Object, t_wizard: Object):
    """Object with value set directly → cache contains that value."""
    with _open_ctx(t_wizard):
        obj = _make_obj("direct_obj", owner=t_wizard)
        obj.set_property("x", 42)
        prefetch_property([obj], "x")
        pcache = code.ContextManager.get_prop_lookup_cache()
        assert pcache is not None
    assert pcache[_pcache_key(obj.pk, "x")] == 42


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_direct_overrides_ancestor(t_init: Object, t_wizard: Object):
    """Object overrides ancestor value → own value wins."""
    with _open_ctx(t_wizard):
        parent = _make_obj("do_parent", owner=t_wizard)
        parent.set_property("x", True)
        child = _make_obj("do_child", parent=parent, owner=t_wizard)
        child.set_property("x", False)
        prefetch_property([child], "x")
        pcache = code.ContextManager.get_prop_lookup_cache()
        assert pcache is not None
    assert pcache[_pcache_key(child.pk, "x")] is False


# ---------------------------------------------------------------------------
# Inherited properties
# ---------------------------------------------------------------------------


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_inherited_property(t_init: Object, t_wizard: Object):
    """Child with no direct property inherits from parent."""
    with _open_ctx(t_wizard):
        parent = _make_obj("inh_parent", owner=t_wizard)
        parent.set_property("x", 42)
        child = _make_obj("inh_child", parent=parent, owner=t_wizard)
        prefetch_property([child], "x")
        pcache = code.ContextManager.get_prop_lookup_cache()
        assert pcache is not None
    assert pcache[_pcache_key(child.pk, "x")] == 42


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_nearest_ancestor_wins(t_init: Object, t_wizard: Object):
    """Nearest ancestor (min depth) takes priority over a more distant one."""
    with _open_ctx(t_wizard):
        grandparent = _make_obj("na_grandparent", owner=t_wizard)
        grandparent.set_property("x", 2)
        parent = _make_obj("na_parent", parent=grandparent, owner=t_wizard)
        parent.set_property("x", 1)
        child = _make_obj("na_child", parent=parent, owner=t_wizard)
        prefetch_property([child], "x")
        pcache = code.ContextManager.get_prop_lookup_cache()
        assert pcache is not None
    assert pcache[_pcache_key(child.pk, "x")] == 1


# ---------------------------------------------------------------------------
# Missing property
# ---------------------------------------------------------------------------


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_missing_property_sentinel(t_init: Object, t_wizard: Object):
    """Object with no matching property anywhere in the chain → _PROP_MISSING."""
    with _open_ctx(t_wizard):
        obj = _make_obj("missing_obj", owner=t_wizard)
        prefetch_property([obj], "no_such_prop_xyz")
        pcache = code.ContextManager.get_prop_lookup_cache()
        assert pcache is not None
    assert pcache[_pcache_key(obj.pk, "no_such_prop_xyz")] is _PROP_MISSING


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_empty_list_noop(t_init: Object, t_wizard: Object):
    """Empty list is a no-op and does not raise."""
    with _open_ctx(t_wizard):
        _cache = code.ContextManager.get_prop_lookup_cache()
        assert _cache is not None
        pcache_before = dict(_cache)
        prefetch_property([], "x")
        pcache_after = code.ContextManager.get_prop_lookup_cache()
        assert pcache_after is not None
    assert pcache_after == pcache_before


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_batch_mixed(t_init: Object, t_wizard: Object):
    """Batch of direct, inherited, and missing cases all resolved in one call."""
    with _open_ctx(t_wizard):
        parent = _make_obj("bm_parent", owner=t_wizard)
        parent.set_property("x", 99)

        direct_obj = _make_obj("bm_direct", owner=t_wizard)
        direct_obj.set_property("x", 7)

        inherited_obj = _make_obj("bm_inherited", parent=parent, owner=t_wizard)

        missing_obj = _make_obj("bm_missing", owner=t_wizard)

        prefetch_property([direct_obj, inherited_obj, missing_obj], "x")
        pcache = code.ContextManager.get_prop_lookup_cache()
        assert pcache is not None

    assert pcache[_pcache_key(direct_obj.pk, "x")] == 7
    assert pcache[_pcache_key(inherited_obj.pk, "x")] == 99
    assert pcache[_pcache_key(missing_obj.pk, "x")] is _PROP_MISSING


@pytest.mark.django_db(transaction=True, reset_sequences=True)
@pytest.mark.parametrize("t_init", ["default"], indirect=True)
def test_already_cached_not_overwritten(t_init: Object, t_wizard: Object):
    """Entries already in the session cache are not overwritten by a subsequent call."""
    with _open_ctx(t_wizard):
        obj = _make_obj("cached_obj", owner=t_wizard)
        obj.set_property("x", 5)
        # Manually prime the cache with a different value
        pcache = code.ContextManager.get_prop_lookup_cache()
        assert pcache is not None
        pcache[_pcache_key(obj.pk, "x")] = 999
        prefetch_property([obj], "x")
    # Should still be 999, not 5
    assert pcache[_pcache_key(obj.pk, "x")] == 999
