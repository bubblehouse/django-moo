# -*- coding: utf-8 -*-

from unittest.mock import patch

import pytest
from django.core.cache import cache

from moo.shell.history import RedisHistory


@pytest.fixture(autouse=True)
def _clear_cache():
    cache.clear()
    yield
    cache.clear()


def test_store_and_load_round_trip():
    """load_history_strings() yields stored entries newest-first."""
    h = RedisHistory(user_pk=1)
    h.store_string("a")
    h.store_string("b")
    h.store_string("c")
    assert list(h.load_history_strings()) == ["c", "b", "a"]


def test_dedupes_consecutive_repeats():
    """Back-to-back identical entries are collapsed to a single entry."""
    h = RedisHistory(user_pk=1)
    h.store_string("look")
    h.store_string("look")
    h.store_string("get key")
    h.store_string("get key")
    assert cache.get(h.key) == ["look", "get key"]


def test_non_consecutive_repeats_allowed():
    """Repeats separated by other entries are kept (only consecutive dedup)."""
    h = RedisHistory(user_pk=1)
    h.store_string("look")
    h.store_string("north")
    h.store_string("look")
    assert cache.get(h.key) == ["look", "north", "look"]


def test_skips_empty_and_whitespace():
    """Empty / whitespace-only strings are never persisted."""
    h = RedisHistory(user_pk=1)
    h.store_string("")
    h.store_string("   ")
    h.store_string("\t")
    h.store_string("\n  \t")
    assert cache.get(h.key) is None


def test_caps_at_limit():
    """Entries beyond ``cap`` drop oldest-first."""
    h = RedisHistory(user_pk=1, cap=5)
    for i in range(8):
        h.store_string(f"cmd-{i}")
    assert cache.get(h.key) == [f"cmd-{i}" for i in range(3, 8)]


def test_scoped_per_user():
    """Separate user_pks do not share history."""
    h1 = RedisHistory(user_pk=1)
    h2 = RedisHistory(user_pk=2)
    h1.store_string("alpha")
    h2.store_string("beta")
    assert list(h1.load_history_strings()) == ["alpha"]
    assert list(h2.load_history_strings()) == ["beta"]


def test_ttl_applied():
    """store_string passes the configured ttl through to cache.set."""
    h = RedisHistory(user_pk=1, ttl=1234)
    with patch("django.core.cache.cache.set") as mock_set:
        h.store_string("hello")
    mock_set.assert_called_once()
    _, kwargs = mock_set.call_args
    assert kwargs.get("timeout") == 1234
